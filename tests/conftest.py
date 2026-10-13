import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qsr import generate_data, measures as M, staging  # noqa: E402
from qsr.config import RAW_DIR  # noqa: E402


@pytest.fixture(scope="session")
def pipeline():
    """Regenerate data and rebuild the database once per test session (deterministic seed)."""
    generate_data.main()
    log = staging.build_db()
    return log


@pytest.fixture(scope="session")
def con(pipeline):
    c = M.connect()
    yield c
    c.close()


@pytest.fixture(scope="session")
def tables(con):
    names = ["encounter", "ed_visit", "safety_event", "abstraction_case", "core_measure_clinical", "patient_days",
             "device_days", "infection", "public_reporting_submission"]
    return {n: pd.read_sql(f"SELECT * FROM {n}", con) for n in names}
