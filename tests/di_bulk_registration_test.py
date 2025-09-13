"""
Test for the new bulk service registration feature.
"""

import logging
from pathlib import Path

from nexus.core.di import container
from nexus.core.di.container import DIContainer
from nexus.core.context import NexusContext
from nexus.core.data.hub import DataHub


def test_bulk_registration():
    """Test the new bulk service registration feature."""
    # Create a test container
    test_container = DIContainer()
    
    # Create a mock context
    logger = logging.getLogger(__name__)
    data_hub = DataHub(case_path=Path("."))
    
    class MockContext:
        def __init__(self):
            self.logger = logger
            self.data_hub = data_hub
    
    context = MockContext()
    
    # Test bulk registration
    test_container.register_core_services(context)
    
    print("Bulk service registration test passed!")


if __name__ == "__main__":
    test_bulk_registration()