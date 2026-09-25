"""adm-encode: session JSON + mono stems → ADM BWF master."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import encode_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="adm-encode",
        description="Encode a recorded session JSON and its mono 48 kHz stems into an ADM BWF master.",
    )
    parser.add_argument("session", type=Path, help="session.json written by the Unity recorder")
    parser.add_argument("-o", "--output", type=Path, required=True, help="output ADM BWF .wav path")
    parser.add_argument(
        "--stems-dir",
        type=Path,
        metavar="DIR",
        help="folder holding the stems (default: next to the session file, then its stems/ subfolder)",
    )
    parser.add_argument(
        "--keep-intermediates",
        type=Path,
        metavar="DIR",
        help="also write the generated adm.xml and chna.json to DIR",
    )
    args = parser.parse_args(argv)

    if not args.session.is_file():
        print(f"error: session not found: {args.session}", file=sys.stderr)
        return 1

    try:
        session = encode_session(
            args.session,
            args.output,
            stems_dir=args.stems_dir,
            intermediates_dir=args.keep_intermediates,
        )
    except KeyError as exc:
        print(f"error: session JSON is missing field {exc}", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    meta = session.session
    print(f"Wrote {args.output} ({len(session.objects)} objects, {meta.duration:.1f} s, {meta.bit_depth}-bit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
