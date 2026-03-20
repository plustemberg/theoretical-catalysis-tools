# Compare Structures

`compare_structures.py` compares two structures using ASE.

This script is useful for quickly checking structural differences between two files such as `POSCAR` and `CONTCAR`, or between two optimized geometries.

The script can compare:

- number of atoms
- chemical composition
- atom order
- cell parameters
- atom-by-atom displacement vectors
- RMSD
- maximum atomic displacement
- selected pair distances

It also supports:

- `--mic` for periodic systems
- `--align` for rigid alignment before computing displacements

## Recommended location in the repository

```text
scripts/postprocess/structure/
```

## Script name

```text
compare_structures.py
```

## Requirements

You need:

- Python 3
- ASE
- NumPy

## Installation

Install the required Python packages with:

```bash
python3 -m pip install --user ase numpy
```

## Basic usage

```bash
python3 compare_structures.py STRUCTURE1 STRUCTURE2
```

Example:

```bash
python3 compare_structures.py POSCAR CONTCAR
```

## Options

### Use minimum image convention

```bash
python3 compare_structures.py POSCAR CONTCAR --mic
```

Use this option for periodic systems when atoms may cross the cell boundary.

### Use rigid alignment

```bash
python3 compare_structures.py POSCAR CONTCAR --align
```

Use this option when both structures have the same atom order and you want to remove rigid translation and rotation before comparing displacements.

### Compare selected pair distances

```bash
python3 compare_structures.py POSCAR CONTCAR --pairs 1-2 1-5 7-9
```

Atom indices are **1-based**.

### Custom output file names

```bash
python3 compare_structures.py POSCAR CONTCAR --csv my_atoms.csv --summary my_summary.txt
```

## Output files

By default, the script writes:

```text
compare_structures_summary.txt
compare_structures_atoms.csv
```

## Output description

### `compare_structures_summary.txt`

Text summary including:

- file names
- number of atoms
- composition
- whether atom order is identical
- cell parameter comparison
- RMSD
- maximum displacement
- per-atom displacement table
- selected pair-distance comparison, if requested

### `compare_structures_atoms.csv`

CSV table with columns:

- atom index
- symbol in structure 1
- symbol in structure 2
- `dx`, `dy`, `dz` in Å
- displacement norm in Å

This file is useful for spreadsheet analysis or further processing.

## Meaning of `--mic`

`MIC` means **Minimum Image Convention**.

For periodic systems, two atoms or two atomic positions may look far apart in Cartesian coordinates even though they are actually close through the periodic boundary.

Using `--mic` makes the script compute the shortest displacement consistent with periodic boundary conditions.

This is usually useful for:

- bulk structures
- slab models
- periodic surfaces
- structures where atoms may cross the cell boundary

## Meaning of `--align`

`--align` applies a rigid Kabsch alignment before computing displacements.

This removes overall translation and rotation between the two structures.

This is usually useful for:

- molecules
- clusters
- non-periodic structures
- ordered structures where atom `i` in file 1 corresponds to atom `i` in file 2

In this version, `--align` and `--mic` should not be used together.

## Notes and limitations

- The script compares atom `i` in structure 1 with atom `i` in structure 2.
- It does not reorder atoms automatically.
- For meaningful comparisons, both structures should normally have the same atom ordering.
- `--mic` requires compatible cells.
- `--align` is intended for cases where the two structures differ mainly by rigid translation and rotation.

## Example

```bash
python3 compare_structures.py POSCAR CONTCAR --mic --pairs 1-2 1-5
```

This will:

- compare `POSCAR` and `CONTCAR`
- compute atom-by-atom displacements using periodic boundary conditions
- compare distances for pairs `1-2` and `1-5`
- write the default summary and CSV files
