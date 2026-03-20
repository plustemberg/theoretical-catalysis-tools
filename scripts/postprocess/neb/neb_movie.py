#!/usr/bin/env python3
"""
neb_movie.py

Create a movie (GIF or MP4) from final NEB image structures stored in numbered
directories such as 00, 01, 02, ...

By default the script reads CONTCAR files, renders one frame per NEB image using
ASE + matplotlib, and writes a GIF called neb_movie.gif.

Examples
--------
python3 neb_movie.py
python3 neb_movie.py --output neb_movie.gif
python3 neb_movie.py --output neb_movie.mp4
python3 neb_movie.py --filename POSCAR
python3 neb_movie.py --rotation "-80x,20y,0z" --interval 500
python3 neb_movie.py --pingpong --output neb_movie.gif
python3 neb_movie.py --fallback-poscar --write-extxyz
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

import numpy as np
from ase.io import read, write
from ase.visualize.plot import plot_atoms
from ase.data import covalent_radii
import matplotlib.pyplot as plt

try:
    import imageio.v2 as imageio
except Exception as exc:
    print("ERROR: imageio is required. Install it with:")
    print("  python3 -m pip install --user imageio")
    raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a GIF or MP4 movie from final NEB image structures."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory containing numbered NEB folders (default: current directory).",
    )
    parser.add_argument(
        "--filename",
        default="CONTCAR",
        help="Structure filename inside each NEB image directory (default: CONTCAR).",
    )
    parser.add_argument(
        "--fallback-poscar",
        action="store_true",
        help="If the selected filename is missing, try POSCAR as fallback.",
    )
    parser.add_argument(
        "--output",
        default="neb_movie.gif",
        help="Output movie file (.gif or .mp4). Default: neb_movie.gif",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=400,
        help="Frame duration in milliseconds for GIF, or converted to FPS for MP4 (default: 400).",
    )
    parser.add_argument(
        "--rotation",
        default="",
        help='Rotation to apply before plotting, e.g. "-80x,20y,0z"',
    )
    parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Frame width in pixels (default: 800).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=600,
        help="Frame height in pixels (default: 600).",
    )
    parser.add_argument(
        "--fontsize",
        type=int,
        default=18,
        help="Font size for image labels (default: 18).",
    )
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="Do not write image labels (00, 01, 02, ...) on frames.",
    )
    parser.add_argument(
        "--show-cell",
        action="store_true",
        help="Display the simulation cell in the frames.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.90,
        help="Atom radius scale passed to plot_atoms (default: 0.90).",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=1.5,
        help="Extra margin in Angstrom added around the global 2D frame bounds (default: 1.5).",
    )
    parser.add_argument(
        "--pingpong",
        action="store_true",
        help="Append the reverse sequence (excluding endpoints) to create a back-and-forth movie.",
    )
    parser.add_argument(
        "--write-extxyz",
        action="store_true",
        help="Also write neb_images.extxyz with the loaded structures.",
    )
    return parser.parse_args()


def find_image_dirs(root: Path):
    dirs = [p for p in root.iterdir() if p.is_dir() and re.fullmatch(r"\d+", p.name)]
    dirs.sort(key=lambda p: int(p.name))
    return dirs


def load_images(root: Path, filename: str, fallback_poscar: bool):
    images = []
    labels = []

    for d in find_image_dirs(root):
        primary = d / filename
        chosen = None
        if primary.is_file():
            chosen = primary
        elif fallback_poscar and filename != "POSCAR" and (d / "POSCAR").is_file():
            chosen = d / "POSCAR"

        if chosen is None:
            continue

        atoms = read(str(chosen))
        images.append(atoms)
        labels.append(d.name)

    return images, labels


def apply_rotation(atoms, rotation_spec: str):
    rotated = atoms.copy()
    spec = rotation_spec.strip()
    if not spec:
        return rotated

    tokens = [tok.strip() for tok in spec.split(",") if tok.strip()]
    pat = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*([xyzXYZ])\s*$")

    for token in tokens:
        m = pat.match(token)
        if not m:
            raise ValueError(
                f"Invalid rotation token '{token}'. Use forms like 90x, -80x, 20y, 10z"
            )
        angle = float(m.group(1))
        axis = m.group(2).lower()
        rotated.rotate(angle, axis, center="COP", rotate_cell=True)
    return rotated


def global_bounds(rotated_images, show_cell=False):
    xmin = ymin = np.inf
    xmax = ymax = -np.inf
    max_r = 0.0

    for atoms in rotated_images:
        pos = atoms.get_positions()
        if len(pos) == 0:
            continue

        x = pos[:, 0]
        y = pos[:, 1]

        nums = atoms.get_atomic_numbers()
        radii = covalent_radii[nums]
        if len(radii):
            max_r = max(max_r, float(np.max(radii)))

        xmin = min(xmin, float(np.min(x)))
        xmax = max(xmax, float(np.max(x)))
        ymin = min(ymin, float(np.min(y)))
        ymax = max(ymax, float(np.max(y)))

        if show_cell:
            cell = atoms.cell.array
            corners = np.array([
                [0, 0, 0],
                cell[0],
                cell[1],
                cell[0] + cell[1],
            ])
            xmin = min(xmin, float(np.min(corners[:, 0])))
            xmax = max(xmax, float(np.max(corners[:, 0])))
            ymin = min(ymin, float(np.min(corners[:, 1])))
            ymax = max(ymax, float(np.max(corners[:, 1])))

    if not np.isfinite([xmin, xmax, ymin, ymax]).all():
        raise ValueError("Could not determine plot bounds from the loaded structures.")

    return xmin, xmax, ymin, ymax, max_r


def render_frame(atoms, label, bounds, width, height, show_cell, scale, margin, fontsize, show_labels):
    xmin, xmax, ymin, ymax, max_r = bounds

    dpi = 100
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax = fig.add_subplot(111)

    plot_atoms(
        atoms,
        ax=ax,
        radii=scale,
        rotation="",
        show_unit_cell=2 if show_cell else 0,
    )

    pad = margin + max_r
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_aspect("equal")
    ax.axis("off")

    if show_labels:
        ax.text(
            0.03, 0.95, label,
            transform=ax.transAxes,
            ha="left", va="top",
            fontsize=fontsize,
            bbox=dict(facecolor="white", alpha=0.75, edgecolor="none", pad=3),
        )

    buf = io.BytesIO()
    fig.tight_layout(pad=0)
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)
    return imageio.imread(buf)


def write_movie(frames, output_path: Path, interval_ms: int):
    suffix = output_path.suffix.lower()

    if suffix == ".gif":
        duration_s = interval_ms / 1000.0
        imageio.mimsave(output_path, frames, duration=duration_s, loop=0)
        return

    if suffix == ".mp4":
        fps = 1000.0 / interval_ms
        try:
            with imageio.get_writer(output_path, fps=fps, codec="libx264") as writer:
                for frame in frames:
                    writer.append_data(frame)
        except Exception as exc:
            raise RuntimeError(
                "Failed to write MP4. You may need the imageio ffmpeg backend.\n"
                "Try:\n"
                "  python3 -m pip install --user imageio imageio-ffmpeg\n"
                f"Original error: {exc}"
            )
        return

    raise ValueError("Output extension must be .gif or .mp4")


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)

    if not root.is_dir():
        print(f"ERROR: root directory does not exist: {root}")
        sys.exit(1)

    images, labels = load_images(root, args.filename, args.fallback_poscar)
    if not images:
        print("ERROR: no structures found in numbered image folders.")
        sys.exit(1)

    try:
        rotated_images = [apply_rotation(at, args.rotation) for at in images]
    except Exception as exc:
        print(f"ERROR while applying rotation: {exc}")
        sys.exit(1)

    try:
        bounds = global_bounds(rotated_images, show_cell=args.show_cell)
    except Exception as exc:
        print(f"ERROR while computing global bounds: {exc}")
        sys.exit(1)

    frames = []
    for atoms, label in zip(rotated_images, labels):
        frame = render_frame(
            atoms=atoms,
            label=label,
            bounds=bounds,
            width=args.width,
            height=args.height,
            show_cell=args.show_cell,
            scale=args.scale,
            margin=args.margin,
            fontsize=args.fontsize,
            show_labels=not args.no_labels,
        )
        frames.append(frame)

    if args.pingpong and len(frames) > 2:
        frames = frames + frames[-2:0:-1]

    try:
        write_movie(frames, output, args.interval)
    except Exception as exc:
        print(f"ERROR while writing movie: {exc}")
        sys.exit(1)

    if args.write_extxyz:
        try:
            write(root / "neb_images.extxyz", images)
            print(root / "neb_images.extxyz")
        except Exception as exc:
            print(f"WARNING: failed to write neb_images.extxyz: {exc}")

    print(f"Loaded {len(images)} NEB images")
    print(f"Movie written to: {output.resolve()}")


if __name__ == "__main__":
    main()
