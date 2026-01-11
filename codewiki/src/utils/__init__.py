"""Utility modules for CodeWiki."""

# Import file_manager from parent utils.py module
# We need to import from the parent utils.py file, not create a circular import
import importlib.util
import sys
from pathlib import Path

# Load utils.py as a module
parent_dir = Path(__file__).parent.parent
utils_py_path = parent_dir / "utils.py"

if utils_py_path.exists():
    spec = importlib.util.spec_from_file_location("codewiki.src.utils_module", utils_py_path)
    utils_module = importlib.util.module_from_spec(spec)
    sys.modules["codewiki.src.utils_module"] = utils_module
    spec.loader.exec_module(utils_module)
    file_manager = utils_module.file_manager
else:
    # Fallback if utils.py doesn't exist
    file_manager = None

# Export metrics (optional, won't break if not available)
try:
    from .metrics import get_metrics_collector, MetricsCollector, RepoMetrics, StageMetrics
except ImportError:
    # Metrics are optional
    pass

