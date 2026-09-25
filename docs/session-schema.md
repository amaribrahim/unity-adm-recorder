# Session format (v1.0)

`session.json` is the only thing the Unity recorder and the encoder share. Anything that writes this format can be encoded with `adm-encode`.

## Example

```json
{
  "version": "1.0",
  "session": {
    "title": "My Session",
    "sampleRate": 48000,
    "bitDepth": 24,
    "duration": 30.0,
    "blockDurationSamples": 2400,
    "sceneRadius": 20.0
  },
  "objects": [
    {
      "id": "obj_0001",
      "name": "Pad",
      "stemFile": "pad.wav",
      "gain": 1.0,
      "start": 0.0,
      "duration": 30.0,
      "blocks": [
        { "rtime": 0.0, "duration": 0.5, "x": -14.0, "y": 0.0, "z": 0.0, "gain": 1.0 },
        { "rtime": 0.5, "duration": 29.5, "x": -10.0, "y": 2.0, "z": 5.0, "gain": 1.0 }
      ]
    }
  ]
}
```

## `session`

| Field | Type | Meaning |
|---|---|---|
| `title` | string | Programme and content name in the ADM metadata. |
| `sampleRate` | int | Must be `48000`. |
| `bitDepth` | int | `16`, `24` or `32`. Bit depth of the output master (Atmos masters use 24). |
| `duration` | float, seconds | Length of the programme. |
| `blockDurationSamples` | int, > 0 | The recorder's block interval for stationary objects. Kept for reference; the encoder uses each block's own `rtime` and `duration`. |
| `sceneRadius` | float, meters, > 0 | Distance from the origin that maps to the edge of the ADM room (±1). |

## `objects[]`

One entry per stem. The order becomes the track order in the master. There must be at least one object.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Recorder's ID (`obj_0001`, …). Informational. |
| `name` | string | Object name in the ADM metadata. The Unity playback driver also matches objects by this name. |
| `stemFile` | string | Stem file name (or relative path). See *Finding stems* below. |
| `gain` | float | Object gain. Currently always `1.0`. |
| `start` | float, seconds | Object start time. |
| `duration` | float, seconds | Object length. |
| `blocks` | array | At least one position block. |

## `blocks[]`

Each block says where the object is from `rtime` for `duration` seconds.

| Field | Type | Meaning |
|---|---|---|
| `rtime` | float, seconds | Block start, relative to the object's start. |
| `duration` | float, seconds | Block length. |
| `x`, `y`, `z` | float, meters | Position in Unity world space (see below). |
| `gain` | float, ≥ 0 | Block gain. Written to the ADM only when it isn't `1.0`. The Unity recorder always writes `1.0`. |

## Coordinates

Positions are Unity world space: left-handed, **Y up**, X right, Z forward, in meters, with the listener at the origin. The encoder converts them to ADM Cartesian coordinates (ITU-R BS.2076), where Y is front/back and Z is up/down:

| ADM | from Unity |
|---|---|
| X (left −1 … right +1) | `x / sceneRadius` |
| Y (back −1 … front +1) | `z / sceneRadius` |
| Z (down −1 … up +1) | `y / sceneRadius` |

Each value is clamped to [−1, 1], so anything beyond `sceneRadius` sits on the edge of the room.

In the ADM output, the first block of each object jumps straight to its position. Later blocks ramp from the previous position over about 5 ms (`jumpPosition interpolationLength="0.005208"`).

## Finding stems

`adm-encode` resolves each `stemFile`:

1. in `--stems-dir`, if given (and nowhere else), otherwise
2. next to `session.json`, then
3. in a `stems/` folder beside `session.json`.

Stems must be mono, 48 kHz and all the same length. Any format libsndfile reads works (WAV, AIFF, FLAC, OGG).
