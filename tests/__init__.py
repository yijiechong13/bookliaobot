import sys
import os

# Get absolute paths to key directories
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bot_dir = os.path.join(project_root, 'bot')
utils_dir = os.path.join(project_root, 'utils')

# Add to Python path if not already present
for path in [project_root, bot_dir, utils_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Optional: Configure any test-wide settings
def pytest_configure(config):
    """Pytest configuration hook"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )