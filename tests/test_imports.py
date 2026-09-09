import importlib
import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

MODULES = [
    "validation",
    "data_processing",
    "analysis",
    "recommendation",
    "scenario",
    "gemini",
    "app",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    module = importlib.import_module(module_name)
    assert module is not None


def test_repo_root_on_path():
    assert REPO_ROOT in sys.path


def test_required_env_files_are_not_committed():
    assert not os.path.exists(os.path.join(REPO_ROOT, ".env"))
