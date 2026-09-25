"""Session JSON + stems → ADM BWF master in one call."""

from __future__ import annotations

import json
from pathlib import Path

from .adm_xml import build_adm_xml, build_chna
from .session import Session, load_session
from .wav_writer import assemble_adm_bwf


class StemNotFoundError(FileNotFoundError):
    """A session's stemFile wasn't found in any of the searched folders."""


def resolve_stem(stem_file: str, session_dir: Path, stems_dir: Path | None = None) -> Path:
    """Find a session's stemFile on disk.

    With *stems_dir*, look only there. Otherwise look next to the session file,
    then in a ``stems/`` folder beside it (the layout used in ``examples/``).
    """
    if stems_dir is not None:
        candidates = [Path(stems_dir) / stem_file]
    else:
        candidates = [Path(session_dir) / stem_file, Path(session_dir) / "stems" / stem_file]

    for path in candidates:
        if path.is_file():
            return path

    tried = "\n  ".join(str(p) for p in candidates)
    raise StemNotFoundError(f"stem '{stem_file}' not found. Looked in:\n  {tried}")


def encode_session(
    session_path: Path,
    output_path: Path,
    stems_dir: Path | None = None,
    intermediates_dir: Path | None = None,
) -> Session:
    """Encode *session_path* and its stems into an ADM BWF master at *output_path*.

    Every stem is located before anything is written. With *intermediates_dir*,
    the generated ``adm.xml`` and ``chna.json`` are also saved there for inspection.
    Returns the loaded session.
    """
    session_path = Path(session_path)
    session = load_session(session_path)
    stem_paths = [
        resolve_stem(obj.stem_file, session_path.parent, stems_dir) for obj in session.objects
    ]

    adm_xml = build_adm_xml(session)
    chna = build_chna(session)

    if intermediates_dir is not None:
        intermediates_dir = Path(intermediates_dir)
        intermediates_dir.mkdir(parents=True, exist_ok=True)
        (intermediates_dir / "adm.xml").write_text(adm_xml, encoding="utf-8")
        (intermediates_dir / "chna.json").write_text(
            json.dumps(
                [
                    {
                        "trackIndex": e.trackIndex,
                        "audioTrackUID": e.audioTrackUID,
                        "audioTrackFormatIDRef": e.audioTrackFormatIDRef,
                        "audioPackFormatIDRef": e.audioPackFormatIDRef,
                    }
                    for e in chna
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

    assemble_adm_bwf(
        stem_paths,
        adm_xml,
        chna,
        Path(output_path),
        sample_rate=session.session.sample_rate,
        bit_depth=session.session.bit_depth,
    )
    return session
