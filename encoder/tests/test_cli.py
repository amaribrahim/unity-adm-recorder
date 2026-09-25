"""Tests for the adm-encode CLI."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from adm_encoder.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_STEMS = REPO_ROOT / "examples" / "cmaj7-demo" / "stems"
FIXTURE_SESSION = Path(__file__).parent / "fixtures" / "cmaj7_session.json"


def _one_object_session(tmp_path: Path, stem_name: str = "tone.wav") -> Path:
    session = {
        "version": "1.0",
        "session": {
            "title": "CLI test", "sampleRate": 48000, "bitDepth": 24,
            "duration": 1.0, "blockDurationSamples": 2400, "sceneRadius": 20.0,
        },
        "objects": [{
            "id": "obj_0001", "name": "Tone", "stemFile": stem_name,
            "gain": 1.0, "start": 0.0, "duration": 1.0,
            "blocks": [{"rtime": 0.0, "duration": 1.0, "x": 5.0, "y": 0.0, "z": 5.0, "gain": 1.0}],
        }],
    }
    path = tmp_path / "session.json"
    path.write_text(json.dumps(session), encoding="utf-8")
    return path


def _write_tone(path: Path, sr: int = 48000, channels: int = 1) -> None:
    t = np.linspace(0, 1, sr, endpoint=False, dtype=np.float32)
    tone = 0.3 * np.sin(2 * np.pi * 440 * t)
    data = tone if channels == 1 else np.column_stack([tone] * channels)
    sf.write(str(path), data, sr, subtype="PCM_24")


def test_encodes_demo_and_reports(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    out = tmp_path / "master.wav"
    rc = main([str(FIXTURE_SESSION), "--stems-dir", str(DEMO_STEMS), "-o", str(out)])
    assert rc == 0
    assert out.exists()
    assert "4 objects" in capsys.readouterr().out


def test_keep_intermediates_writes_xml_and_chna(tmp_path: Path) -> None:
    inter = tmp_path / "inter"
    rc = main([
        str(FIXTURE_SESSION), "--stems-dir", str(DEMO_STEMS),
        "-o", str(tmp_path / "master.wav"), "--keep-intermediates", str(inter),
    ])
    assert rc == 0
    assert (inter / "adm.xml").is_file()
    assert (inter / "chna.json").is_file()


def test_missing_session_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = main([str(tmp_path / "nope.json"), "-o", str(tmp_path / "m.wav")])
    assert rc == 1
    assert "error: session not found" in capsys.readouterr().err


def test_missing_stem_lists_paths_tried(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    session = _one_object_session(tmp_path)
    rc = main([str(session), "-o", str(tmp_path / "m.wav")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "Looked in:" in err
    assert str(tmp_path / "stems" / "tone.wav") in err


def test_wrong_sample_rate_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    session = _one_object_session(tmp_path)
    _write_tone(tmp_path / "tone.wav", sr=44100)
    rc = main([str(session), "-o", str(tmp_path / "m.wav")])
    assert rc == 1
    assert "sample rate 44100" in capsys.readouterr().err


def test_stereo_stem_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    session = _one_object_session(tmp_path)
    _write_tone(tmp_path / "tone.wav", channels=2)
    rc = main([str(session), "-o", str(tmp_path / "m.wav")])
    assert rc == 1
    assert "mono" in capsys.readouterr().err


def test_malformed_session_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    bad = tmp_path / "session.json"
    bad.write_text(json.dumps({"version": "1.0", "objects": []}), encoding="utf-8")
    rc = main([str(bad), "-o", str(tmp_path / "m.wav")])
    assert rc == 1
    assert "missing field" in capsys.readouterr().err


def test_corrupt_stem_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    session = _one_object_session(tmp_path)
    (tmp_path / "tone.wav").write_bytes(b"not really audio")
    rc = main([str(session), "-o", str(tmp_path / "m.wav")])
    assert rc == 1
    assert "error:" in capsys.readouterr().err


def test_unwritable_output_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a folder")
    rc = main([str(FIXTURE_SESSION), "--stems-dir", str(DEMO_STEMS), "-o", str(blocker / "m.wav")])
    assert rc == 1
    assert "error:" in capsys.readouterr().err
