"""Optional snapshot of the real ledger counts (Plan 05 section 10.3), updated 2026-11-02 for the Fermenteria batch. Skipped when the ledger is absent."""
from pathlib import Path

import pytest

from liquid.pipeline import run

SHIP = Path(__file__).resolve().parents[2]
LEDGER = SHIP.parent / "Drinks Ledger.xlsx"


@pytest.mark.skipif(not LEDGER.exists(), reason="real ledger not available")
def test_real_counts(tmp_path):
    ship = tmp_path / "Ship"
    (ship / "content").mkdir(parents=True)
    res = run(ship, ledger_path=LEDGER, photos_dir=SHIP.parent / "Photos", new_dir=tmp_path / "New", check=True)
    assert res.exit_code == 0, res.issues.errors
    c = res.summary["counts"]
    assert c["drinks"] == 281
    assert c["categories"] == {"Sake": 250, "Fermented Beverages": 15, "Umeshu": 3, "Wine": 3, "Spirits": 8,
                               "Cocktails": 2}
    assert c["unshelved"] == 0
    assert sum(c["categories"].values()) == 281
