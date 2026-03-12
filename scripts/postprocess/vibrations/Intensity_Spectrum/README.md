# Spectrum from `legacy_z^2`

This directory contains a Python script to generate a broadened vibrational spectrum from the `legacy_z^2` column produced by:

- `dyndip_intensities_general_xyz_legacy.sh`

The script reads the mode frequencies and the corresponding `legacy_z^2` values from `dyndip_xyz_legacy.txt`, builds a broadened spectrum using **Gaussian functions**, and writes the result to a text file. Optionally, it can also generate a PNG figure.

## Purpose

This workflow is intended for users who want to:

- build a continuous spectrum from discrete mode intensities
- use specifically the `legacy_z^2` component
- compare broadened spectra obtained with different Gaussian widths
- visualize the resulting spectrum directly as a PNG file

## Main script

- `ir_spectrum_legacy_z2.py`

## Input

The script expects as input a file such as:

- `dyndip_xyz_legacy.txt`

This file must contain, for each mode:

- the vibrational frequency in `cm^-1`
- the corresponding `legacy_z^2` value

The script ignores comment lines starting with `#`.

## Output

By default, the script generates:

- `ir_spectrum_legacy_z2.dat`

This file contains two columns:

1. frequency in `cm^-1`
2. broadened intensity

If requested, it can also generate:

- a PNG file with the broadened spectrum

## Broadening model

The current implementation uses **Gaussian broadening**.

For each vibrational mode, a Gaussian centered at the corresponding frequency is added, weighted by the `legacy_z^2` intensity.

The total spectrum is the sum of all these Gaussian contributions.

## How to run

Basic example using `sigma`:

```bash
python3 ir_spectrum_legacy_z2.py --sigma 10
```
Basic example using `FWHM`:

```bash
python3 ir_spectrum_legacy_z2.py --fwhm 20
```
Generate both `.dat` and `.png`:

```bash
python3 ir_spectrum_legacy_z2.py --fwhm 20 --png ir_spectrum_legacy_z2.png
```

Use a custom frequency range::

```bash
python3 ir_spectrum_legacy_z2.py --sigma 12 --xmin 0 --xmax 4000
```
Increase the number of grid points:

```bash
python3 ir_spectrum_legacy_z2.py --sigma 12 --points 8000
```
Normalize the final spectrum so that the maximum intensity is 1:

```bash
python3 ir_spectrum_legacy_z2.py --fwhm 20 --normalize-max
```
Include vertical sticks in the PNG:

```bash
python3 ir_spectrum_legacy_z2.py --fwhm 20 --png ir_spectrum_legacy_z2.png --sticks
```
Include negative frequencies::

```bash
python3 ir_spectrum_legacy_z2.py --sigma 10 --include-negative
```
## Command-line options
*Input and output*

-i, --input
Input file.
Default: dyndip_xyz_legacy.txt

-o, --output
Output .dat file.
Default: ir_spectrum_legacy_z2.dat

