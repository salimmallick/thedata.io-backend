from typing import Dict, Any, List
import yaml
from pathlib import Path
from ..transform import (
    TransformationType,
    TransformationConfig,
    TransformationRule,
    TimestampEnrichmentRule,
    SchemaValidationRule,
    DataNormalizationRule,
    transformation_pipeline
)
import logging

logger = logging.getLogger(__name__)

# Registry of available transformation rule types
RULE_REGISTRY = {
    "timestamp_enrichment": TimestampEnrichmentRule,
    "schema_validation": SchemaValidationRule,
    "data_normalization": DataNormalizationRule
}

class TransformationConfigManager:
    """Manages transformation rule configurations"""
    
    def __init__(self, config_dir: str = "config/transformations"):
        self.config_dir = Path(config_dir)
        self.config_cache: Dict[str, TransformationConfig] = {}
    
    def load_rule_configs(self) -> List[TransformationConfig]:
        """Load all rule configurations from the config directory"""
        configs = []
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load all YAML files
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file, "r") as f:
                    rule_data = yaml.safe_load(f)
                
                config = TransformationConfig(
                    name=rule_data["name"],
                    type=TransformationType(rule_data["type"]),
                    enabled=rule_data.get("enabled", True),
                    order=rule_data["order"],
                    config=rule_data.get("config", {})
                )
                
                self.config_cache[config.name] = config
                configs.append(config)
                
            except Exception as e:
                logger.error(f"Error loading config from {config_file}: {str(e)}")
        
        return sorted(configs, key=lambda x: x.order)
    
    def save_rule_config(self, config: TransformationConfig):
        """Save a rule configuration to file"""
        config_path = self.config_dir / f"{config.name}.yaml"
        
        config_data = {
            "name": config.name,
            "type": config.type,
            "enabled": config.enabled,
            "order": config.order,
            "config": config.config
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        self.config_cache[config.name] = config
    
    def get_rule_config(self, rule_name: str) -> TransformationConfig:
        """Get a rule configuration by name"""
        return self.config_cache.get(rule_name)
    
    def update_rule_config(
        self,
        rule_name: str,
        updates: Dict[str, Any]
    ) -> TransformationConfig:
        """Update a rule configuration"""
        config = self.config_cache.get(rule_name)
        if not config:
            raise ValueError(f"Rule {rule_name} not found")
        
        # Update configuration
        for key, value in updates.items():
            if key == "config":
                config.config.update(value)
            elif hasattr(config, key):
                setattr(config, key, value)
        
        # Save updated config
        self.save_rule_config(config)
        return config
    
    def create_rule(self, config: TransformationConfig) -> TransformationRule:
        """Create a transformation rule instance from config"""
        rule_class = RULE_REGISTRY.get(config.name)
        if not rule_class:
            raise ValueError(f"Unknown rule type: {config.name}")
        
        return rule_class(config)
    
    def apply_configs(self):
        """Apply all configurations to the transformation pipeline"""
        # Clear existing rules
        for rule_name in transformation_pipeline.rules.keys():
            transformation_pipeline.unregister_rule(rule_name)
        
        # Load and apply new configurations
        configs = self.load_rule_configs()
        for config in configs:
            try:
                rule = self.create_rule(config)
                transformation_pipeline.register_rule(rule)
                logger.info(f"Registered rule: {config.name}")
            except Exception as e:
                logger.error(f"Error registering rule {config.name}: {str(e)}")

# Create global config manager instance
config_manager = TransformationConfigManager() 