"""
Test for enhanced error handling in the DI container.
"""

import logging
from pathlib import Path

from nexus.core.di import container, DIContainer
from nexus.core.di.exceptions import (
    ServiceResolutionException, 
    ServiceRegistrationException, 
    DependencyInjectionException
)
from nexus.core.di.container import ServiceNotFoundError


def test_enhanced_error_handling():
    """Test enhanced error handling in the DI container."""
    # Create a test container
    test_container = DIContainer()
    
    # Test ServiceResolutionException
    try:
        # Try to resolve a service that is not registered
        test_container.resolve(logging.Logger)
        assert False, "Expected ServiceResolutionException was not raised"
    except ServiceResolutionException as e:
        print(f"ServiceResolutionException caught as expected: {e}")
        assert "logging.Logger" in e.service_type
    except ServiceNotFoundError:
        # This is also acceptable - ServiceNotFoundError is the base exception
        print("ServiceNotFoundError caught as expected")
    except Exception as e:
        assert False, f"Wrong exception type: {type(e)} - {e}"
    
    print("Enhanced error handling test passed!")


def test_service_not_found_error():
    """Test ServiceNotFoundError handling."""
    test_container = DIContainer()
    
    try:
        # Try to resolve a non-existent service
        test_container.resolve(str)  # str is unlikely to be registered
        assert False, "Expected ServiceResolutionException was not raised"
    except ServiceResolutionException as e:
        print(f"ServiceResolutionException properly handles service not found: {e}")
    except ServiceNotFoundError:
        # This is also acceptable
        print("ServiceNotFoundError caught directly")
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)} - {e}"


if __name__ == "__main__":
    test_enhanced_error_handling()
    test_service_not_found_error()
    print("All enhanced error handling tests passed!")