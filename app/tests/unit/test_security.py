import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from jose import jwt, JWTError
from app.api.core.security import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    authenticate_user,
    get_current_user
)
from app.api.core.config import get_settings
import time

# Get settings instance
settings = get_settings()

def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    
    # Test hashing
    hashed = get_password_hash(password)
    assert hashed != password
    assert len(hashed) > 0
    
    # Test verification
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_create_access_token():
    """Test JWT token creation."""
    user_data = {
        "sub": "testuser@example.com",
        "roles": ["user"],
        "org_id": "org123"
    }
    
    # Test token creation
    token = create_access_token(user_data)
    assert token
    
    # Verify token contents
    decoded = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    assert decoded["sub"] == user_data["sub"]
    assert decoded["roles"] == user_data["roles"]
    assert decoded["org_id"] == user_data["org_id"]
    assert "exp" in decoded

def test_create_access_token_expiry():
    """Test token expiration."""
    user_data = {"sub": "testuser@example.com"}
    expires_delta = timedelta(minutes=15)
    
    token = create_access_token(user_data, expires_delta)
    decoded = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    
    # Verify expiration time
    exp_time = datetime.fromtimestamp(decoded["exp"])
    expected_exp = datetime.utcnow() + expires_delta
    assert abs((exp_time - expected_exp).total_seconds()) < 1

def test_verify_token():
    """Test token verification."""
    user_data = {
        "sub": "testuser@example.com",
        "roles": ["user"]
    }
    token = create_access_token(user_data)
    
    # Test valid token
    verified_data = verify_token(token)
    assert verified_data["sub"] == user_data["sub"]
    assert verified_data["roles"] == user_data["roles"]
    
    # Test invalid token
    with pytest.raises(Exception):
        verify_token("invalid-token")

@pytest.mark.asyncio
async def test_verify_expired_token():
    """Test verification of expired JWT token."""
    # Create a token that's already expired
    data = {"sub": "test@example.com"}
    expired_token = create_access_token(
        data=data,
        expires_delta=timedelta(seconds=-1)  # Token is already expired
    )

    # Verify the expired token raises JWTError
    with pytest.raises(Exception, match="Invalid token: Signature has expired."):
        await verify_token(expired_token)

@pytest.mark.asyncio
async def test_authenticate_user():
    """Test user authentication."""
    test_user = {
        "email": "test@example.com",
        "hashed_password": get_password_hash("testpass123")
    }
    
    with patch('app.api.core.security.get_user_by_email') as mock_get_user:
        # Setup mock
        mock_get_user.return_value = test_user
        
        # Test valid credentials
        user = await authenticate_user("test@example.com", "testpass123")
        assert user == test_user
        
        # Test invalid password
        user = await authenticate_user("test@example.com", "wrongpass")
        assert user is None
        
        # Test non-existent user
        mock_get_user.return_value = None
        user = await authenticate_user("nonexistent@example.com", "testpass123")
        assert user is None

@pytest.mark.asyncio
async def test_get_current_user():
    """Test current user retrieval from token."""
    test_user = {
        "email": "test@example.com",
        "roles": ["user"],
        "org_id": "org123"
    }
    token = create_access_token({"sub": test_user["email"], **test_user})
    
    with patch('app.api.core.security.get_user_by_email') as mock_get_user:
        # Setup mock
        mock_get_user.return_value = test_user
        
        # Test valid token
        user = await get_current_user(token)
        assert user == test_user
        
        # Test invalid token
        with pytest.raises(Exception):
            await get_current_user("invalid-token")
        
        # Test valid token but non-existent user
        mock_get_user.return_value = None
        with pytest.raises(Exception):
            await get_current_user(token)

def test_token_refresh():
    """Test token refresh functionality."""
    original_token = create_access_token({"sub": "test@example.com"})
    
    # Verify original token
    original_data = verify_token(original_token)
    
    # Create refresh token
    refresh_token = create_access_token(
        {"sub": original_data["sub"]},
        expires_delta=timedelta(days=7)
    )
    
    # Verify refresh token has longer expiration
    refresh_data = verify_token(refresh_token)
    assert refresh_data["exp"] > original_data["exp"] 