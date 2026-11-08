"""Plan 13: the crop tool's server, the check image, the new photo-map fields, E07 and the report's contact sheet."""
import http.client
import json
import subprocess
import threading
from pathlib import Path

import sys

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import croptool
import cropcheck
from liquid import cropguard, photos
from liquid.common import Issues
from liquid.pipeline import run

from fixture import make_project

REAL_MAP = Path(__file__).resolve().parents[2] / "content" / "photo-map.json"

START = {
    "alpha": {"front": "alpha.jpg", "labelCrop": [0.1, 0.2, 0.3, 0.4], "labelStatus": "ok"},
    "beta": {"front": "beta.jpg", "labelStatus": "skip", "labelSkip": "a glass"},
    "gamma": {"front": "gamma.jpg", "labelCrop": [0.2, 0.2, 0.5, 0.5], "labelStatus": "ok", "cropBy": "owner"},
}


def project(tmp_path, crlf=True):
    """A tiny Ship/ with a photo map (CRLF, no trailing newline, like the real file), three photos and a shell."""
    ship = tmp_path / "Ship"
    (ship / "content").mkdir(parents=True)
    (ship / "reports").mkdir()
    (ship / "docs" / "data").mkdir(parents=True)
    (ship / "docs" / "img" / "scene").mkdir(parents=True)
    photos_dir = tmp_path / "Photos"
    photos_dir.mkdir()
    text = json.dumps(START, indent=1, ensure_ascii=False)
    (ship / "content" / "photo-map.json").write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    for n in ("alpha", "beta", "gamma"):
        Image.new("RGB", (400, 600), (90, 120, 60)).save(photos_dir / f"{n}.jpg")
    Image.new("RGBA", (200, 600), (30, 90, 40, 255)).save(ship / "docs" / "img" / "scene" / "shell-sake@2x.webp")
    scene = {"shells": {"sake": {"labelRect": [0.05, 0.6, 0.9, 0.3], "labelBlend": "multiply", "aspect": 0.33,
                                 "files": {"1x": "img/scene/shell-sake@1x.webp", "2x": "img/scene/shell-sake@2x.webp"}}}}
    (ship / "docs" / "data" / "scene.json").write_text(json.dumps(scene), encoding="utf-8")
    cands = {n: {"name": n.title(), "category": "sake", "sub": "junmai", "front": f"{n}.jpg"} for n in ("alpha", "beta", "gamma", "delta")}
    cands["delta"]["front"] = "alpha.jpg"
    (ship / "reports" / "crop-candidates.json").write_text(json.dumps(cands), encoding="utf-8")
    return ship, photos_dir


@pytest.fixture()
def server(tmp_path):
    ship, photos_dir = project(tmp_path)
    srv = croptool.make_server(ship, photos_dir, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, ship
    srv.shutdown()
    srv.server_close()


def call(srv, method, path, body=None, headers=None):
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    data = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
    conn.request(method, path, body=data, headers=h)
    r = conn.getresponse()
    out = r.read()
    conn.close()
    return r.status, out


def raw_map(ship):
    return (ship / "content" / "photo-map.json").read_bytes()


# ---------------------------------------------------------------- the server

def test_listens_on_loopback_only(server):
    srv, _ = server
    assert srv.server_address[0] == "127.0.0.1"


def test_serves_page_map_info_and_photos_read_only(server):
    srv, ship = server
    st, body = call(srv, "GET", "/")
    assert st == 200 and b"Crop tool" in body
    st, body = call(srv, "GET", "/api/map")
    assert st == 200 and json.loads(body)["alpha"]["labelStatus"] == "ok"
    st, body = call(srv, "GET", "/api/info")
    info = json.loads(body)
    assert st == 200 and set(info["drinks"]) == {"alpha", "beta", "gamma", "delta"} and "sake" in info["shells"]
    st, body = call(srv, "GET", "/photo/alpha")
    assert st == 200 and body[:2] == b"\xff\xd8"
    assert call(srv, "GET", "/photo/..%2f..%2fShip%2fcontent%2fphoto-map.json")[0] == 404     # ids only, never paths
    assert call(srv, "GET", "/photo/nope")[0] == 404
    assert call(srv, "GET", "/shell/shell-sake@2x.webp")[0] == 200
    assert call(srv, "GET", "/shell/..%2f..%2f..%2fcontent%2fphoto-map.json")[0] == 404
    assert call(srv, "GET", "/content/photo-map.json")[0] == 404
    for method in ("PUT", "DELETE", "PATCH"):
        assert call(srv, method, "/save", {})[0] == 405


def test_save_updates_only_that_entry_keeps_format_and_backs_up(server):
    srv, ship = server
    before = raw_map(ship)
    st, body = call(srv, "POST", "/save", {"id": "alpha", "status": "ok", "crop": [0.25, 0.3, 0.4, 0.35]})
    assert st == 200, body
    after = json.loads(raw_map(ship))
    assert after["alpha"] == {"front": "alpha.jpg", "labelCrop": [0.25, 0.3, 0.4, 0.35], "labelStatus": "ok", "cropBy": "owner"}
    assert list(after) == list(START)                                  # key order kept
    assert after["beta"] == START["beta"] and after["gamma"] == START["gamma"]
    assert b"\r\n" in raw_map(ship) and not raw_map(ship).endswith(b"\n")     # line ending and ending kept
    backups = sorted((ship / "reports" / "photo-map-backups").glob("photo-map-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == before     # the backup is the old file, byte for byte
    assert not list((ship / "content").glob("*.tmp"))                  # the temp file is gone
    saves = json.loads((ship / "reports" / "owner-saves.json").read_text(encoding="utf-8"))
    assert saves["alpha"] == cropguard.entry_hash(after["alpha"])


def test_each_save_makes_its_own_backup_and_a_new_drink_is_added_at_the_end(server):
    srv, ship = server
    assert call(srv, "POST", "/save", {"id": "delta", "status": "ok", "crop": [0.1, 0.1, 0.5, 0.5]})[0] == 200
    assert call(srv, "POST", "/save", {"id": "beta", "status": "skip", "reason": "blurred"})[0] == 200
    data = json.loads(raw_map(ship))
    assert list(data) == ["alpha", "beta", "gamma", "delta"]
    assert data["beta"] == {"front": "beta.jpg", "labelStatus": "skip", "labelSkip": "blurred", "cropBy": "owner"}
    assert data["delta"] == {"labelCrop": [0.1, 0.1, 0.5, 0.5], "labelStatus": "ok", "cropBy": "owner"}
    assert len(list((ship / "reports" / "photo-map-backups").glob("*.json"))) == 2


def test_save_refuses_every_other_path_and_bad_input(server):
    srv, ship = server
    before = raw_map(ship)
    good = {"id": "alpha", "status": "ok", "crop": [0.1, 0.1, 0.5, 0.5]}
    for path in ("/", "/api/map", "/save/", "/content/photo-map.json", "/../content/other.json", "/save/../x"):
        assert call(srv, "POST", path, good)[0] == 404, path
    assert call(srv, "POST", "/save", {**good, "path": "../x.json"})[0] == 400         # no path field is ever accepted
    assert call(srv, "POST", "/save", {**good, "file": "x"})[0] == 400
    assert call(srv, "POST", "/save", {**good, "id": "not-a-drink"})[0] == 400
    assert call(srv, "POST", "/save", {**good, "id": "../Ship/x"})[0] == 400
    assert call(srv, "POST", "/save", {**good, "crop": [0.9, 0.9, 0.5, 0.5]})[0] == 400  # runs off the photo
    assert call(srv, "POST", "/save", {**good, "crop": [0.1, 0.1]})[0] == 400
    assert call(srv, "POST", "/save", {**good, "status": "maybe"})[0] == 400
    assert call(srv, "POST", "/save", b"not json")[0] == 400
    assert call(srv, "POST", "/save", good, {"Origin": "http://evil.example"})[0] == 403
    assert call(srv, "POST", "/save", good, {"Host": "evil.example"})[0] == 403
    assert raw_map(ship) == before
    assert not (ship / "reports" / "photo-map-backups").exists()
    assert sorted(p.name for p in (ship / "content").iterdir()) == ["photo-map.json"]      # nothing else was written


def test_dump_keeps_the_real_file_exactly():
    like = REAL_MAP.read_bytes().decode("utf-8")
    assert croptool.dump_map(json.loads(like), like) == like


def test_shipper_cannot_record_over_an_owner_crop(tmp_path):
    ship, _ = project(tmp_path)
    before = raw_map(ship)
    with pytest.raises(PermissionError):
        croptool.record_decision(ship, "gamma", "shipper", "ok", [0.1, 0.1, 0.5, 0.5], check="passed")
    assert raw_map(ship) == before
    croptool.record_decision(ship, "alpha", "shipper", "ok", [0.2, 0.2, 0.3, 0.3], check="unsure")
    e = json.loads(raw_map(ship))["alpha"]
    assert e["cropBy"] == "shipper" and e["cropCheck"] == "unsure"
    assert not (ship / "reports" / "owner-saves.json").exists()            # only the owner's saves are logged


# ---------------------------------------------------------------- the check image

def test_cropcheck_writes_the_three_part_image_and_skips_owner_crops(tmp_path, capsys):
    ship, photos_dir = project(tmp_path)
    path = cropcheck.make_check(ship, "alpha", [0.1, 0.5, 0.6, 0.3], photos_dir)
    assert path == ship / "reports" / "crops" / "alpha.png"
    with Image.open(path) as im:
        assert im.width > 600 and im.height > 500                          # photo, crop and shell side by side
    with pytest.raises(SystemExit):
        cropcheck.make_check(ship, "alpha", [0.9, 0.9, 0.5, 0.5], photos_dir)


# ---------------------------------------------------------------- build: the new fields

def _map(entry):
    issues = Issues()
    out, _, _ = photos.build_photo_map([{"id": "x", "name": "X"}], ["x.jpg"], {"x": dict({"front": "x.jpg"}, **entry)}, issues)
    return out["x"], issues


def test_build_accepts_cropby_and_cropcheck():
    out, issues = _map({"labelCrop": [0.1, 0.1, 0.5, 0.5], "labelStatus": "ok", "cropBy": "owner", "cropCheck": "passed"})
    assert not issues.errors and out["cropBy"] == "owner" and out["cropCheck"] == "passed"
    out, issues = _map({"labelCrop": [0.1, 0.1, 0.5, 0.5], "labelStatus": "ok", "cropBy": "shipper", "cropCheck": "unsure"})
    assert not issues.errors and out["cropBy"] == "shipper" and out["cropCheck"] == "unsure"
    out, issues = _map({"labelCrop": [0.1, 0.1, 0.5, 0.5], "labelStatus": "ok"})                  # existing entries have neither
    assert not issues.errors and out["cropBy"] is None and out["cropCheck"] is None


@pytest.mark.parametrize("entry", [{"cropBy": "designer"}, {"cropCheck": "fine"}, {"cropBy": True}])
def test_build_rejects_other_values_with_e04(entry):
    _, issues = _map(dict({"labelCrop": [0.1, 0.1, 0.5, 0.5], "labelStatus": "ok"}, **entry))
    assert [i["code"] for i in issues.items if i["level"] == "error"] == ["E04"]


# ---------------------------------------------------------------- E07

OWNER = {"labelCrop": [0.1, 0.1, 0.5, 0.5], "labelStatus": "ok", "cropBy": "owner"}


def test_e07_when_a_non_owner_changes_an_owner_crop():
    head = {"a": dict(OWNER), "b": {"labelStatus": "ok", "labelCrop": [0.1, 0.1, 0.3, 0.3]}}
    issues = Issues()
    changed = {"a": dict(OWNER, labelCrop=[0.2, 0.2, 0.5, 0.5]), "b": {"labelStatus": "ok", "labelCrop": [0.5, 0.5, 0.3, 0.3]}}
    assert cropguard.check_owner_crops(head, changed, {}, issues) == 1                 # b is not an owner crop
    assert [i["code"] for i in issues.errors] == ["E07"] and "'a'" in issues.errors[0]["message"]
    issues = Issues()
    assert cropguard.check_owner_crops(head, {"b": head["b"]}, {}, issues) == 1       # removed
    issues = Issues()
    assert cropguard.check_owner_crops(head, {"a": dict(OWNER, cropBy="shipper"), "b": head["b"]}, {}, issues) == 1   # mark stripped
    issues = Issues()
    assert cropguard.check_owner_crops(head, {"a": dict(OWNER), "b": changed["b"]}, {}, issues) == 0      # unchanged is fine
    assert not issues.errors


def test_e07_allows_the_owner_to_redraw_in_the_tool():
    head = {"a": dict(OWNER)}
    redrawn = dict(OWNER, labelCrop=[0.3, 0.3, 0.4, 0.4])
    issues = Issues()
    assert cropguard.check_owner_crops(head, {"a": redrawn}, {"a": cropguard.entry_hash(redrawn)}, issues) == 0
    assert cropguard.check_owner_crops(head, {"a": redrawn}, {"a": "stale"}, Issues()) == 1
    assert cropguard.entry_hash(redrawn) == croptool.entry_hash(redrawn)               # build and tool agree


def test_e07_stops_a_real_build_through_the_last_commit(tmp_path):
    ship = make_project(tmp_path)
    mp = ship / "content" / "photo-map.json"
    mp.write_text(json.dumps({"sake-a": dict(OWNER)}), encoding="utf-8")
    git = lambda *a: subprocess.run(["git", "-C", str(ship), "-c", "user.email=t@t", "-c", "user.name=t", *a], capture_output=True, check=True)
    git("init", "-q")
    git("add", "content/photo-map.json")
    git("commit", "-q", "-m", "owner crop")
    assert run(ship, check=True).exit_code == 0                                         # matches the last commit
    mp.write_text(json.dumps({"sake-a": dict(OWNER, labelCrop=[0.2, 0.2, 0.5, 0.5])}), encoding="utf-8")   # a script edit
    res = run(ship, check=True)
    assert res.exit_code == 1 and [i["code"] for i in res.issues.errors] == ["E07"]
    croptool.record_decision(ship, "sake-a", "owner", "ok", [0.2, 0.2, 0.5, 0.5])        # the same change, through the tool
    assert run(ship, check=True).exit_code == 0


# ---------------------------------------------------------------- the report

def test_report_groups_crops_tags_owner_crops_and_links_to_the_tool(tmp_path):
    ship = make_project(tmp_path)
    (ship / "content" / "photo-map.json").write_text(json.dumps({
        "sake-a": {"labelCrop": [0.3, 0.5, 0.4, 0.2], "labelStatus": "ok", "cropBy": "owner"},
        "sake-b": {"labelCrop": [0.3, 0.5, 0.4, 0.2], "labelStatus": "ok", "cropBy": "shipper", "cropCheck": "unsure"},
    }), encoding="utf-8")
    res = run(ship)
    assert res.exit_code == 0, res.issues.errors
    html = (ship / "reports" / "build-report.html").read_text(encoding="utf-8")
    assert html.index("Needs a look (1)") < html.index("The rest (1)")
    assert "<span class='tag'>yours</span>" in html
    assert "http://127.0.0.1:8765/#sake-a" in html and "http://127.0.0.1:8765/#sake-b" in html
    cands = json.loads((ship / "reports" / "crop-candidates.json").read_text(encoding="utf-8"))
    assert "sake-a" in cands and cands["sake-a"]["front"]
