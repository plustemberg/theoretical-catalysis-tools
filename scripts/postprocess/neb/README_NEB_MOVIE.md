# NEB Movie

`neb_movie.py` creates a movie from the final structures of a VASP NEB calculation stored in numbered folders such as `00`, `01`, `02`, etc.

The script reads one structure per image, renders each frame with ASE + matplotlib, and writes either:

- a GIF (`.gif`)
- or an MP4 (`.mp4`)

By default, it reads `CONTCAR` and writes:

```text
neb_movie.gif
```

This is useful for quickly visualizing the sequence of final NEB images without opening a structure viewer.

## Recommended location in the repository

```text
scripts/postprocess/neb/
```

## Script name

```text
neb_movie.py
```

## Requirements

Minimum requirements:

- Python 3
- ASE
- NumPy
- matplotlib
- imageio

Install them with:

```bash
python3 -m pip install --user ase numpy matplotlib imageio
```

For MP4 output, you may also need:

```bash
python3 -m pip install --user imageio-ffmpeg
```

## Expected directory structure

Run the script from a NEB directory containing numbered folders such as:

```text
neb_calculation/
├── 00/
│   └── CONTCAR
├── 01/
│   └── CONTCAR
├── 02/
│   └── CONTCAR
...
└── 07/
    └── CONTCAR
```

## Basic usage

### Default GIF from `CONTCAR`

```bash
python3 neb_movie.py
```

This writes:

```text
neb_movie.gif
```

### Choose the output file explicitly

```bash
python3 neb_movie.py --output my_neb.gif
```

### Write MP4 instead of GIF

```bash
python3 neb_movie.py --output my_neb.mp4
```

## Useful options

### Use `POSCAR` instead of `CONTCAR`

```bash
python3 neb_movie.py --filename POSCAR
```

### Fall back to `POSCAR` if `CONTCAR` is missing

```bash
python3 neb_movie.py --fallback-poscar
```

### Rotate the view

```bash
python3 neb_movie.py --rotation "-80x,20y,0z"
```

### Change frame duration

```bash
python3 neb_movie.py --interval 500
```

`--interval` is given in milliseconds.

### Add a back-and-forth animation

```bash
python3 neb_movie.py --pingpong
```

### Hide image labels

```bash
python3 neb_movie.py --no-labels
```

### Show the simulation cell

```bash
python3 neb_movie.py --show-cell
```

### Also write an `extxyz` trajectory

```bash
python3 neb_movie.py --write-extxyz
```

This additionally writes:

```text
neb_images.extxyz
```

## Output description

### GIF or MP4 movie

The frames are rendered from the final structures in the numbered NEB folders.

By default, each frame contains:

- the atomic structure
- a fixed viewing window for all images
- the image label (`00`, `01`, `02`, ...)

### Optional `neb_images.extxyz`

If `--write-extxyz` is used, the script also writes a trajectory file that can be opened with OVITO or other tools.

## Notes

- The script assumes that the numbered folders correspond to the NEB image order.
- The movie is generated from the final structures only.
- The same global frame limits are used for all images so that the view does not jump between frames.
- For MP4 output, an ffmpeg backend may be required through `imageio-ffmpeg`.

## Example commands

### Simple GIF

```bash
python3 neb_movie.py
```

### GIF with rotation and ping-pong effect

```bash
python3 neb_movie.py --rotation "-80x,20y,0z" --pingpong --output neb_movie.gif
```

### MP4 with visible cell

```bash
python3 neb_movie.py --output neb_movie.mp4 --show-cell
```

### Write movie and trajectory

```bash
python3 neb_movie.py --output neb_movie.gif --write-extxyz
```
