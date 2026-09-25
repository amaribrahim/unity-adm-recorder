"""Assemble mono WAV stems + ADM XML + chna mapping into an ADM BWF master WAV."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf
from ear.fileio.bw64 import Bw64Writer
from ear.fileio.bw64.chunks import AudioID, ChnaChunk, FormatInfoChunk


def load_chna(path: Path) -> list[AudioID]:
    """Load chna entries from a JSON file.

    Expected format — list of objects:
      [{"trackIndex": 1, "audioTrackUID": "ATU_00000001",
        "audioTrackFormatIDRef": "AT_00031001_01",
        "audioPackFormatIDRef": "AP_00031001"}, ...]
    """
    data = json.loads(path.read_text())
    return [
        AudioID(
            trackIndex=e["trackIndex"],
            audioTrackUID=e["audioTrackUID"],
            audioTrackFormatIDRef=e["audioTrackFormatIDRef"],
            audioPackFormatIDRef=e["audioPackFormatIDRef"],
        )
        for e in data
    ]


def assemble_adm_bwf(
    stem_paths: list[Path],
    adm_xml: str,
    chna_entries: list[AudioID],
    output_path: Path,
    sample_rate: int = 48000,
    bit_depth: int = 24,
) -> None:
    """Write an ADM BWF master WAV from mono stems + pre-written ADM XML.

    Args:
        stem_paths:   Ordered list of mono WAV paths. Order must match
                      trackIndex in chna_entries (1-based).
        adm_xml:      Complete ADM XML string (UTF-8). Must be valid.
        chna_entries: One AudioID per stem, in the same order as stem_paths.
        output_path:  Destination .wav path.
        sample_rate:  Must match all stems and the audioTrackUID sampleRate.
        bit_depth:    24 or 32. Dolby Atmos Profile requires 24-bit.
    """
    if len(stem_paths) != len(chna_entries):
        raise ValueError(
            f"stem_paths ({len(stem_paths)}) and chna_entries ({len(chna_entries)}) "
            "must have the same length"
        )

    stripped = adm_xml.lstrip()
    if not (stripped.startswith("<?xml") or stripped.startswith("<")):
        raise ValueError(
            "adm_xml does not look like XML — starts with: " + repr(adm_xml[:80])
        )

    stems: list[np.ndarray] = []
    for path in stem_paths:
        audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if sr != sample_rate:
            raise ValueError(f"{path}: sample rate {sr} != expected {sample_rate}")
        if audio.ndim != 1:
            raise ValueError(f"{path}: expected mono (1 channel), got {audio.ndim}D")
        stems.append(audio)

    lengths = [s.shape[0] for s in stems]
    if len(set(lengths)) != 1:
        raise ValueError(
            f"Stems have different lengths: {dict(zip(stem_paths, lengths))}"
        )

    # (n_samples, n_channels) — what Bw64Writer.write expects
    audio_block = np.column_stack(stems)

    n_channels = len(stems)
    fmt = FormatInfoChunk(
        channelCount=n_channels,
        sampleRate=sample_rate,
        bitsPerSample=bit_depth,
    )
    chna = ChnaChunk(audioIDs=chna_entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as fh:
        with Bw64Writer(
            fh,
            formatInfo=fmt,
            chna=chna,
            axml=adm_xml.encode("utf-8"),
        ) as writer:
            writer.write(audio_block)
