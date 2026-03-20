# Bader Summary

`bader_summary.py` summarizes Bader charges from `ACF.dat` and a structure file such as `POSCAR` or `CONTCAR`.

The script:

- reads atomic symbols and positions from the structure file using ASE
- reads Bader electrons from `ACF.dat`
- reports atom-by-atom Bader values
- optionally computes approximate net charges if reference valence electrons are supplied
- optionally sums charges over user-defined groups of atoms
- writes `.txt` and `.csv` output files


## Script name

```text
bader_summary.py
```

## Requirements

You need:

- Python 3
- ASE

## Installation

Install ASE with:

```bash
python3 -m pip install --user ase
```

## Required input files

At minimum you need:

- `ACF.dat`
- a structure file readable by ASE, for example `POSCAR` or `CONTCAR`

## Basic usage

```bash
python3 bader_summary.py --acf ACF.dat --structure CONTCAR
```

## Reference valence electrons

If you want approximate net charges, provide reference valence electrons by element:

```bash
python3 bader_summary.py --acf ACF.dat --structure CONTCAR --ref Ce=12 O=6 Ni=10 C=4 H=1
```

The script uses:

```text
net_charge = reference_valence - bader_electrons
```

If no reference values are given, `net_charge` is reported as `n/a`.

## Groups of atoms

You can define groups using 1-based atom indices:

```bash
python3 bader_summary.py --acf ACF.dat --structure CONTCAR \
  --groups cluster:1-8 support:9-120 adsorbate:121-126
```

You can also combine ranges and explicit indices:

```bash
python3 bader_summary.py --acf ACF.dat --structure CONTCAR \
  --groups cluster:1-6,9 support:7-120 ads:121-123,126
```

## Output files

By default, the script writes:

```text
bader_summary.txt
bader_atoms.csv
```

If groups are supplied, it also writes:

```text
bader_groups.csv
```

## Output description

### `bader_summary.txt`

Text summary including:

- basic system information
- composition
- reference valence values used
- atom-by-atom Bader electrons
- approximate net charges
- element-wise averages
- group charge sums, if requested

### `bader_atoms.csv`

CSV table with columns:

- atom index
- element
- atomic coordinates from the structure file
- coordinates reported in `ACF.dat`
- Bader electrons
- reference valence
- net charge

### `bader_groups.csv`

CSV table with columns:

- group name
- number of atoms
- group formula
- atom indices
- total Bader electrons
- total reference valence
- total net charge

## Example

### Basic summary

```bash
python3 bader_summary.py --acf ACF.dat --structure CONTCAR
```

### With reference valence electrons

```bash
python3 bader_summary.py --acf ACF.dat --structure CONTCAR --ref Ce=12 O=6 Ni=10 C=4 H=1
```

### With groups

```bash
python3 bader_summary.py --acf ACF.dat --structure CONTCAR \
  --ref Ce=12 O=6 Ni=10 C=4 H=1 \
  --groups Ni_cluster:1-6 O_cluster:7-8 support:9-120 ads:121-126
```

## Notes

- The script assumes the atom order in `ACF.dat` matches the atom order in the structure file.
- The reported net charge is an approximate quantity that depends on the chosen reference valence electrons.
- Group totals are only fully meaningful when reference values are supplied for all elements present in the group.
