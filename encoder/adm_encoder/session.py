"""Load and validate the Unity session JSON (object list, stem paths, per-object position blocks)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Block:
    rtime: float
    duration: float
    x: float
    y: float
    z: float
    gain: float = 1.0


@dataclass
class AudioObject:
    id: str
    name: str
    stem_file: str
    gain: float
    start: float
    duration: float
    blocks: list[Block]


@dataclass
class SessionMeta:
    title: str
    sample_rate: int
    bit_depth: int
    duration: float
    block_duration_samples: int
    scene_radius: float


@dataclass
class Session:
    version: str
    session: SessionMeta
    objects: list[AudioObject]


def load_session(path: Path) -> Session:
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    meta_raw = raw["session"]
    meta = SessionMeta(
        title=meta_raw["title"],
        sample_rate=meta_raw["sampleRate"],
        bit_depth=meta_raw["bitDepth"],
        duration=float(meta_raw["duration"]),
        block_duration_samples=meta_raw["blockDurationSamples"],
        scene_radius=float(meta_raw["sceneRadius"]),
    )
    objects = []
    for obj_raw in raw["objects"]:
        blocks = [
            Block(
                rtime=float(b["rtime"]),
                duration=float(b["duration"]),
                x=float(b["x"]),
                y=float(b["y"]),
                z=float(b["z"]),
                gain=float(b.get("gain", 1.0)),
            )
            for b in obj_raw["blocks"]
        ]
        objects.append(
            AudioObject(
                id=obj_raw["id"],
                name=obj_raw["name"],
                stem_file=obj_raw["stemFile"],
                gain=float(obj_raw.get("gain", 1.0)),
                start=float(obj_raw.get("start", 0.0)),
                duration=float(obj_raw["duration"]),
                blocks=blocks,
            )
        )
    session = Session(version=raw["version"], session=meta, objects=objects)
    _validate(session)
    return session


def _validate(session: Session) -> None:
    meta = session.session
    if meta.sample_rate != 48000:
        raise ValueError(f"sampleRate must be 48000, got {meta.sample_rate}")
    if meta.bit_depth not in {16, 24, 32}:
        raise ValueError(f"bitDepth must be 16, 24, or 32, got {meta.bit_depth}")
    if meta.scene_radius <= 0:
        raise ValueError(f"sceneRadius must be > 0, got {meta.scene_radius}")
    if meta.block_duration_samples <= 0:
        raise ValueError(f"blockDurationSamples must be > 0, got {meta.block_duration_samples}")
    if not session.objects:
        raise ValueError("session must contain at least one object")
    for obj in session.objects:
        if not obj.blocks:
            raise ValueError(f"object '{obj.id}' has no blocks")
        for blk in obj.blocks:
            if blk.gain < 0:
                raise ValueError(f"block gain must be >= 0, got {blk.gain} in object '{obj.id}'")
