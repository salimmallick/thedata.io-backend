from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..core.config.transform_config import config_manager, RULE_REGISTRY
from ..core.config.transform_version import version_manager
from ..core.data.transform import TransformationType, TransformationConfig
from ..core.auth.security import get_current_user_token, PermissionChecker
from ..core.database import db_pool, DatabaseError
from fastapi import status
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["Transformation Rules"])

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

@router.get("/", response_model=List[Dict[str, Any]])
async def list_rules(token = Depends(require_transform_admin)):
    """List all transformation rules"""
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

@router.get("/{rule_name}")
async def get_rule(
    rule_name: str,
    token = Depends(require_transform_admin)
):
    """Get a specific rule"""
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

@router.post("/")
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

@router.patch("/{rule_name}")
async def update_rule(
    rule_name: str,
    updates: RuleUpdate,
    token = Depends(require_transform_admin)
):
    """Update a rule"""
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

@router.delete("/{rule_name}")
async def delete_rule(
    rule_name: str,
    token = Depends(require_transform_admin)
):
    """Delete a rule"""
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

@router.post("/{rule_name}/toggle")
async def toggle_rule(
    rule_name: str,
    token = Depends(require_transform_admin)
):
    """Toggle rule enabled/disabled state"""
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

@router.get("/{rule_name}/versions")
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

@router.get("/{rule_name}/versions/{version}")
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

@router.post("/{rule_name}/versions")
async def create_rule_version(
    rule_name: str,
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
            }
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

@router.post("/{rule_name}/rollback/{version}")
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

@router.post("/batch")
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

@router.get("/rules")
async def list_transformation_rules(
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> List[Dict[str, Any]]:
    """List all transformation rules."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Get user's organizations
            org_ids = await conn.fetch("""
                SELECT organization_id
                FROM organization_members
                WHERE user_id = $1
            """, current_user["id"])
            
            if not org_ids:
                return []
            
            # Get transformation rules
            rules = await conn.fetch("""
                SELECT 
                    r.id,
                    r.name,
                    r.type,
                    r.input_table,
                    r.output_table,
                    r.transformation,
                    r.status,
                    r.order_index,
                    r.created_at,
                    r.updated_at
                FROM transformation_rules r
                JOIN data_sources ds ON r.input_table = ds.name
                WHERE ds.organization_id = ANY($1::bigint[])
                ORDER BY r.order_index
            """, [org["organization_id"] for org in org_ids])
            
            return [dict(rule) for rule in rules]
            
    except DatabaseError as e:
        logger.error(f"Database error listing transformation rules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error listing transformation rules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/materialized-views")
async def list_materialized_views(
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> List[Dict[str, Any]]:
    """List all materialized views."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Get user's organizations
            org_ids = await conn.fetch("""
                SELECT organization_id
                FROM organization_members
                WHERE user_id = $1
            """, current_user["id"])
            
            if not org_ids:
                return []
            
            # Get materialized views
            views = await conn.fetch("""
                SELECT 
                    v.id,
                    v.name,
                    v.source_table,
                    v.refresh_schedule,
                    v.last_refresh,
                    v.status,
                    v.created_at,
                    v.updated_at
                FROM materialized_views v
                JOIN data_sources ds ON v.source_table = ds.name
                WHERE ds.organization_id = ANY($1::bigint[])
                ORDER BY v.name
            """, [org["organization_id"] for org in org_ids])
            
            return [dict(view) for view in views]
            
    except DatabaseError as e:
        logger.error(f"Database error listing materialized views: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error listing materialized views: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/sinks")
async def list_data_sinks(
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> List[Dict[str, Any]]:
    """List all data sinks."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Get user's organizations
            org_ids = await conn.fetch("""
                SELECT organization_id
                FROM organization_members
                WHERE user_id = $1
            """, current_user["id"])
            
            if not org_ids:
                return []
            
            # Get data sinks
            sinks = await conn.fetch("""
                SELECT 
                    s.id,
                    s.name,
                    s.type,
                    s.config,
                    s.status,
                    s.created_at,
                    s.updated_at
                FROM data_sinks s
                WHERE s.organization_id = ANY($1::bigint[])
                ORDER BY s.name
            """, [org["organization_id"] for org in org_ids])
            
            return [dict(sink) for sink in sinks]
            
    except DatabaseError as e:
        logger.error(f"Database error listing data sinks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error listing data sinks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/retention-policies")
async def list_retention_policies(
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> List[Dict[str, Any]]:
    """List all retention policies."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Get user's organizations
            org_ids = await conn.fetch("""
                SELECT organization_id
                FROM organization_members
                WHERE user_id = $1
            """, current_user["id"])
            
            if not org_ids:
                return []
            
            # Get retention policies
            policies = await conn.fetch("""
                SELECT 
                    p.id,
                    p.name,
                    p.table_name,
                    p.retention_days,
                    p.status,
                    p.created_at,
                    p.updated_at
                FROM retention_policies p
                JOIN data_sources ds ON p.table_name = ds.name
                WHERE ds.organization_id = ANY($1::bigint[])
                ORDER BY p.name
            """, [org["organization_id"] for org in org_ids])
            
            return [dict(policy) for policy in policies]
            
    except DatabaseError as e:
        logger.error(f"Database error listing retention policies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error listing retention policies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 