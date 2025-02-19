"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from fastapi import HTTPException, status, Depends, Request, Security
from ...models.user import TokenData, UserRole
from ...models.organization import Organization
from ..config import settings
from ..storage import db_pool
from pydantic import BaseModel
from ..logging.logger import logger
from ..monitoring.metrics import metrics
import hmac
import hashlib
import time
import json
import ipaddress
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
SIGNATURE_HEADER = APIKeyHeader(name="X-Signature", auto_error=False)
TIMESTAMP_HEADER = APIKeyHeader(name="X-Timestamp", auto_error=False)

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__min_rounds=12
)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise Exception(f"Invalid token: {str(e)}")

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user from database by email."""
    # In production, implement actual database lookup
    # This is a mock implementation for testing
    if email == "test@example.com":
        return {
            "email": email,
            "hashed_password": get_password_hash("testpass123"),
            "roles": ["user"],
            "org_id": "org123"
        }
    return None

async def authenticate_user(plain_password: str, hashed_password: str) -> bool:
    """Authenticate user by verifying password."""
    return verify_password(plain_password, hashed_password)

async def get_current_user(token: str) -> Dict[str, Any]:
    """Get current user from token."""
    payload = verify_token(token)
    email = payload.get("sub")
    if email is None:
        raise Exception("Invalid token payload")
    
    user = await get_user_by_email(email)
    if user is None:
        raise Exception("User not found")
    
    return user

async def get_current_user_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    async with db_pool.postgres_connection() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            email
        )
        if user is None:
            raise credentials_exception
        return dict(user)

def check_permissions(required_permissions: list[str], token_data: TokenData) -> bool:
    """Check if user has required permissions."""
    if token_data.role == UserRole.ADMIN:
        return True
    return all(perm in token_data.permissions for perm in required_permissions)

class PermissionChecker:
    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions
    
    async def __call__(self, current_user: dict = Depends(get_current_user_token)):
        async with db_pool.postgres_connection() as conn:
            user_permissions = await conn.fetch(
                """
                SELECT p.name
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN user_roles ur ON rp.role = ur.role
                WHERE ur.user_id = $1
                """,
                current_user["id"]
            )
            user_permissions = [p["name"] for p in user_permissions]
            
            for permission in self.required_permissions:
                if permission not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission: {permission}"
                    )
            return current_user

class SecurityMiddleware:
    """Security middleware for request validation and audit logging"""
    
    def __init__(self):
        self.audit_logger = logging.getLogger("audit")
        self._setup_audit_logging()
    
    def _setup_audit_logging(self):
        """Setup audit logging with proper formatting"""
        # Create logs directory if it doesn't exist
        os.makedirs("/opt/dagster/logs", exist_ok=True)
        handler = logging.FileHandler("/opt/dagster/logs/audit.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)
    
    async def validate_api_key(
        self, 
        api_key: str = Security(API_KEY_HEADER)
    ) -> Organization:
        """Validate API key and return organization"""
        async with get_postgres_conn() as conn:
            org = await conn.fetchrow(
                """
                SELECT id, name, api_key, api_secret
                FROM organizations
                WHERE api_key = $1
                """,
                api_key
            )
            
            if not org:
                self.audit_logger.warning(f"Invalid API key attempt: {api_key}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key"
                )
            
            return Organization(**org)
    
    async def validate_signature(
        self,
        request: Request,
        org: Organization,
        signature: Optional[str] = Security(SIGNATURE_HEADER),
        timestamp: Optional[str] = Security(TIMESTAMP_HEADER)
    ):
        """Validate request signature"""
        if not signature or not timestamp:
            self.audit_logger.warning(
                f"Missing signature/timestamp for org {org.id}"
            )
            raise HTTPException(
                status_code=401,
                detail="Missing signature or timestamp"
            )
        
        # Verify timestamp is within 5 minutes
        try:
            ts = int(timestamp)
            now = int(time.time())
            if abs(now - ts) > 300:  # 5 minutes
                raise HTTPException(
                    status_code=401,
                    detail="Request timestamp too old"
                )
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid timestamp"
            )
        
        # Reconstruct signature
        body = await request.body()
        message = f"{timestamp}{request.method}{request.url.path}{body.decode()}"
        expected_signature = hmac.new(
            org.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            self.audit_logger.warning(
                f"Invalid signature for org {org.id}"
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid signature"
            )
    
    async def audit_log_request(
        self,
        request: Request,
        org: Organization,
        response_status: int,
        response_body: Dict[str, Any]
    ):
        """Log request details for audit"""
        body = await request.body()
        self.audit_logger.info(
            json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "organization_id": org.id,
                "organization_name": org.name,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "request_body": body.decode(),
                "response_status": response_status,
                "response_body": response_body,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent")
            })
        )

# Create global security middleware instance
security = SecurityMiddleware()

# Dependency for protected endpoints
async def get_current_organization(
    request: Request,
    org: Organization = Depends(security.validate_api_key)
) -> Organization:
    """Get current organization with signature validation"""
    await security.validate_signature(request, org)
    return org 

class SecurityManager:
    """Enhanced security management for the API"""
    
    def __init__(self):
        self.blocked_ips: Dict[str, datetime] = {}
        self.suspicious_ips: Dict[str, int] = {}
        self.ip_rate_limits: Dict[str, Dict[str, Any]] = {}
        self.jwt_secret = settings.SECRET_KEY
        self.max_failed_attempts = 5
        self.block_duration = timedelta(minutes=15)
        self.suspicious_threshold = 3
        
        # IP whitelist and blacklist
        self.ip_whitelist = set(settings.IP_WHITELIST)
        self.ip_blacklist = set(settings.IP_BLACKLIST)
        
        # Rate limit configurations per endpoint
        self.endpoint_rate_limits = {
            "/ingest/events": {"limit": 1000, "window": 60},
            "/ingest/metrics": {"limit": 500, "window": 60},
            "/analytics": {"limit": 100, "window": 60},
            "default": {"limit": 200, "window": 60}
        }
    
    async def validate_ip(self, request: Request) -> bool:
        """Validate IP address against security rules"""
        ip = request.client.host
        
        # Check whitelist/blacklist
        if ip in self.ip_whitelist:
            return True
        if ip in self.ip_blacklist:
            raise HTTPException(status_code=403, detail="IP address blocked")
        
        # Check if IP is blocked
        if ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[ip]:
                raise HTTPException(status_code=403, detail="IP temporarily blocked")
            else:
                del self.blocked_ips[ip]
        
        # Update suspicious activity tracking
        if ip in self.suspicious_ips:
            if self.suspicious_ips[ip] >= self.max_failed_attempts:
                self.blocked_ips[ip] = datetime.now() + self.block_duration
                metrics.track_ip_blocked(ip)
                raise HTTPException(status_code=403, detail="IP blocked due to suspicious activity")
        
        return True
    
    async def check_endpoint_rate_limit(
        self,
        request: Request,
        org: Optional[Organization] = None
    ) -> bool:
        """Check rate limits for specific endpoints"""
        ip = request.client.host
        endpoint = request.url.path
        
        # Get rate limit configuration
        config = self.endpoint_rate_limits.get(
            endpoint,
            self.endpoint_rate_limits["default"]
        )
        
        # Adjust limits based on organization tier
        if org:
            config["limit"] *= self._get_tier_multiplier(org.tier)
        
        # Generate rate limit key
        key = f"ratelimit:{ip}:{endpoint}"
        if org:
            key += f":{org.id}"
        
        # Check rate limit
        allowed = await redis.check_rate_limit(
            key,
            config["limit"],
            config["window"]
        )
        
        if not allowed:
            metrics.track_rate_limit_hit(endpoint)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(config["window"])}
            )
        
        return True
    
    def _get_tier_multiplier(self, tier: str) -> float:
        """Get rate limit multiplier based on organization tier"""
        return {
            "basic": 1.0,
            "premium": 2.0,
            "enterprise": 5.0
        }.get(tier, 1.0)
    
    async def validate_request_signature(
        self,
        request: Request,
        org: Organization,
        signature: str,
        timestamp: str
    ) -> bool:
        """Validate request signature with enhanced security"""
        try:
            # Check timestamp freshness
            ts = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - ts) > settings.MAX_TIMESTAMP_DIFF:
                raise HTTPException(
                    status_code=401,
                    detail="Request timestamp too old"
                )
            
            # Get request body
            body = await self._get_request_body(request)
            
            # Generate expected signature
            message = f"{timestamp}{request.method}{request.url.path}{body}"
            expected_signature = hmac.new(
                org.api_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Constant time comparison
            if not hmac.compare_digest(signature, expected_signature):
                self._handle_failed_validation(request.client.host)
                raise HTTPException(
                    status_code=401,
                    detail="Invalid signature"
                )
            
            return True
            
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid timestamp format"
            )
    
    async def _get_request_body(self, request: Request) -> str:
        """Get request body for signature validation"""
        body = await request.body()
        return body.decode() if body else ""
    
    def _handle_failed_validation(self, ip: str):
        """Handle failed validation attempts"""
        self.suspicious_ips[ip] = self.suspicious_ips.get(ip, 0) + 1
        metrics.track_failed_validation(ip)
    
    async def create_jwt_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT token with enhanced security"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(
            to_encode,
            self.jwt_secret,
            algorithm=settings.ALGORITHM
        )
    
    async def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token with enhanced security"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[settings.ALGORITHM]
            )
            
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
    
    async def cleanup_blocked_ips(self):
        """Cleanup expired IP blocks"""
        current_time = datetime.now()
        expired = [
            ip for ip, block_time in self.blocked_ips.items()
            if current_time >= block_time
        ]
        
        for ip in expired:
            del self.blocked_ips[ip]
            if ip in self.suspicious_ips:
                del self.suspicious_ips[ip]

# Create global security manager
security_manager = SecurityManager() 