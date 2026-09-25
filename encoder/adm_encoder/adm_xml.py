"""Generate Dolby Atmos Profile-conformant ADM XML from a Session object."""

from __future__ import annotations

from lxml import etree as ET

from ear.fileio.bw64.chunks import AudioID

from .coordinates import unity_to_adm
from .session import Session

_EBU_NS = "urn:ebu:metadata-schema:ebuCore_2014"
_NSMAP = {None: _EBU_NS}

# ITU-R BS.2076 reserves IDs in the range XXXX_0001..XXXX_0FFF for common /
# predefined elements. User-defined content must start at index 0x1001, as Dolby's
# own ADM masters do. MediaInfo and Dolby Atmos Renderer flag user IDs in the
# reserved range as "not a known value."
_USER_INDEX_BASE = 0x1000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_adm_xml(session: Session) -> str:
    """Return a Dolby-profile ADM XML string generated from *session*."""
    root = ET.Element("ebuCoreMain", nsmap=_NSMAP)
    core = ET.SubElement(root, "coreMetadata")
    fmt = ET.SubElement(core, "format")
    afe = ET.SubElement(fmt, "audioFormatExtended")
    afe.set("version", "ITU-R_BS.2076-2")

    meta = session.session
    end_time = _adm_time(meta.duration)

    # --- audioProgramme ---
    prog = ET.SubElement(afe, "audioProgramme")
    prog.set("audioProgrammeID", "APR_1001")
    prog.set("audioProgrammeName", meta.title)
    prog.set("start", "00:00:00.00000")
    prog.set("end", end_time)
    ET.SubElement(prog, "audioContentIDRef").text = "ACO_1001"

    # --- audioContent ---
    content = ET.SubElement(afe, "audioContent")
    content.set("audioContentID", "ACO_1001")
    content.set("audioContentName", meta.title)
    for i, obj in enumerate(session.objects, start=1):
        ET.SubElement(content, "audioObjectIDRef").text = f"AO_{i + _USER_INDEX_BASE:04x}"
    dialogue = ET.SubElement(content, "dialogue")
    dialogue.set("mixedContentKind", "0")
    dialogue.text = "2"

    # --- per-object elements ---
    for i, obj in enumerate(session.objects, start=1):
        idx = i + _USER_INDEX_BASE
        obj_id = f"AO_{idx:04x}"
        pack_id = f"AP_0003{idx:04x}"
        chan_id = f"AC_0003{idx:04x}"
        stream_id = f"AS_0003{idx:04x}"
        track_fmt_id = f"AT_0003{idx:04x}_01"
        uid = f"ATU_{i:08x}"

        # audioObject
        ao = ET.SubElement(afe, "audioObject")
        ao.set("audioObjectID", obj_id)
        ao.set("audioObjectName", obj.name)
        ao.set("start", _adm_time(obj.start))
        ao.set("duration", _adm_time(obj.duration))
        ET.SubElement(ao, "audioPackFormatIDRef").text = pack_id
        ET.SubElement(ao, "audioTrackUIDRef").text = uid

        # audioPackFormat
        apf = ET.SubElement(afe, "audioPackFormat")
        apf.set("audioPackFormatID", pack_id)
        apf.set("audioPackFormatName", obj.name)
        apf.set("typeDefinition", "Objects")
        apf.set("typeLabel", "0003")
        ET.SubElement(apf, "audioChannelFormatIDRef").text = chan_id

        # audioChannelFormat + audioBlockFormats
        acf = ET.SubElement(afe, "audioChannelFormat")
        acf.set("audioChannelFormatID", chan_id)
        acf.set("audioChannelFormatName", obj.name)
        acf.set("typeDefinition", "Objects")
        acf.set("typeLabel", "0003")

        for b_idx, blk in enumerate(obj.blocks, start=1):
            block_id = f"AB_0003{idx:04x}_{b_idx:08x}"
            adm_x, adm_y, adm_z = unity_to_adm(blk.x, blk.y, blk.z, meta.scene_radius)

            abf = ET.SubElement(acf, "audioBlockFormat")
            abf.set("audioBlockFormatID", block_id)
            abf.set("rtime", _adm_time(blk.rtime))
            abf.set("duration", _adm_time(blk.duration))

            ET.SubElement(abf, "cartesian").text = "1"
            ET.SubElement(abf, "position", coordinate="X").text = f"{adm_x:.10f}"
            ET.SubElement(abf, "position", coordinate="Y").text = f"{adm_y:.10f}"
            if abs(adm_z) > 1e-6:
                ET.SubElement(abf, "position", coordinate="Z").text = f"{adm_z:.10f}"

            if abs(blk.gain - 1.0) > 1e-9:
                gain_el = ET.SubElement(abf, "gain")
                gain_el.set("gainUnit", "linear")
                gain_el.text = f"{blk.gain:.10f}"

            interp = "0.000000" if b_idx == 1 else "0.005208"
            jp = ET.SubElement(abf, "jumpPosition")
            jp.set("interpolationLength", interp)
            jp.text = "1"

        # audioStreamFormat
        asf = ET.SubElement(afe, "audioStreamFormat")
        asf.set("audioStreamFormatID", stream_id)
        asf.set("audioStreamFormatName", f"PCM_{obj.name}")
        asf.set("formatDefinition", "PCM")
        asf.set("formatLabel", "0001")
        ET.SubElement(asf, "audioChannelFormatIDRef").text = chan_id
        ET.SubElement(asf, "audioPackFormatIDRef").text = pack_id
        ET.SubElement(asf, "audioTrackFormatIDRef").text = track_fmt_id

        # audioTrackFormat
        atf = ET.SubElement(afe, "audioTrackFormat")
        atf.set("audioTrackFormatID", track_fmt_id)
        atf.set("audioTrackFormatName", f"PCM_{obj.name}")
        atf.set("formatDefinition", "PCM")
        atf.set("formatLabel", "0001")
        ET.SubElement(atf, "audioStreamFormatIDRef").text = stream_id

        # audioTrackUID
        atu = ET.SubElement(afe, "audioTrackUID")
        atu.set("UID", uid)
        atu.set("bitDepth", str(meta.bit_depth))
        atu.set("sampleRate", str(meta.sample_rate))
        ET.SubElement(atu, "audioTrackFormatIDRef").text = track_fmt_id
        ET.SubElement(atu, "audioPackFormatIDRef").text = pack_id

    return ET.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")


def build_chna(session: Session) -> list[AudioID]:
    """Return chna entries ordered by 1-based track index (one per object)."""
    entries = []
    for i, _ in enumerate(session.objects, start=1):
        idx = i + _USER_INDEX_BASE
        entries.append(
            AudioID(
                trackIndex=i,
                audioTrackUID=f"ATU_{i:08x}",
                audioTrackFormatIDRef=f"AT_0003{idx:04x}_01",
                audioPackFormatIDRef=f"AP_0003{idx:04x}",
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _adm_time(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:08.5f}"
