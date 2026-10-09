import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FIXTURE = BACKEND / "tests" / "fixtures" / "catalog.fixture.json"
sys.path.insert(0, str(BACKEND))
os.environ["VNSTORE_CATALOG"] = str(FIXTURE)

from app.catalog.store import load_snapshot  # noqa: E402
from app.search.engine import SearchEngine  # noqa: E402


@pytest.fixture(scope="session")
def snap():
    return load_snapshot(FIXTURE)


@pytest.fixture(scope="session")
def engine(snap):
    return SearchEngine(snap)
