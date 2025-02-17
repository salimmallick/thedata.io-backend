from typing import Dict, Any, List, Optional
from datetime import datetime
import yaml
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)

class RuleVersion:
    """Represents a version of a transformation rule configuration"""
    
    def __init__(
        self,
        version: int,
        config: Dict[str, Any],
        created_at: datetime,
        comment: str = ""
    ):
        self.version = version
        self.config = config
        self.created_at = created_at
        self.comment = comment

class VersionManager:
    """Manages versioning for transformation rule configurations"""
    
    def __init__(self, version_dir: str = "config/transformations/versions"):
        self.version_dir = Path(version_dir)
        self.version_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_rule_version_dir(self, rule_name: str) -> Path:
        """Get the version directory for a rule"""
        rule_dir = self.version_dir / rule_name
        rule_dir.mkdir(exist_ok=True)
        return rule_dir
    
    def save_version(
        self,
        rule_name: str,
        config: Dict[str, Any],
        comment: str = ""
    ) -> RuleVersion:
        """Save a new version of a rule configuration"""
        rule_dir = self._get_rule_version_dir(rule_name)
        
        # Get next version number
        existing_versions = [
            int(p.stem.split('_')[1])
            for p in rule_dir.glob("version_*.yaml")
        ]
        next_version = max(existing_versions, default=0) + 1
        
        # Create version object
        version = RuleVersion(
            version=next_version,
            config=config,
            created_at=datetime.utcnow(),
            comment=comment
        )
        
        # Save version file
        version_file = rule_dir / f"version_{next_version}.yaml"
        version_data = {
            "version": version.version,
            "created_at": version.created_at.isoformat(),
            "comment": version.comment,
            "config": version.config
        }
        
        with open(version_file, "w") as f:
            yaml.dump(version_data, f)
        
        return version
    
    def get_version(
        self,
        rule_name: str,
        version: int
    ) -> Optional[RuleVersion]:
        """Get a specific version of a rule configuration"""
        rule_dir = self._get_rule_version_dir(rule_name)
        version_file = rule_dir / f"version_{version}.yaml"
        
        if not version_file.exists():
            return None
        
        with open(version_file, "r") as f:
            data = yaml.safe_load(f)
            return RuleVersion(
                version=data["version"],
                config=data["config"],
                created_at=datetime.fromisoformat(data["created_at"]),
                comment=data["comment"]
            )
    
    def list_versions(
        self,
        rule_name: str
    ) -> List[Dict[str, Any]]:
        """List all versions of a rule configuration"""
        rule_dir = self._get_rule_version_dir(rule_name)
        versions = []
        
        for version_file in sorted(rule_dir.glob("version_*.yaml")):
            with open(version_file, "r") as f:
                data = yaml.safe_load(f)
                versions.append({
                    "version": data["version"],
                    "created_at": data["created_at"],
                    "comment": data["comment"]
                })
        
        return versions
    
    def rollback_to_version(
        self,
        rule_name: str,
        version: int
    ) -> Optional[Dict[str, Any]]:
        """Rollback a rule to a specific version"""
        rule_version = self.get_version(rule_name, version)
        if not rule_version:
            return None
        
        return rule_version.config
    
    def cleanup_old_versions(
        self,
        rule_name: str,
        keep_versions: int = 10
    ):
        """Clean up old versions of a rule configuration"""
        rule_dir = self._get_rule_version_dir(rule_name)
        versions = sorted(
            rule_dir.glob("version_*.yaml"),
            key=lambda p: int(p.stem.split('_')[1])
        )
        
        # Keep the latest n versions
        versions_to_delete = versions[:-keep_versions] if len(versions) > keep_versions else []
        
        for version_file in versions_to_delete:
            version_file.unlink()
    
    def delete_rule_versions(self, rule_name: str):
        """Delete all versions of a rule"""
        rule_dir = self._get_rule_version_dir(rule_name)
        if rule_dir.exists():
            shutil.rmtree(rule_dir)

# Create global version manager instance
version_manager = VersionManager() 