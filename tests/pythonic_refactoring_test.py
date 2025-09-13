"""
Test for the Pythonic refactoring plan.
"""

import tempfile
from pathlib import Path

from nexus.core.refactoring.pythonic_plan import (
    PythonicRefactoringPlan,
    demonstrate_pythonic_refactoring,
    benchmark_pythonic_approaches
)


def test_pythonic_refactoring_plan():
    """Test the Pythonic refactoring plan."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        # Create a Pythonic refactoring plan
        plan = PythonicRefactoringPlan(project_root)
        
        # Test identifying complex areas
        complex_areas = plan.identify_complex_areas()
        assert isinstance(complex_areas, list)
        assert len(complex_areas) > 0
        assert "Deep class hierarchies in DI container" in complex_areas
        
        # Test progress summary
        progress = plan.get_progress_summary()
        assert isinstance(progress, dict)
        assert "completed_phases" in progress
        assert "current_phase" in progress
        assert "total_phases" in progress
        assert "progress_percentage" in progress
        
        print("Pythonic refactoring plan test passed!")


def test_demonstrate_pythonic_refactoring():
    """Test the demonstration of Pythonic refactoring principles."""
    # This is a simple test to ensure the function runs without error
    try:
        demonstrate_pythonic_refactoring()
        print("Demonstration of Pythonic refactoring principles test passed!")
    except Exception as e:
        assert False, f"Demonstration failed with error: {e}"


def test_benchmark_pythonic_approaches():
    """Test the benchmark of Pythonic approaches."""
    # This is a simple test to ensure the function runs without error
    try:
        benchmark_pythonic_approaches()
        print("Benchmark of Pythonic approaches test passed!")
    except Exception as e:
        assert False, f"Benchmark failed with error: {e}"


if __name__ == "__main__":
    test_pythonic_refactoring_plan()
    test_demonstrate_pythonic_refactoring()
    test_benchmark_pythonic_approaches()
    print("All Pythonic refactoring plan tests passed!")