"""Tests for adm_xml.py — Dolby-profile ADM XML emitter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from lxml import etree as ET

from adm_encoder.adm_xml import _adm_time, build_adm_xml, build_chna
from adm_encoder.session import AudioObject, Block, Session, SessionMeta

NS = "urn:ebu:metadata-schema:ebuCore_2014"


def _make_session(
    objects: list[AudioObject] | None = None,
    scene_radius: float = 20.0,
    duration: float = 10.0,
) -> Session:
    if objects is None:
        objects = [
            AudioObject(
                id="obj_0001",
                name="Pad",
                stem_file="stems/pad.wav",
                gain=1.0,
                start=0.0,
                duration=duration,
                blocks=[
                    Block(rtime=0.0, duration=5.0, x=-14.0, y=0.0, z=0.0, gain=0.8),
                    Block(rtime=5.0, duration=5.0, x=14.0, y=0.0, z=0.0, gain=1.0),
                ],
            ),
            AudioObject(
                id="obj_0002",
                name="Hi-Hat",
                stem_file="stems/hihat.wav",
                gain=1.0,
                start=0.0,
                duration=duration,
                blocks=[Block(rtime=0.0, duration=duration, x=0.0, y=0.0, z=10.0)],
            ),
        ]
    return Session(
        version="1.0",
        session=SessionMeta(
            title="Test Track",
            sample_rate=48000,
            bit_depth=24,
            duration=duration,
            block_duration_samples=250,
            scene_radius=scene_radius,
        ),
        objects=objects,
    )


def _parse(xml_str: str) -> ET._Element:
    return ET.fromstring(xml_str.encode("utf-8"))


# --- XML validity ---


def test_output_is_valid_xml() -> None:
    session = _make_session()
    xml = build_adm_xml(session)
    root = _parse(xml)
    assert root is not None


def test_xml_declaration_present() -> None:
    xml = build_adm_xml(_make_session())
    assert xml.startswith("<?xml")


# --- Element counts ---


def test_correct_number_of_audio_objects() -> None:
    session = _make_session()
    root = _parse(build_adm_xml(session))
    objs = root.findall(f".//{{{NS}}}audioObject")
    assert len(objs) == 2


def test_correct_number_of_pack_formats() -> None:
    session = _make_session()
    root = _parse(build_adm_xml(session))
    packs = root.findall(f".//{{{NS}}}audioPackFormat")
    assert len(packs) == 2


def test_correct_number_of_channel_formats() -> None:
    session = _make_session()
    root = _parse(build_adm_xml(session))
    chans = root.findall(f".//{{{NS}}}audioChannelFormat")
    assert len(chans) == 2


def test_correct_number_of_block_formats() -> None:
    session = _make_session()
    root = _parse(build_adm_xml(session))
    # obj 0001 has 2 blocks, obj 0002 has 1 block
    blocks = root.findall(f".//{{{NS}}}audioBlockFormat")
    assert len(blocks) == 3


# --- IDs ---


def test_programme_id() -> None:
    root = _parse(build_adm_xml(_make_session()))
    prog = root.find(f".//{{{NS}}}audioProgramme")
    assert prog.get("audioProgrammeID") == "APR_1001"


def test_object_ids() -> None:
    root = _parse(build_adm_xml(_make_session()))
    ids = [o.get("audioObjectID") for o in root.findall(f".//{{{NS}}}audioObject")]
    assert ids == ["AO_1001", "AO_1002"]


def test_pack_format_ids() -> None:
    root = _parse(build_adm_xml(_make_session()))
    ids = [p.get("audioPackFormatID") for p in root.findall(f".//{{{NS}}}audioPackFormat")]
    assert ids == ["AP_00031001", "AP_00031002"]


def test_track_uid_ids() -> None:
    root = _parse(build_adm_xml(_make_session()))
    ids = [u.get("UID") for u in root.findall(f".//{{{NS}}}audioTrackUID")]
    assert ids == ["ATU_00000001", "ATU_00000002"]


# --- Time formatting ---


def test_adm_time_zero() -> None:
    assert _adm_time(0.0) == "00:00:00.00000"


def test_adm_time_minutes() -> None:
    assert _adm_time(90.0) == "00:01:30.00000"


def test_adm_time_hours() -> None:
    assert _adm_time(3661.5) == "01:01:01.50000"


def test_adm_time_rounds_up_into_next_minute() -> None:
    assert _adm_time(59.999996) == "00:01:00.00000"


def test_adm_time_rounds_up_into_next_hour() -> None:
    assert _adm_time(3599.999999) == "01:00:00.00000"


def test_programme_end_time() -> None:
    root = _parse(build_adm_xml(_make_session(duration=10.0)))
    prog = root.find(f".//{{{NS}}}audioProgramme")
    assert prog.get("end") == "00:00:10.00000"


# --- Coordinate conversion in XML ---


def test_block_x_coordinate_remapped() -> None:
    # Unity x=-14, sceneRadius=20 → ADM X=-0.7
    session = _make_session()
    root = _parse(build_adm_xml(session))
    chan = root.findall(f".//{{{NS}}}audioChannelFormat")[0]
    first_block = chan.findall(f"{{{NS}}}audioBlockFormat")[0]
    x_pos = first_block.find(f"{{{NS}}}position[@coordinate='X']")
    assert float(x_pos.text) == pytest.approx(-0.7, abs=1e-6)


def test_block_y_coordinate_from_unity_z() -> None:
    # Unity z=10, sceneRadius=20 → ADM Y=0.5
    session = _make_session()
    root = _parse(build_adm_xml(session))
    # obj_0002 has z=10
    chan = root.findall(f".//{{{NS}}}audioChannelFormat")[1]
    block = chan.find(f"{{{NS}}}audioBlockFormat")
    y_pos = block.find(f"{{{NS}}}position[@coordinate='Y']")
    assert float(y_pos.text) == pytest.approx(0.5, abs=1e-6)


def test_z_position_omitted_when_zero() -> None:
    session = _make_session()
    root = _parse(build_adm_xml(session))
    chan = root.findall(f".//{{{NS}}}audioChannelFormat")[0]
    first_block = chan.findall(f"{{{NS}}}audioBlockFormat")[0]
    z_pos = first_block.find(f"{{{NS}}}position[@coordinate='Z']")
    assert z_pos is None


def test_z_position_present_when_nonzero() -> None:
    objects = [
        AudioObject(
            id="obj_0001",
            name="High",
            stem_file="s.wav",
            gain=1.0,
            start=0.0,
            duration=5.0,
            blocks=[Block(rtime=0.0, duration=5.0, x=0.0, y=10.0, z=0.0)],  # Unity Y=10 → ADM Z
        )
    ]
    session = _make_session(objects=objects)
    root = _parse(build_adm_xml(session))
    block = root.find(f".//{{{NS}}}audioBlockFormat")
    z_pos = block.find(f"{{{NS}}}position[@coordinate='Z']")
    assert z_pos is not None
    assert float(z_pos.text) == pytest.approx(0.5, abs=1e-6)


# --- jumpPosition ---


def test_first_block_interpolation_length_zero() -> None:
    root = _parse(build_adm_xml(_make_session()))
    chan = root.findall(f".//{{{NS}}}audioChannelFormat")[0]
    first_block = chan.findall(f"{{{NS}}}audioBlockFormat")[0]
    jp = first_block.find(f"{{{NS}}}jumpPosition")
    assert jp.get("interpolationLength") == "0.000000"
    assert jp.text == "1"


def test_second_block_interpolation_length_frame() -> None:
    root = _parse(build_adm_xml(_make_session()))
    chan = root.findall(f".//{{{NS}}}audioChannelFormat")[0]
    second_block = chan.findall(f"{{{NS}}}audioBlockFormat")[1]
    jp = second_block.find(f"{{{NS}}}jumpPosition")
    assert jp.get("interpolationLength") == "0.005208"


# --- gain ---


def test_gain_element_absent_when_one() -> None:
    # obj_0002's single block has gain=1.0 (default)
    root = _parse(build_adm_xml(_make_session()))
    chan = root.findall(f".//{{{NS}}}audioChannelFormat")[1]
    block = chan.find(f"{{{NS}}}audioBlockFormat")
    assert block.find(f"{{{NS}}}gain") is None


def test_gain_element_present_when_not_one() -> None:
    # obj_0001 first block has gain=0.8
    root = _parse(build_adm_xml(_make_session()))
    chan = root.findall(f".//{{{NS}}}audioChannelFormat")[0]
    first_block = chan.findall(f"{{{NS}}}audioBlockFormat")[0]
    gain_el = first_block.find(f"{{{NS}}}gain")
    assert gain_el is not None
    assert gain_el.get("gainUnit") == "linear"
    assert float(gain_el.text) == pytest.approx(0.8, abs=1e-9)


# --- build_chna ---


def test_chna_length_matches_objects() -> None:
    session = _make_session()
    chna = build_chna(session)
    assert len(chna) == 2


def test_chna_track_indices() -> None:
    chna = build_chna(_make_session())
    assert chna[0].trackIndex == 1
    assert chna[1].trackIndex == 2


def test_chna_uids() -> None:
    chna = build_chna(_make_session())
    assert chna[0].audioTrackUID == "ATU_00000001"
    assert chna[1].audioTrackUID == "ATU_00000002"


def test_chna_pack_refs() -> None:
    chna = build_chna(_make_session())
    assert chna[0].audioPackFormatIDRef == "AP_00031001"
    assert chna[1].audioPackFormatIDRef == "AP_00031002"


def test_chna_track_format_refs() -> None:
    chna = build_chna(_make_session())
    assert chna[0].audioTrackFormatIDRef == "AT_00031001_01"
    assert chna[1].audioTrackFormatIDRef == "AT_00031002_01"
