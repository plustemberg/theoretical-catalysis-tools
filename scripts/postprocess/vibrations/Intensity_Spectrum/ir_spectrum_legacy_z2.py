#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import List, Tuple


def parse_file(filepath: Path, include_negative: bool = False) -> List[Tuple[float, float]]:
    """
    Reads dyndip_xyz_legacy.txt and extracts:
      frequency (cm^-1)  -> column 2
      legacy_z^2         -> last column
    """
    data: List[Tuple[float, float]] = []

    with filepath.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue

            fields = line.split()

            # Data lines should start with integer mode index
            try:
                int(fields[0])
            except (ValueError, IndexError):
                continue

            if len(fields) < 12:
                continue

            try:
                freq = float(fields[1])
                legacy_z2 = float(fields[-1])
            except ValueError:
                continue

            if not include_negative and freq < 0.0:
                continue

            data.append((freq, legacy_z2))

    if not data:
        raise ValueError("No valid (frequency, legacy_z^2) data found in input file.")

    return data


def gaussian(x: float, x0: float, sigma: float, area_normalized: bool = False) -> float:
    if sigma <= 0.0:
        raise ValueError("sigma must be > 0")
    arg = (x - x0) / sigma
    g = math.exp(-0.5 * arg * arg)
    if area_normalized:
        g /= (sigma * math.sqrt(2.0 * math.pi))
    return g


def build_spectrum(
    peaks: List[Tuple[float, float]],
    xmin: float,
    xmax: float,
    npoints: int,
    sigma: float,
    area_normalized: bool = False,
) -> List[Tuple[float, float]]:
    if xmax <= xmin:
        raise ValueError("xmax must be greater than xmin")
    if npoints < 2:
        raise ValueError("npoints must be at least 2")

    dx = (xmax - xmin) / (npoints - 1)
    spectrum: List[Tuple[float, float]] = []

    for i in range(npoints):
        x = xmin + i * dx
        y = 0.0
        for freq, intensity in peaks:
            y += intensity * gaussian(x, freq, sigma, area_normalized=area_normalized)
        spectrum.append((x, y))

    return spectrum


def save_dat(outfile: Path, spectrum: List[Tuple[float, float]]) -> None:
    with outfile.open("w", encoding="utf-8") as f:
        f.write("# frequency_cm-1 intensity\n")
        for x, y in spectrum:
            f.write(f"{x:12.6f} {y:18.12e}\n")


def maybe_plot(
    pngfile: Path,
    spectrum: List[Tuple[float, float]],
    sticks: List[Tuple[float, float]] | None = None,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not found: skipping PNG plot.")
        return

    xs = [p[0] for p in spectrum]
    ys = [p[1] for p in spectrum]

    plt.figure(figsize=(8, 5))
    plt.plot(xs, ys)

    if sticks:
        maxy = max(ys) if ys else 1.0
        for freq, inten in sticks:
            plt.vlines(freq, 0.0, inten, linewidth=1)

    plt.xlabel(r"Frequency / cm$^{-1}$")
    plt.ylabel("Intensity [Arb. Units]")
    plt.gca().invert_xaxis()
    plt.tight_layout()
    plt.savefig(pngfile, dpi=300)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Gaussian-broadened IR spectrum from legacy_z^2 in dyndip_xyz_legacy.txt"
    )

    parser.add_argument(
        "-i", "--input",
        default="dyndip_xyz_legacy.txt",
        help="Input file (default: dyndip_xyz_legacy.txt)",
    )
    parser.add_argument(
        "-o", "--output",
        default="ir_spectrum_legacy_z2.dat",
        help="Output .dat file (default: ir_spectrum_legacy_z2.dat)",
    )
    parser.add_argument(
        "--png",
        default=None,
        help="Optional output PNG file (requires matplotlib)",
    )

    width_group = parser.add_mutually_exclusive_group(required=True)
    width_group.add_argument(
        "--sigma",
        type=float,
        help="Gaussian sigma in cm^-1",
    )
    width_group.add_argument(
        "--fwhm",
        type=float,
        help="Gaussian FWHM in cm^-1",
    )

    parser.add_argument(
        "--xmin",
        type=float,
        default=None,
        help="Minimum frequency for the spectrum grid",
    )
    parser.add_argument(
        "--xmax",
        type=float,
        default=None,
        help="Maximum frequency for the spectrum grid",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=4000,
        help="Number of grid points (default: 4000)",
    )
    parser.add_argument(
        "--include-negative",
        action="store_true",
        help="Include negative frequencies",
    )
    parser.add_argument(
        "--area-normalized",
        action="store_true",
        help="Use area-normalized Gaussians instead of height-normalized ones",
    )
    parser.add_argument(
        "--normalize-max",
        action="store_true",
        help="Normalize the final spectrum so that its maximum is 1",
    )
    parser.add_argument(
        "--sticks",
        action="store_true",
        help="When saving PNG, also draw stick spectrum using legacy_z^2",
    )

    args = parser.parse_args()

    infile = Path(args.input)
    outfile = Path(args.output)

    peaks = parse_file(infile, include_negative=args.include_negative)

    if args.sigma is not None:
        sigma = args.sigma
    else:
        sigma = args.fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))

    freqs = [f for f, _ in peaks]

    xmin = args.xmin if args.xmin is not None else min(freqs) - 5.0 * sigma
    xmax = args.xmax if args.xmax is not None else max(freqs) + 5.0 * sigma

    spectrum = build_spectrum(
        peaks=peaks,
        xmin=xmin,
        xmax=xmax,
        npoints=args.points,
        sigma=sigma,
        area_normalized=args.area_normalized,
    )

    if args.normalize_max:
        ymax = max(y for _, y in spectrum)
        if ymax > 0.0:
            spectrum = [(x, y / ymax) for x, y in spectrum]

    save_dat(outfile, spectrum)

    if args.png:
        stick_data = None
        if args.sticks:
            if args.normalize_max:
                max_stick = max(i for _, i in peaks)
                stick_data = [(f, i / max_stick) for f, i in peaks] if max_stick > 0 else peaks
            else:
                stick_data = peaks
        maybe_plot(Path(args.png), spectrum, sticks=stick_data)

    print(f"Read {len(peaks)} peaks from {infile}")
    print(f"Sigma used: {sigma:.6f} cm^-1")
    print(f"Grid: xmin={xmin:.3f}, xmax={xmax:.3f}, points={args.points}")
    print(f"Wrote: {outfile}")
    if args.png:
        print(f"Wrote: {args.png}")


if __name__ == "__main__":
    main()