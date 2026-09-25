"""Integration tests for the ADM BWF smusher (wav_writer.assemble_adm_bwf)."""

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from ear.fileio.bw64 import Bw64Reader
from ear.fileio.bw64.chunks import AudioID

from adm_encoder.adm_xml import build_adm_xml, build_chna
from adm_encoder.session import load_session
from adm_encoder.wav_writer import assemble_adm_bwf, load_chna

FIXTURES = Path(__file__).parent / "fixtures"
SR = 48000
DURATION_SECS = 1
N_SAMPLES = SR * DURATION_SECS


@pytest.fixture()
def two_stems(tmp_path: Path) -> tuple[Path, Path]:
    """Write two 1-second 48kHz mono sine-wave stems to tmp_path."""
    t = np.linspace(0, DURATION_SECS, N_SAMPLES, endpoint=False, dtype=np.float32)
    stem1 = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    stem2 = (0.5 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)

    p1 = tmp_path / "stem1.wav"
    p2 = tmp_path / "stem2.wav"
    sf.write(str(p1), stem1, SR, subtype="PCM_24")
    sf.write(str(p2), stem2, SR, subtype="PCM_24")
    return p1, p2


@pytest.fixture()
def chna_entries() -> list[AudioID]:
    return [
        AudioID(
            trackIndex=1,
            audioTrackUID="ATU_00000001",
            audioTrackFormatIDRef="AT_00031001_01",
            audioPackFormatIDRef="AP_00031001",
        ),
        AudioID(
            trackIndex=2,
            audioTrackUID="ATU_00000002",
            audioTrackFormatIDRef="AT_00031002_01",
            audioPackFormatIDRef="AP_00031002",
        ),
    ]


@pytest.fixture()
def adm_xml() -> str:
    return (FIXTURES / "minimal_2obj.xml").read_text(encoding="utf-8")


def test_assembles_without_error(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
    adm_xml: str,
) -> None:
    out = tmp_path / "master.wav"
    assemble_adm_bwf(list(two_stems), adm_xml, chna_entries, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_output_has_correct_channels_and_samples(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
    adm_xml: str,
) -> None:
    out = tmp_path / "master.wav"
    assemble_adm_bwf(list(two_stems), adm_xml, chna_entries, out)

    with Bw64Reader(open(out, "rb")) as reader:
        assert reader.channels == 2
        assert reader.sampleRate == SR
        assert reader.bitdepth == 24


def test_axml_chunk_round_trips(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
    adm_xml: str,
) -> None:
    out = tmp_path / "master.wav"
    assemble_adm_bwf(list(two_stems), adm_xml, chna_entries, out)

    with Bw64Reader(open(out, "rb")) as reader:
        recovered = reader.axml.decode("utf-8")

    assert "APR_1001" in recovered
    assert "AP_00031001" in recovered
    assert "ATU_00000001" in recovered


def test_small_file_uses_riff_magic_for_dolby_compat(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
    adm_xml: str,
) -> None:
    """Dolby Atmos Renderer rejects BW64 magic; small files must be plain RIFF."""
    out = tmp_path / "master.wav"
    assemble_adm_bwf(list(two_stems), adm_xml, chna_entries, out)
    with open(out, "rb") as fh:
        assert fh.read(4) == b"RIFF"


def test_chna_chunk_round_trips(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
    adm_xml: str,
) -> None:
    out = tmp_path / "master.wav"
    assemble_adm_bwf(list(two_stems), adm_xml, chna_entries, out)

    with Bw64Reader(open(out, "rb")) as reader:
        ids = reader.chna.audioIDs

    assert len(ids) == 2
    assert ids[0].trackIndex == 1
    assert ids[0].audioTrackUID == "ATU_00000001"
    assert ids[1].trackIndex == 2
    assert ids[1].audioTrackUID == "ATU_00000002"


def test_non_xml_adm_raises(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
) -> None:
    out = tmp_path / "master.wav"
    garbage = "/some/path/attr/_make.py:918: RuntimeWarning: something bad\n  set_closure_cell(cell, cls)\n<?xml ..."
    with pytest.raises(ValueError, match="does not look like XML"):
        assemble_adm_bwf(list(two_stems), garbage, chna_entries, out)


def test_mismatched_stem_and_chna_lengths_raises(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
    adm_xml: str,
) -> None:
    out = tmp_path / "master.wav"
    with pytest.raises(ValueError, match="same length"):
        assemble_adm_bwf([two_stems[0]], adm_xml, chna_entries, out)


def test_wrong_sample_rate_raises(
    tmp_path: Path,
    two_stems: tuple[Path, Path],
    chna_entries: list[AudioID],
    adm_xml: str,
) -> None:
    out = tmp_path / "master.wav"
    with pytest.raises(ValueError, match="sample rate"):
        assemble_adm_bwf(list(two_stems), adm_xml, chna_entries, out, sample_rate=44100)


def test_load_chna_from_json(tmp_path: Path) -> None:
    data = [
        {
            "trackIndex": 1,
            "audioTrackUID": "ATU_00000001",
            "audioTrackFormatIDRef": "AT_00031001_01",
            "audioPackFormatIDRef": "AP_00031001",
        }
    ]
    p = tmp_path / "chna.json"
    p.write_text(json.dumps(data))

    entries = load_chna(p)
    assert len(entries) == 1
    assert entries[0].trackIndex == 1
    assert entries[0].audioTrackUID == "ATU_00000001"


# ---------------------------------------------------------------------------
# Full round-trip: session JSON → XML + chna → ADM BWF → Bw64Reader verify
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"
SR = 48000
N_SAMPLES = SR  # 1 second


@pytest.fixture()
def roundtrip_stems(tmp_path: Path) -> tuple[Path, Path]:
    t = np.linspace(0, 1, N_SAMPLES, endpoint=False, dtype=np.float32)
    stem1 = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    stem2 = (0.4 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)
    p1 = tmp_path / "stem1.wav"
    p2 = tmp_path / "stem2.wav"
    sf.write(str(p1), stem1, SR, subtype="PCM_24")
    sf.write(str(p2), stem2, SR, subtype="PCM_24")
    return p1, p2


def test_session_to_adm_bwf_roundtrip(
    tmp_path: Path, roundtrip_stems: tuple[Path, Path]
) -> None:
    session = load_session(FIXTURES / "minimal_session.json")
    xml = build_adm_xml(session)
    chna_entries = build_chna(session)
    out = tmp_path / "master.wav"

    assemble_adm_bwf(list(roundtrip_stems), xml, chna_entries, out)

    with Bw64Reader(open(out, "rb")) as reader:
        assert reader.channels == 2
        assert reader.sampleRate == SR
        assert reader.bitdepth == 24
        recovered_xml = reader.axml.decode("utf-8")
        chna_ids = reader.chna.audioIDs

    assert "APR_1001" in recovered_xml
    assert "ATU_00000001" in recovered_xml
    assert "ATU_00000002" in recovered_xml
    assert "AP_00031001" in recovered_xml
    assert len(chna_ids) == 2
    assert chna_ids[0].trackIndex == 1
    assert chna_ids[0].audioTrackUID == "ATU_00000001"
    assert chna_ids[1].trackIndex == 2
    assert chna_ids[1].audioTrackUID == "ATU_00000002"
