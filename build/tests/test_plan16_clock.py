"""Plan 16: the clock face is cut to a transparent circle, and W30 fires for a missing or non-square picture."""
from PIL import Image

from liquid import scene
from liquid.common import Issues


def test_cut_clock_is_a_transparent_circle(tmp_path):
    im = Image.new("RGB", (1024, 1024), (0, 0, 0))
    im.paste((200, 180, 140), (60, 60, 964, 964))
    p = tmp_path / "clock.jpg"
    im.save(p)
    out = scene.cut_clock(p, 128)
    assert out.size == (128, 128) and out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0 and out.getpixel((64, 64))[3] == 255


def test_w30_missing_and_not_square(tmp_path):
    issues = Issues()
    scene.check_clock(tmp_path, issues)
    assert issues.counts("warning") == {"W30": 1}
    Image.new("RGB", (100, 80)).save(tmp_path / "clock.jpg")
    issues = Issues()
    scene.check_clock(tmp_path, issues)
    assert issues.counts("warning") == {"W30": 1}
    Image.new("RGB", (100, 100)).save(tmp_path / "clock.jpg")
    issues = Issues()
    scene.check_clock(tmp_path, issues)
    assert issues.counts("warning") == {}
