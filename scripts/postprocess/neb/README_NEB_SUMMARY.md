# NEB Summary

`neb_summary.py` summarizes the energies of VASP NEB images stored in numbered folders such as `00`, `01`, `02`, etc.

The script:

- reads the final energy of each NEB image
- uses `OSZICAR` by default
- falls back to `OUTCAR` if needed
- writes summary tables in `.dat` and `.csv` format
- optionally generates a PNG plot of the NEB energy profile

This is useful for quickly checking the energetic profile of a NEB calculation without manually opening each image.

## Recommended location in the repository

```text
scripts/postprocess/neb/
```

## Script name

```text
neb_summary.py
```

## Requirements

Minimum requirement:

- Python 3

Optional requirement for plotting:

- matplotlib

## Installation

### Python 3

Check that Python is available:

```bash
python3 --version
```

### matplotlib

Install matplotlib if you want to generate `neb_profile.png`:

```bash
python3 -m pip install --user matplotlib
```

## Expected directory structure

Run the script from a NEB directory containing numbered image folders:

```text
neb_calculation/
├── 00/
│   ├── OUTCAR
│   └── OSZICAR
├── 01/
│   ├── OUTCAR
│   └── OSZICAR
├── 02/
│   ├── OUTCAR
│   └── OSZICAR
...
└── 07/
    ├── OUTCAR
    └── OSZICAR
```

## How the script reads energies

The script supports three modes:

- `--source auto`  
  Try `OSZICAR` first, then `OUTCAR`
- `--source oszicar`  
  Read only from `OSZICAR`
- `--source outcar`  
  Read only from `OUTCAR`

In `OUTCAR`, the script gives preference to:

1. `energy  without entropy=`
2. `free  energy   TOTEN  =`

## Relative energy reference

Relative energies can be referenced to:

- `first` → first valid image
- `min` → minimum energy image
- `last` → last valid image

Default:

```bash
--ref first
```

## How to run

### Basic usage

From inside the NEB calculation directory:

```bash
python3 neb_summary.py
```

### Generate a plot

```bash
python3 neb_summary.py --plot
```

### Force reading from OUTCAR

```bash
python3 neb_summary.py --source outcar
```

### Use the minimum-energy image as reference

```bash
python3 neb_summary.py --ref min
```

### Use a different root directory

```bash
python3 neb_summary.py --root /path/to/neb
```

### Example with plot and minimum reference

```bash
python3 neb_summary.py --ref min --plot
```

## Output files

The script writes:

```text
neb_summary.dat
neb_summary.csv
```

If `--plot` is used, it also writes:

```text
neb_profile.png
```

## Output description

### `neb_summary.dat`

Plain text summary with columns:

- image
- absolute energy in eV
- relative energy in eV
- source used (`OSZICAR` or `OUTCAR`)

### `neb_summary.csv`

CSV version of the same information, useful for spreadsheets or further processing.

### `neb_profile.png`

Line plot of relative energy vs NEB image.

## Printed summary

The script also prints a summary in the terminal, including:

- image-by-image energies
- relative energies
- forward barrier
- reverse barrier
- maximum relative energy
- names of generated output files

## Barrier definition

In this version, the barriers are computed from the discrete NEB image energies:

- forward barrier = highest relative energy - first valid image relative energy
- reverse barrier = highest relative energy - last valid image relative energy

This means the script does **not** perform interpolation or spline fitting. It only uses the available image energies.

## Example

```bash
python3 neb_summary.py --plot
```

Possible terminal output:

```text
NEB summary
-----------
  00   E =   -1234.56789012 eV   dE =   0.00000000 eV   [OSZICAR]
  01   E =   -1234.42100000 eV   dE =   0.14689012 eV   [OSZICAR]
  02   E =   -1234.31000000 eV   dE =   0.25789012 eV   [OUTCAR]
  03   E =   -1234.25000000 eV   dE =   0.31789012 eV   [OSZICAR]
  04   E =   -1234.29000000 eV   dE =   0.27789012 eV   [OSZICAR]
  05   E =   -1234.38000000 eV   dE =   0.18789012 eV   [OSZICAR]
  06   E =   -1234.50000000 eV   dE =   0.06789012 eV   [OSZICAR]
  07   E =   -1234.60000000 eV   dE =  -0.03210988 eV   [OSZICAR]

Barriers
--------
Forward barrier: 0.31789012 eV
Reverse barrier: 0.35000000 eV
Maximum relative energy: 0.31789012 eV
```

## Notes

- The script expects numbered folders for the images.
- If an image is missing a readable energy, it is reported as `nan`.
- `OSZICAR` is usually enough for a quick summary.
- `OUTCAR` can be useful as a fallback when `OSZICAR` is missing or incomplete.
