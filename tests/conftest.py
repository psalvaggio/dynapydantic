"""Pytest configuration"""

import re
import sys
from pathlib import Path

import pytest


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    """Determine whether to ignore a certain path"""
    del config

    match = re.search(r"test_.*_py3(?P<minor>[0-9]+)\.py", collection_path.name)
    if match is not None and sys.version_info < (3, int(match.group("minor"))):
        return True
    return False
