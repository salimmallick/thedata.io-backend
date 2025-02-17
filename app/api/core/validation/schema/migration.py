from typing import Dict, Any, List, Optional
import yaml
from pathlib import Path
import logging
from datetime import datetime
from .validation import validate_schema
from ..metrics import metrics

logger = logging.getLogger(__name__)

class SchemaMigration:
    """Represents a schema migration"""
    
    def __init__(
        self,
        version: str,
        description: str,
        changes: Dict[str, Any],
        created_at: datetime = None
    ):
        self.version = version
        self.description = description
        self.changes = changes
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert migration to dictionary"""
        return {
            "version": self.version,
            "description": self.description,
            "changes": self.changes,
            "created_at": self.created_at.isoformat()
        }

class MigrationManager:
    """Manages schema migrations"""
    
    def __init__(self, migrations_dir: str = "migrations"):
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        self._load_migrations()
    
    def _load_migrations(self):
        """Load existing migrations"""
        self.migrations: Dict[str, SchemaMigration] = {}
        
        for migration_file in sorted(self.migrations_dir.glob("*.yaml")):
            try:
                with open(migration_file, "r") as f:
                    data = yaml.safe_load(f)
                    migration = SchemaMigration(
                        version=data["version"],
                        description=data["description"],
                        changes=data["changes"],
                        created_at=datetime.fromisoformat(data["created_at"])
                    )
                    self.migrations[migration.version] = migration
            except Exception as e:
                logger.error(f"Error loading migration {migration_file}: {str(e)}")
    
    def create_migration(
        self,
        description: str,
        changes: Dict[str, Any]
    ) -> SchemaMigration:
        """Create a new migration"""
        # Generate version
        version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        migration = SchemaMigration(
            version=version,
            description=description,
            changes=changes
        )
        
        # Save migration
        migration_path = self.migrations_dir / f"{version}.yaml"
        with open(migration_path, "w") as f:
            yaml.dump(migration.to_dict(), f)
        
        self.migrations[version] = migration
        return migration
    
    def apply_migration(
        self,
        data: Dict[str, Any],
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply migrations to data"""
        current_data = data.copy()
        
        # Get sorted migration versions
        versions = sorted(self.migrations.keys())
        if target_version:
            versions = [v for v in versions if v <= target_version]
        
        # Apply migrations in order
        for version in versions:
            migration = self.migrations[version]
            try:
                current_data = self._apply_changes(
                    current_data,
                    migration.changes
                )
                metrics.schema_changes_total.labels(
                    source="migration"
                ).inc()
            except Exception as e:
                logger.error(
                    f"Error applying migration {version}: {str(e)}"
                )
                raise
        
        return current_data
    
    def _apply_changes(
        self,
        data: Dict[str, Any],
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply migration changes to data"""
        result = data.copy()
        
        # Handle field renames
        renames = changes.get("rename_fields", {})
        for old_name, new_name in renames.items():
            if old_name in result:
                result[new_name] = result.pop(old_name)
        
        # Handle field removals
        removals = changes.get("remove_fields", [])
        for field in removals:
            result.pop(field, None)
        
        # Handle field additions
        additions = changes.get("add_fields", {})
        for field, value in additions.items():
            if field not in result:
                result[field] = value
        
        # Handle type changes
        type_changes = changes.get("change_types", {})
        for field, new_type in type_changes.items():
            if field in result:
                result[field] = self._convert_type(
                    result[field],
                    new_type
                )
        
        return result
    
    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type"""
        try:
            if target_type == "string":
                return str(value)
            elif target_type == "integer":
                return int(value)
            elif target_type == "float":
                return float(value)
            elif target_type == "boolean":
                return bool(value)
            elif target_type == "datetime":
                if isinstance(value, str):
                    return datetime.fromisoformat(value)
                return value
            else:
                return value
        except Exception as e:
            logger.error(f"Type conversion error: {str(e)}")
            return value
    
    def validate_migration(
        self,
        migration: SchemaMigration,
        sample_data: List[Dict[str, Any]]
    ) -> bool:
        """Validate migration against sample data"""
        try:
            for data in sample_data:
                # Apply migration
                migrated_data = self._apply_changes(
                    data,
                    migration.changes
                )
                
                # Validate result
                validate_schema(migrated_data)
            
            return True
        except Exception as e:
            logger.error(f"Migration validation error: {str(e)}")
            return False
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history"""
        return [
            {
                "version": version,
                "description": migration.description,
                "created_at": migration.created_at.isoformat()
            }
            for version, migration in sorted(
                self.migrations.items()
            )
        ]

# Create global migration manager instance
migration_manager = MigrationManager() 