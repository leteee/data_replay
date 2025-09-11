import subprocess
import sys
import shutil
import yaml
from pathlib import Path
import pytest

# --- Constants ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_MODULE = "nexus.cli"
DEMO_CASE_NAME = "demo"
DEMO_CASE_PATH = PROJECT_ROOT / "cases" / DEMO_CASE_NAME

# --- Helper Functions ---

def load_demo_case_plugins():
    """Dynamically loads plugin names from the demo case yaml file."""
    case_yaml_path = DEMO_CASE_PATH / "case.yaml"
    if not case_yaml_path.exists():
        # This will be handled by the generate-data test, but good to be robust
        return []
    with open(case_yaml_path, 'r') as f:
        case_config = yaml.safe_load(f)
    return [item['plugin'] for item in case_config.get('pipeline', [])]

def run_cli_command(command_args):
    """Runs a CLI command and returns the result."""
    full_command = [sys.executable, "-m", CLI_MODULE] + command_args
    return subprocess.run(
        full_command, 
        check=True, 
        capture_output=True, 
        text=True, 
        cwd=PROJECT_ROOT
    )

# --- Pytest Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def cleanup_before_session(request):
    """Cleans up demo case directory before any tests run."""
    if DEMO_CASE_PATH.exists():
        shutil.rmtree(DEMO_CASE_PATH)
    # Optional: Add other directories to clean, like 'logs'

# --- Test Suite ---

@pytest.mark.dependency()
def test_generate_data():
    """Tests the 'generate-data' command and verifies its output."""
    run_cli_command(["generate-data"])
    
    # Assert that key files were created
    assert (DEMO_CASE_PATH / "case.yaml").exists(), "case.yaml not found"
    assert (DEMO_CASE_PATH / "raw_data" / "latent_measurements.csv").exists(), "latent_measurements.csv not found"
    assert (DEMO_CASE_PATH / "raw_data" / "video_manifest.csv").exists(), "video_manifest.csv not found"
    assert (DEMO_CASE_PATH / "raw_data" / "frames").is_dir(), "frames directory not found"

@pytest.mark.dependency(depends=["test_generate_data"])
def test_full_pipeline():
    """Tests the full pipeline run and verifies the final output."""
    run_cli_command(["pipeline", "--case", DEMO_CASE_NAME])
    
    # Assert that the intermediate output from the refactored plugin exists
    assert (DEMO_CASE_PATH / "intermediate" / "predicted_states.parquet").exists(), "Intermediate parquet output not found"
    
    # Assert that the final output video was created
    # Note: The output file name is derived from the default config for the VideoCreator plugin
    assert (DEMO_CASE_PATH / "output" / "replay_video.mp4").exists(), "Final video output not found"

@pytest.mark.dependency(depends=["test_full_pipeline"])
@pytest.mark.parametrize("plugin_name", load_demo_case_plugins())
def test_single_plugin(plugin_name):
    """Tests running each plugin individually."""
    run_cli_command(["plugin", plugin_name, "--case", DEMO_CASE_NAME])
    # Assertion for single plugin runs could be more complex, e.g., checking for intermediate files.
    # For now, we just ensure the command runs successfully.

@pytest.mark.dependency(depends=["test_full_pipeline"])
def test_generate_docs():
    """Tests the 'docs' command and verifies its output."""
    run_cli_command(["docs"])
    
    output_file = PROJECT_ROOT / 'REFERENCE.md'
    assert output_file.exists(), "REFERENCE.md was not generated"
    
    # Verify content
    content = output_file.read_text()
    assert "# Framework Reference" in content
    # Check if plugins from the demo case are in the docs
    for plugin_name in load_demo_case_plugins():
        assert f"### {plugin_name}" in content, f"{plugin_name} not found in documentation"