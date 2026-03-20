# Bader Compare

`bader_compare.py` compares Bader charges between two calculations.

This script is useful for analyzing charge redistribution between:

- clean and adsorbate-covered surfaces
- initial and final states
- reduced and oxidized systems
- defective and non-defective models
- different adsorption geometries

## Recommended location in the repository

```text
scripts/postprocess/charges/
```

## Script name

```text
bader_compare.py
```

## Requirements

You need:

- Python 3
- ASE
- NumPy
- `ACF.dat` from both calculations
- a structure file for each calculation, such as `POSCAR` or `CONTCAR`

## Installation

Install the required Python packages with:

```bash
python3 -m pip install --user ase numpy
```

## Input files

The script requires:

- `ACF.dat` for calculation 1
- `POSCAR` or `CONTCAR` for calculation 1
- `ACF.dat` for calculation 2
- `POSCAR` or `CONTCAR` for calculation 2

## Important assumption

This version assumes **atom-by-atom correspondence** between both calculations.

That means:

- both structures must contain the same number of atoms
- atom order should be the same
- atom `i` in calculation 1 is compared with atom `i` in calculation 2

If atom order changes, the comparison is not meaningful unless atoms are remapped first.

## Definitions

The script uses:

```text
delta_bader_e = Bader(calc2) - Bader(calc1)
```

If reference valence electrons are provided:

```text
net_charge = reference_valence - bader_electrons
delta_net_e = net_charge(calc2) - net_charge(calc1)
```

Because of these definitions:

```text
delta_net_e = - delta_bader_e
```

when the reference is the same for a given element.

## Basic usage

```bash
python3 bader_compare.py --acf1 ACF_1.dat --structure1 CONTCAR_1 \
                         --acf2 ACF_2.dat --structure2 CONTCAR_2
```

Example:

```bash
python3 bader_compare.py --acf1 calc1/ACF.dat --structure1 calc1/CONTCAR \
                         --acf2 calc2/ACF.dat --structure2 calc2/CONTCAR
```

## Provide reference valence electrons

```bash
python3 bader_compare.py --acf1 calc1/ACF.dat --structure1 calc1/CONTCAR \
                         --acf2 calc2/ACF.dat --structure2 calc2/CONTCAR \
                         --ref Ce=12 O=6 Ni=10 C=4 H=1
```

## Compare charge by groups

Groups are defined with **1-based indices**.

Example:

```bash
python3 bader_compare.py --acf1 calc1/ACF.dat --structure1 calc1/CONTCAR \
                         --acf2 calc2/ACF.dat --structure2 calc2/CONTCAR \
                         --ref Ce=12 O=6 Ni=10 C=4 H=1 \
                         --groups cluster:1-6 support:7-120 ads:121-126
```

You can also mix individual atoms and ranges:

```bash
--groups active_site:1-3,8,10-12
```

## Output files

By default, the script writes:

```text
bader_compare_atoms.csv
bader_compare_summary.txt
```

If groups are provided, it also writes:

```text
bader_compare_groups.csv
```

## Output description

### `bader_compare_atoms.csv`

Atom-by-atom comparison with columns:

- atom index
- symbol in calculation 1
- symbol in calculation 2
- Bader electrons in calculation 1
- Bader electrons in calculation 2
- delta Bader electrons
- reference valence electrons
- net charge in calculation 1
- net charge in calculation 2
- delta net charge

### `bader_compare_groups.csv`

Group-wise charge comparison with:

- group name
- number of atoms
- total Bader electrons in calculation 1
- total Bader electrons in calculation 2
- delta Bader electrons
- total net charge in calculation 1
- total net charge in calculation 2
- delta net charge
- atom indices used in the group

### `bader_compare_summary.txt`

Text summary including:

- file names
- atom-count and composition checks
- whether atom order is identical
- atom-by-atom charge comparison
- total charge differences
- optional group comparison
- definitions used by the script

## Example

```bash
python3 bader_compare.py --acf1 IS/ACF.dat --structure1 IS/CONTCAR \
                         --acf2 FS/ACF.dat --structure2 FS/CONTCAR \
                         --ref Ce=12 O=6 Ni=10 C=4 H=1 \
                         --groups cluster:1-6 support:7-120 ads:121-126
```

## Notes

- The script reads atomic Bader values from the standard `ACF.dat` format.
- It does not run the Bader code itself.
- It compares existing Bader results only.
- If no reference dictionary is provided, the script still compares Bader electrons, but it does not compute net charges.
- For chemically meaningful comparisons, make sure both calculations use compatible structures and the same atom ordering.
