"""Tests for pipeline.py — session JSON + stems → ADM BWF in one call."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from ear.fileio.bw64 import Bw64Reader
from lxml import etree

from adm_encoder.pipeline import StemNotFoundError, encode_session, resolve_stem
from adm_encoder.wav_writer import load_chna

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "examples" / "cmaj7-demo"
DEMO_STEMS = DEMO_DIR / "stems"
FIXTURE_SESSION = Path(__file__).parent / "fixtures" / "cmaj7_session.json"
NS = {"e": "urn:ebu:metadata-schema:ebuCore_2014"}


def _assert_valid_master(path: Path, n_objects: int, seconds: float) -> None:
    with Bw64Reader(open(path, "rb")) as reader:
        assert reader.channels == n_objects
        assert reader.sampleRate == 48000
        assert reader.bitdepth == 24
        assert abs(len(reader) / 48000 - seconds) < 0.01
        assert len(reader.chna.audioIDs) == n_objects
        tree = etree.fromstring(reader.axml)
    assert len(tree.findall(".//e:audioObject", NS)) == n_objects


# ---------------------------------------------------------------------------
# resolve_stem
# ---------------------------------------------------------------------------


def test_resolve_stem_next_to_session(tmp_path: Path) -> None:
    (tmp_path / "pad.wav").write_bytes(b"x")
    assert resolve_stem("pad.wav", tmp_path) == tmp_path / "pad.wav"


def test_resolve_stem_in_stems_subfolder(tmp_path: Path) -> None:
    (tmp_path / "stems").mkdir()
    (tmp_path / "stems" / "pad.wav").write_bytes(b"x")
    assert resolve_stem("pad.wav", tmp_path) == tmp_path / "stems" / "pad.wav"


def test_resolve_stem_explicit_dir_is_the_only_place_searched(tmp_path: Path) -> None:
    (tmp_path / "pad.wav").write_bytes(b"x")  # next to session, but must be ignored
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(StemNotFoundError):
        resolve_stem("pad.wav", tmp_path, stems_dir=other)
    (other / "pad.wav").write_bytes(b"x")
    assert resolve_stem("pad.wav", tmp_path, stems_dir=other) == other / "pad.wav"


def test_resolve_stem_missing_lists_every_path_tried(tmp_path: Path) -> None:
    with pytest.raises(StemNotFoundError) as exc:
        resolve_stem("pad.wav", tmp_path)
    message = str(exc.value)
    assert "not found" in message
    assert "Looked in:" in message
    assert str(tmp_path / "pad.wav") in message
    assert str(tmp_path / "stems" / "pad.wav") in message


# ---------------------------------------------------------------------------
# encode_session
# ---------------------------------------------------------------------------


def test_encode_fixture_session_with_demo_stems(tmp_path: Path) -> None:
    out = tmp_path / "master.wav"
    session = encode_session(FIXTURE_SESSION, out, stems_dir=DEMO_STEMS)
    assert len(session.objects) == 4
    _assert_valid_master(out, n_objects=4, seconds=30.0)


def test_encode_finds_stems_folder_beside_session(tmp_path: Path) -> None:
    shutil.copy(FIXTURE_SESSION, tmp_path / "session.json")
    shutil.copytree(DEMO_STEMS, tmp_path / "stems")
    out = tmp_path / "master.wav"
    encode_session(tmp_path / "session.json", out)
    _assert_valid_master(out, n_objects=4, seconds=30.0)


def test_encode_writes_intermediates(tmp_path: Path) -> None:
    inter = tmp_path / "inter"
    encode_session(FIXTURE_SESSION, tmp_path / "master.wav", stems_dir=DEMO_STEMS, intermediates_dir=inter)
    tree = etree.fromstring((inter / "adm.xml").read_bytes())
    assert len(tree.findall(".//e:audioObject", NS)) == 4
    entries = load_chna(inter / "chna.json")
    assert [e.trackIndex for e in entries] == [1, 2, 3, 4]


def test_encode_missing_stem_raises_before_writing(tmp_path: Path) -> None:
    out = tmp_path / "master.wav"
    with pytest.raises(StemNotFoundError):
        encode_session(FIXTURE_SESSION, out, stems_dir=tmp_path)
    assert not out.exists()


@pytest.mark.skipif(
    not (DEMO_DIR / "session.json").exists(),
    reason="examples/cmaj7-demo/session.json is recorded in Unity (plan Task 8)",
)
def test_encode_recorded_demo_session(tmp_path: Path) -> None:
    out = tmp_path / "demo.wav"
    session = encode_session(DEMO_DIR / "session.json", out)
    _assert_valid_master(out, n_objects=4, seconds=session.session.duration)
