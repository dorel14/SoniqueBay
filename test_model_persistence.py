#!/usr/bin/env python
"""
Test script for model persistence service
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root directory to the path
sys.path.append(str(Path(__file__).parent))

# Set TESTING environment variable to avoid dependency issues
os.environ["TESTING"] = "true"

async def test_model_persistence():
    """Test the model persistence service"""
    print("Testing Model Persistence Service...")
    
    try:
        from backend_worker.services.model_persistence_service import ModelPersistenceService, ModelVersion
        
        # Create service instance
        service = ModelPersistenceService()
        print(f"[OK] ModelPersistenceService created: {service.models_dir}")
        
        # Test creating a model version
        version = ModelVersion(
            version_id="test_v1",
            created_at=datetime.now(),
            model_data={"test": "data"}
        )
        print(f"[OK] ModelVersion created: {version.version_id}")
        
        # Test list_model_versions (should return empty list in TESTING mode)
        versions = await service.list_model_versions()
        print(f"[OK] Listed {len(versions)} model versions")
        
        # Test get_current_version (should return None in TESTING mode)
        current = await service.get_current_version()
        print(f"[OK] Current version: {current}")
        
        print("\nAll tests passed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    from datetime import datetime
    result = asyncio.run(test_model_persistence())
    sys.exit(0 if result else 1)