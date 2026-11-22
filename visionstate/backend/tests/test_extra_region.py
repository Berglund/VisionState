"""Extra regions: a display's smaller last digits read from a box of their own (docs/SCOPE.md §5)."""

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from visionstate import bundle, change_limit, imaging, readers
from visionstate.engine.logic import reading_verdict
from visionstate.main import create_app
from visionstate.settings import (
    COUNTER_LIMIT,
    READING,
    dial_count,
    extra_digits,
    extra_region,
    merge_reading,
    value_decimals,
)

from .conftest import MODEL_DIR, requires_reader
from .displays import render_split, turned
from .test_integration import wait_for

LITRES = {"x": 3.2, "y": 0.0, "w": 0.8, "h": 0.6, "digits": 3}
WATER = merge_reading({"mode": "counter", "display": "lcd", "decimals": 0, "extra_region": LITRES})


@pytest.fixture
def settings(tmp_path):
    from visionstate.settings import Settings

    return Settings(
        data_dir=tmp_path / "data",
        media_dir=tmp_path / "media",
        frontend_dir=tmp_path / "none",
        bundled_models_dir=MODEL_DIR,
    )


def test_an_extra_region_adds_its_digits_as_decimals():
    assert extra_region(WATER) == LITRES and extra_digits(WATER) == 3 and value_decimals(WATER) == 3
    assert value_decimals({**WATER, "decimals": 1}) == 4
    # Kept, but not read, with a display or mode it does not go with.
    for other in ({"display": "counter"}, {"display": "dial", "mode": "flow"}, {"mode": "time_left"}):
        assert extra_region({**WATER, **other}) is None
    assert extra_digits({**WATER, "display": "counter", "counter_reader": "ocr"}) == 0
    assert extra_region(merge_reading({"display": "lcd"})) is None and extra_digits(merge_reading({})) == 0
    # The value: the region's digits, then the extra region's; the reader's own point still ignored.
    assert readers.parse("00957727", WATER) == pytest.approx(957.727)
    assert readers.format_value(957.727, WATER) == "957.727"
    assert readers.right_value("957.727", WATER) == pytest.approx(957.727)


def test_an_extra_region_read_with_another_number_of_digits_is_rejected():
    """A missed small digit would move every digit before it: 00957 and 72 is not 95.772."""
    read = lambda extra: {"reader": "x", "extra": {"text": extra, "score": 0.9}}  # noqa: E731
    assert not readers.wrong_digit_count("00957727", WATER, read("727"))
    assert readers.wrong_digit_count("0095772", WATER, read("72"))
    assert readers.wrong_digit_count("009577271", WATER, read("7271"))
    assert not readers.wrong_digit_count("0095772", WATER)  # nothing said about the extra region
    text = readers.Text("0095772", 0.95, read("72"))
    assert reading_verdict(text, 95.772, None, 0.5, WATER) == ("wrong digit count", False)
    good = readers.Text("00957727", 0.95, read("727"))
    assert reading_verdict(good, 957.727, 957.7, 0.5, WATER) == (None, False)


def test_an_extra_region_counts_like_decimals_not_like_dials():
    """The same value with three decimals read from one region or from two is limited alike: the
    jitter and standard rate of pointer dials are theirs alone."""
    one = merge_reading({"mode": "counter", "display": "lcd", "decimals": 3})
    assert dial_count(WATER) == 0
    assert change_limit.standard_rate(WATER) == change_limit.standard_rate(one)
    assert change_limit.standard_rate(WATER) == pytest.approx(COUNTER_LIMIT["standard_steps_per_min"] * 0.001 * 60)
    assert readers.settling(957.726, 957.727, WATER) and not readers.settling(957.725, 957.727, WATER)


def test_the_extra_region_is_cut_from_the_plane_the_region_is_read_in():
    image, roi, extra = render_split("00957", "727")
    flat = imaging.reading_plane(image, roi)
    assert flat is not None
    cut = imaging.extra_region_image(image, roi, extra)
    assert cut is not None
    assert cut.size == (round(extra["w"] * flat.height), round(extra["h"] * flat.height))
    # Turned and at an angle, straightened: the same box in the same plane, about the same picture.
    askew, region = turned(image, 25, roi, tilt=0.2)
    straight = imaging.extra_region_image(askew, region, extra, straightened=True)
    assert straight is not None and abs(straight.width / straight.height - cut.width / cut.height) < 0.1
    both = imaging.side_by_side([image, cut], gap=8)
    assert both.height == image.height and both.width > image.width + 8


class SplitCamera:
    """A camera looking at a display with smaller last digits (a water meter's litres)."""

    def __init__(self, big: str, small: str, angle: float = 0.0):
        image, roi, self.extra = render_split(big, small)
        if angle:  # turned only: the box was measured on the drawing, whose plane a tilt would stretch
            image, roi = turned(image, angle, roi)
        self.roi = roi
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=92)
        self.jpeg = buf.getvalue()

    async def grab(self, source_type, source, camera=None):
        return self.jpeg

    async def close(self):
        pass


@requires_reader
def test_a_display_with_smaller_last_digits(settings):
    camera = SplitCamera("00957", "727", angle=12)
    with TestClient(create_app(settings)) as client:
        client.app.state.runtime.grabber = camera
        reading = {"mode": "counter", "display": "auto", "decimals": 0, "unit": "m³", "straighten": True}
        preview = {"source_type": "http", "source": "http://fake", "roi": camera.roi}
        # The region alone: the big digits, and the face to place the extra region on.
        plain = client.post("/api/v1/preview/read", json={**preview, "reading": reading}).json()
        assert plain["text"] == "00957" and plain["extra"] is None and plain["face"].startswith("data:image/jpeg")
        # With it: its digits after the region's, as sure as the less sure part.
        litres = {**reading, "extra_region": camera.extra}
        read = client.post("/api/v1/preview/read", json={**preview, "reading": litres}).json()
        assert read["extra"]["text"] == "727" and read["text"] == "00957727" and read["value"] == "957.727"
        assert read["score"] == pytest.approx(min(read["score"], read["extra"]["score"]), abs=1e-4)
        assert not read["wrong_digit_count"]
        # One digit too many: rejected as a wrong digit count, never a value with the digits shifted.
        four = {**litres, "extra_region": {**camera.extra, "digits": 4}}
        assert client.post("/api/v1/preview/read", json={**preview, "reading": four}).json()["wrong_digit_count"]
        # Too many digits, or a box too small, is refused.
        many = {**litres, "extra_region": {**camera.extra, "digits": READING["max_extra_digits"] + 1}}
        assert client.post("/api/v1/preview/read", json={**preview, "reading": many}).status_code == 422
        tiny = {**litres, "extra_region": {**camera.extra, "w": READING["extra_region_min"] / 2}}
        assert client.post("/api/v1/preview/read", json={**preview, "reading": tiny}).status_code == 422
        config = client.get("/api/v1/config").json()
        assert config["reading_extra_region"]["max_extra_digits"] == READING["max_extra_digits"]
        assert config["reading_defaults"]["extra_region"] is None

        # A sensor: its value, History and the readings export carry the extra region.
        body = {"name": "Water", "kind": "reading", "source_type": "http", "source": "http://fake", "roi": camera.roi}
        sid = client.post("/api/v1/sensors", json={**body, "reading": litres}).json()["id"]
        value = lambda: client.get(f"/api/v1/sensors/{sid}").json()["reading"]  # noqa: E731
        assert wait_for(lambda: value()["value"] == "957.727", timeout=20), value()
        history = f"/api/v1/history?sensor={sid}"
        assert wait_for(lambda: client.get(history).json()["items"], timeout=30)
        first = client.get(history).json()["items"][0]
        assert first["probs"]["extra_region"] == camera.extra and first["probs"]["extra"]["text"] == "727"
        # What the reader saw is made again from the stored frame: the region and the extra region.
        seen = Image.open(io.BytesIO(client.get(f"/api/v1/history/{first['id']}/seen").content))
        region = Image.open(io.BytesIO(client.get(f"/api/v1/history/{first['id']}/image?size=region").content))
        assert seen.size != region.size and seen.width > seen.height
        export = client.get(f"/api/v1/sensors/{sid}/reading-export").content
        with zipfile.ZipFile(io.BytesIO(export)) as archive:
            manifest = json.loads(archive.read("readings.json"))
            entry = manifest["readings"][0]
            assert manifest["format"] == bundle.READINGS_FORMAT
            assert manifest["settings"]["extra_region"] == camera.extra
            assert entry["extra_region"] == {"file": "images/0001-extra.jpg", "digits": 3, "read": "727"}
            assert Image.open(archive.open(entry["extra_region"]["file"])).width > 0
