from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from enum import Enum

class APIVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"

class VersionManager:
    """Manages API versioning"""
    
    def __init__(self):
        self.current_version = APIVersion.V2
        self.supported_versions = {
            APIVersion.V1,
            APIVersion.V2
        }
        self.deprecated_versions = {APIVersion.V1}
    
    def get_version_from_request(self, request: Request) -> APIVersion:
        """Extract API version from request"""
        # Check header first
        version_header = request.headers.get("X-API-Version")
        if version_header:
            try:
                return APIVersion(version_header.lower())
            except ValueError:
                pass
        
        # Check URL path
        path_parts = request.url.path.split("/")
        for part in path_parts:
            try:
                return APIVersion(part.lower())
            except ValueError:
                continue
        
        # Default to current version
        return self.current_version
    
    def validate_version(self, version: APIVersion):
        """Validate API version"""
        if version not in self.supported_versions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported API version: {version}"
            )
        
        if version in self.deprecated_versions:
            # Add deprecation warning header
            return {
                "X-API-Warning": "This API version is deprecated. Please upgrade."
            }
        return {}
    
    def transform_request(
        self,
        version: APIVersion,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform request data based on version"""
        if version == APIVersion.V1:
            # Handle V1 format
            return self._transform_v1_request(data)
        return data
    
    def transform_response(
        self,
        version: APIVersion,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform response data based on version"""
        if version == APIVersion.V1:
            # Handle V1 format
            return self._transform_v1_response(data)
        return data
    
    def _transform_v1_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform V1 request format to current format"""
        transformed = data.copy()
        
        # Handle field name changes
        field_mappings = {
            "timestamp": "ts",
            "amount": "amt",
            "description": "desc"
        }
        
        for new_field, old_field in field_mappings.items():
            if old_field in transformed:
                transformed[new_field] = transformed.pop(old_field)
        
        return transformed
    
    def _transform_v1_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform current format to V1 response format"""
        transformed = data.copy()
        
        # Handle field name changes
        field_mappings = {
            "ts": "timestamp",
            "amt": "amount",
            "desc": "description"
        }
        
        for old_field, new_field in field_mappings.items():
            if old_field in transformed:
                transformed[new_field] = transformed.pop(old_field)
        
        return transformed

# Create global version manager instance
version_manager = VersionManager() 