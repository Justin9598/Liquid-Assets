"""Plan 11: no prices on the site, visits ordered cheapest first. Reads the published data the build wrote to docs/data."""
import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "docs" / "data"


@pytest.mark.skipif(not (DATA / "drinks").exists(), reason="docs/data not built")
def test_no_price_anywhere_in_published_data():
    for p in DATA.rglob("*.json"):
        text = p.read_text(encoding="utf-8")
        assert '"price"' not in text, p
        assert "S$" not in text, p


@pytest.mark.skipif(not (DATA / "drinks" / "hagi-no-tsuru-betsu-shikomi.json").exists(), reason="docs/data not built")
def test_real_drink_visits_cheapest_first_free_tasting_first():
    # Ledger: 2026-10-21 tasting at  then 2026-11-01 tasting with no price (free). Free goes first, though it is newer.
    d = json.loads((DATA / "drinks" / "hagi-no-tsuru-betsu-shikomi.json").read_text(encoding="utf-8"))
    assert [v["date"] for v in d["visits"]] == ["2026-11-01", "2026-10-21"]
    assert all(set(v) == {"date", "size", "where", "note"} for v in d["visits"])
