# Cmaj7 demo

Four 30-second stems (the notes C3, E3, G3 and B3 of a Cmaj7 chord), each on its own object. They were moved with **Simple Orbit** in Unity and recorded with this repo's package into `session.json`.

## Encode it

From the repository root, after `pip install ./encoder`:

```bash
adm-encode examples/cmaj7-demo/session.json -o cmaj7-demo.wav
```

The stems are found automatically in `stems/` next to the session.

## Listen

Open `cmaj7-demo.wav` in the Dolby Atmos Renderer, or a DAW or plugin that imports ADM BWF. Each note is a separate object, so you can solo them and watch each one follow its recorded path.

## License

The audio in `stems/` is CC BY 4.0 (see [LICENSE](LICENSE)). The rest of the repository is Apache 2.0.
