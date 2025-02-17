from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List

from ..models.admin import SystemConfig, MetricsConfig, AlertConfig
from ..services.admin_service import AdminService
from ..core.auth.security import get_current_user_token, PermissionChecker
from ..core.config import settings
from ..models.user import UserRole

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/admin",
    tags=["admin"]
)

admin_service = AdminService()

# Create an admin permission checker
require_admin = PermissionChecker(["admin"])

async def get_current_admin_user(token_data = Depends(get_current_user_token)):
    if token_data.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return token_data

@router.get("/system/status")
async def get_system_status(admin = Depends(get_current_admin_user)) -> Dict[str, Any]:
    """Get current system status"""
    return admin_service.get_system_status()

@router.get("/system/config")
async def get_system_config() -> SystemConfig:
    """Get current system configuration"""
    return admin_service.get_config()

@router.put("/system/config")
async def update_system_config(config: SystemConfig) -> SystemConfig:
    """Update system configuration"""
    try:
        return admin_service.update_config(config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/metrics/config")
async def get_metrics_config() -> MetricsConfig:
    """Get metrics configuration"""
    return admin_service.get_metrics_config()

@router.put("/metrics/config")
async def update_metrics_config(config: MetricsConfig) -> MetricsConfig:
    """Update metrics configuration"""
    try:
        return admin_service.update_metrics_config(config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/alerts/config")
async def get_alerts_config() -> AlertConfig:
    """Get alerts configuration"""
    return admin_service.get_alerts_config()

@router.put("/alerts/config")
async def update_alerts_config(config: AlertConfig) -> AlertConfig:
    """Update alerts configuration"""
    try:
        return admin_service.update_alerts_config(config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/alerts/active")
async def get_active_alerts(admin = Depends(get_current_admin_user)) -> List[Dict[str, Any]]:
    """Get active system alerts"""
    try:
        return admin_service.get_active_alerts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    admin = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Acknowledge an alert"""
    try:
        admin_service.acknowledge_alert(alert_id)
        return {"status": "success", "message": f"Alert {alert_id} acknowledged"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 