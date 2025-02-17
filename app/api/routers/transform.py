from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..core.config.transform_config import config_manager, RULE_REGISTRY
from ..core.config.transform_version import version_manager
from ..core.transform import TransformationType, TransformationConfig
from ..core.security import get_current_user_token, PermissionChecker
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transform", tags=["Transformation Rules"])

# Permission checker
require_transform_admin = PermissionChecker(["manage_transformations"])

class RuleUpdate(BaseModel):
    """Model for rule updates"""
    enabled: Optional[bool] = None
    order: Optional[int] = None
    config: Optional[Dict[str, Any]] = None

class RuleCreate(BaseModel):
    """Model for creating new rules"""
    name: str
    type: TransformationType
    enabled: bool = True
    order: int
    config: Dict[str, Any] = {}

@router.get("/rules", response_model=List[Dict[str, Any]])
async def list_rules(token = Depends(require_transform_admin)):
    """List all transformation rules and their configurations"""
    try:
        configs = config_manager.load_rule_configs()
        return [
            {
                "name": config.name,
                "type": config.type,
                "enabled": config.enabled,
                "order": config.order,
                "config": config.config
            }
            for config in configs
        ]
    except Exception as e:
        logger.error(f"Error listing rules: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list transformation rules"
        )

@router.get("/rules/{rule_name}")
async def get_rule(
    rule_name: str,
    token = Depends(require_transform_admin)
):
    """Get configuration for a specific rule"""
    config = config_manager.get_rule_config(rule_name)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Rule {rule_name} not found"
        )
    
    return {
        "name": config.name,
        "type": config.type,
        "enabled": config.enabled,
        "order": config.order,
        "config": config.config
    }

@router.post("/rules")
async def create_rule(
    rule: RuleCreate,
    token = Depends(require_transform_admin)
):
    """Create a new transformation rule"""
    try:
        # Verify rule type exists
        if rule.name not in RULE_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown rule type: {rule.name}"
            )
        
        # Create config
        config = TransformationConfig(
            name=rule.name,
            type=rule.type,
            enabled=rule.enabled,
            order=rule.order,
            config=rule.config
        )
        
        # Save config
        config_manager.save_rule_config(config)
        
        # Apply new configuration
        config_manager.apply_configs()
        
        return {
            "status": "success",
            "message": f"Rule {rule.name} created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating rule: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create transformation rule"
        )

@router.patch("/rules/{rule_name}")
async def update_rule(
    rule_name: str,
    updates: RuleUpdate,
    token = Depends(require_transform_admin)
):
    """Update an existing transformation rule"""
    try:
        # Convert model to dict, excluding None values
        update_data = updates.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No updates provided"
            )
        
        # Update config
        config = config_manager.update_rule_config(rule_name, update_data)
        
        # Apply updated configuration
        config_manager.apply_configs()
        
        return {
            "status": "success",
            "message": f"Rule {rule_name} updated successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating rule: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update transformation rule"
        )

@router.delete("/rules/{rule_name}")
async def delete_rule(
    rule_name: str,
    token = Depends(require_transform_admin)
):
    """Delete a transformation rule"""
    try:
        config_path = config_manager.config_dir / f"{rule_name}.yaml"
        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rule {rule_name} not found"
            )
        
        # Remove from cache
        if rule_name in config_manager.config_cache:
            del config_manager.config_cache[rule_name]
        
        # Delete config file
        config_path.unlink()
        
        # Apply updated configuration
        config_manager.apply_configs()
        
        return {
            "status": "success",
            "message": f"Rule {rule_name} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete transformation rule"
        )

@router.post("/rules/{rule_name}/toggle")
async def toggle_rule(
    rule_name: str,
    token = Depends(require_transform_admin)
):
    """Toggle a rule's enabled status"""
    try:
        config = config_manager.get_rule_config(rule_name)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Rule {rule_name} not found"
            )
        
        # Toggle enabled status
        updates = {"enabled": not config.enabled}
        config_manager.update_rule_config(rule_name, updates)
        
        # Apply updated configuration
        config_manager.apply_configs()
        
        return {
            "status": "success",
            "message": f"Rule {rule_name} {'enabled' if config.enabled else 'disabled'} successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling rule: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to toggle transformation rule"
        )

@router.get("/rules/{rule_name}/versions")
async def list_rule_versions(
    rule_name: str,
    token = Depends(require_transform_admin)
):
    """List all versions of a rule"""
    try:
        if not config_manager.get_rule_config(rule_name):
            raise HTTPException(
                status_code=404,
                detail=f"Rule {rule_name} not found"
            )
        
        versions = version_manager.list_versions(rule_name)
        return versions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing rule versions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list rule versions"
        )

@router.get("/rules/{rule_name}/versions/{version}")
async def get_rule_version(
    rule_name: str,
    version: int,
    token = Depends(require_transform_admin)
):
    """Get a specific version of a rule"""
    try:
        if not config_manager.get_rule_config(rule_name):
            raise HTTPException(
                status_code=404,
                detail=f"Rule {rule_name} not found"
            )
        
        rule_version = version_manager.get_version(rule_name, version)
        if not rule_version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version} not found for rule {rule_name}"
            )
        
        return {
            "version": rule_version.version,
            "created_at": rule_version.created_at.isoformat(),
            "comment": rule_version.comment,
            "config": rule_version.config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule version: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get rule version"
        )

@router.post("/rules/{rule_name}/versions")
async def create_rule_version(
    rule_name: str,
    comment: str = Body(..., embed=True),
    token = Depends(require_transform_admin)
):
    """Create a new version of a rule"""
    try:
        config = config_manager.get_rule_config(rule_name)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Rule {rule_name} not found"
            )
        
        # Create version from current config
        version = version_manager.save_version(
            rule_name,
            {
                "name": config.name,
                "type": config.type,
                "enabled": config.enabled,
                "order": config.order,
                "config": config.config
            },
            comment=comment
        )
        
        return {
            "status": "success",
            "version": version.version,
            "message": f"Version {version.version} created for rule {rule_name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rule version: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create rule version"
        )

@router.post("/rules/{rule_name}/rollback/{version}")
async def rollback_rule_version(
    rule_name: str,
    version: int,
    token = Depends(require_transform_admin)
):
    """Rollback a rule to a specific version"""
    try:
        if not config_manager.get_rule_config(rule_name):
            raise HTTPException(
                status_code=404,
                detail=f"Rule {rule_name} not found"
            )
        
        # Get version config
        config = version_manager.rollback_to_version(rule_name, version)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version} not found for rule {rule_name}"
            )
        
        # Update current config
        config_manager.update_rule_config(rule_name, config)
        
        # Apply updated configuration
        config_manager.apply_configs()
        
        return {
            "status": "success",
            "message": f"Rule {rule_name} rolled back to version {version}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back rule: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to rollback rule"
        )

@router.post("/rules/batch")
async def batch_update_rules(
    updates: Dict[str, RuleUpdate],
    token = Depends(require_transform_admin)
):
    """Update multiple rules in a single operation"""
    try:
        results = {}
        for rule_name, rule_updates in updates.items():
            try:
                update_data = rule_updates.dict(exclude_unset=True)
                if update_data:
                    config = config_manager.update_rule_config(
                        rule_name,
                        update_data
                    )
                    results[rule_name] = "success"
            except Exception as e:
                results[rule_name] = str(e)
        
        # Apply all updates
        config_manager.apply_configs()
        
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in batch update: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to perform batch update"
        ) 