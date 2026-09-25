"""Tests for session.py loader and validator."""

import json
from pathlib import Path

import pytest

from adm_encoder.session import AudioObject, Block, Session, SessionMeta, load_session

MINIMAL_SESSION = {
    "version": "1.0",
    "session": {
        "title": "Test Track",
        "sampleRate": 48000,
        "bitDepth": 24,
        "duration": 10.0,
        "blockDurationSamples": 250,
        "sceneRadius": 20.0,
    },
    "objects": [
        {
            "id": "obj_0001",
            "name": "Pad",
            "stemFile": "stems/pad.wav",
            "gain": 1.0,
            "start": 0.0,
            "duration": 10.0,
            "blocks": [
                {"rtime": 0.0, "duration": 10.0, "x": -14.0, "y": 0.0, "z": 0.0, "gain": 0.8}
            ],
        },
        {
            "id": "obj_0002",
            "name": "Hi-Hat",
            "stemFile": "stems/hihat.wav",
            "gain": 0.9,
            "start": 0.0,
            "duration": 10.0,
            "blocks": [
                {"rtime": 0.0, "duration": 5.0, "x": 0.0, "y": 0.0, "z": 10.0},
                {"rtime": 5.0, "duration": 5.0, "x": 10.0, "y": 0.0, "z": 0.0},
            ],
        },
    ],
}


@pytest.fixture()
def session_file(tmp_path: Path) -> Path:
    p = tmp_path / "session.json"
    p.write_text(json.dumps(MINIMAL_SESSION), encoding="utf-8")
    return p


def test_load_session_round_trips(session_file: Path) -> None:
    s = load_session(session_file)
    assert s.version == "1.0"
    assert s.session.title == "Test Track"
    assert s.session.sample_rate == 48000
    assert s.session.bit_depth == 24
    assert s.session.duration == 10.0
    assert s.session.block_duration_samples == 250
    assert s.session.scene_radius == 20.0


def test_load_session_objects(session_file: Path) -> None:
    s = load_session(session_file)
    assert len(s.objects) == 2
    obj = s.objects[0]
    assert obj.id == "obj_0001"
    assert obj.name == "Pad"
    assert obj.stem_file == "stems/pad.wav"
    assert obj.gain == 1.0
    assert obj.start == 0.0
    assert obj.duration == 10.0


def test_load_session_blocks(session_file: Path) -> None:
    s = load_session(session_file)
    blk = s.objects[0].blocks[0]
    assert blk.rtime == 0.0
    assert blk.duration == 10.0
    assert blk.x == -14.0
    assert blk.y == 0.0
    assert blk.z == 0.0
    assert blk.gain == 0.8


def test_block_gain_defaults_to_one(tmp_path: Path) -> None:
    data = {**MINIMAL_SESSION}
    data["objects"][0]["blocks"][0] = {
        "rtime": 0.0, "duration": 10.0, "x": 0.0, "y": 0.0, "z": 0.0
    }
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data))
    s = load_session(p)
    assert s.objects[0].blocks[0].gain == 1.0


def test_validation_wrong_sample_rate(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SESSION))
    data["session"]["sampleRate"] = 44100
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="sampleRate"):
        load_session(p)


def test_validation_bad_bit_depth(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SESSION))
    data["session"]["bitDepth"] = 20
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="bitDepth"):
        load_session(p)


def test_validation_zero_scene_radius(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SESSION))
    data["session"]["sceneRadius"] = 0
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="sceneRadius"):
        load_session(p)


def test_validation_empty_objects(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SESSION))
    data["objects"] = []
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="at least one object"):
        load_session(p)


def test_validation_object_with_no_blocks(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SESSION))
    data["objects"][0]["blocks"] = []
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="no blocks"):
        load_session(p)


def test_validation_negative_block_gain(tmp_path: Path) -> None:
    data = json.loads(json.dumps(MINIMAL_SESSION))
    data["objects"][0]["blocks"][0]["gain"] = -0.1
    p = tmp_path / "s.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="gain"):
        load_session(p)
