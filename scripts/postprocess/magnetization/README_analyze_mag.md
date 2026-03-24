# analyze_magnetization.py

General-purpose post-processing tool to analyze local magnetic moments from the `OUTCAR` file of a VASP calculation.

This script was originally motivated by the need to identify `Ce3+` centers from the projected `f` magnetization, but it has been generalized so it can also be used for other magnetic systems such as transition metals (`d`) or lanthanides/actinides (`f`).

The script can:

- detect the chemical species present in the `OUTCAR`
- summarize the final magnetic moment by species
- analyze one selected element using a chosen component (`s`, `p`, `d`, `f`, or `tot`)
- compare the local moment against a target value with a user-defined tolerance
- identify atoms within the same species that behave differently from the others
- track the evolution of the local moment of selected atoms along the ionic relaxation

## Requirements

- Python 3.x
- No external Python packages are required

## Input

The script reads a standard VASP `OUTCAR` containing the projected magnetic moments block:

```text
magnetization (x)
```

It extracts:

- species from `VRHFIN`
- number of ions per species from `ions per type`
- total number of atoms from `NIONS`
- all `magnetization (x)` blocks along the run

## Usage

```bash
python3 analyze_magnetization.py -o OUTCAR [options]
```

## Main options

```text
-o, --outcar     Path to OUTCAR (default: OUTCAR)
-e, --element    Element to analyze, e.g. Ce, Ni, Fe
--orbital        Component to analyze: s, p, d, f, tot (default: tot)
--target         Expected local magnetic moment in absolute value
--tol            Tolerance for target matching and outlier detection (default: 0.2)
--track          Track the evolution of the selected atoms along ionic steps
--atoms          Comma-separated list of atom indices to track
--top            Number of atoms to show in the printed ranking (default: 10)
```

## Basic examples

### 1. General summary of the calculation

```bash
python3 analyze_magnetization.py -o OUTCAR
```

This prints:

- detected species and their atom ranges
- a final summary by species using the `tot` contribution

### 2. Analyze Ce using the `f` component

```bash
python3 analyze_magnetization.py -o OUTCAR -e Ce --orbital f
```

Useful for systems where the relevant local moment is mainly associated with the `f` channel.

### 3. Look for atoms close to a target magnetic moment

```bash
python3 analyze_magnetization.py -o OUTCAR -e Ce --orbital f --target 1.0 --tol 0.2
```

This is useful, for example, when searching for atoms whose projected moment is compatible with a reduced state.

### 4. Analyze a transition metal through its `d` contribution

```bash
python3 analyze_magnetization.py -o OUTCAR -e Ni --orbital d --target 1.0 --tol 0.2
```

This is often more informative than using `tot` for 3d systems.

### 5. Detect heterogeneity within the same species

```bash
python3 analyze_magnetization.py -o OUTCAR -e Ni --orbital d --tol 0.15
```

The script computes the median value for that species and reports atoms that differ from the median by more than the chosen tolerance.

This is especially useful when:

- not all atoms of the same element are equivalent
- only part of a cluster is more oxidized/reduced
- interfacial atoms behave differently from terrace or bulk-like atoms

### 6. Track the evolution during relaxation

```bash
python3 analyze_magnetization.py -o OUTCAR -e Ni --orbital d --track
```

If `--track` is used with `--element`, the script follows all atoms of that species along the ionic steps.

### 7. Track only selected atoms

```bash
python3 analyze_magnetization.py -o OUTCAR --orbital d --track --atoms 97,98,99,100
```

This is useful when you already know which atoms you want to monitor.

## Interpretation notes

The local magnetic moments printed in the VASP `OUTCAR` are projected quantities inside the PAW spheres. Therefore:

- they should not be interpreted as exact oxidation states
- they are best used as diagnostic indicators
- trends, relative differences, and changes along the run are often more meaningful than a strict absolute threshold

For this reason, this script includes two complementary approaches:

1. **comparison against a target value**
2. **detection of atoms that differ from the rest of the same species**

In many practical cases, the second criterion is the most robust one.

## Recommended workflows

### For lanthanides or actinides

Use the `f` component:

```bash
python3 analyze_magnetization.py -o OUTCAR -e Ce --orbital f
```

### For transition metals

Use the `d` component:

```bash
python3 analyze_magnetization.py -o OUTCAR -e Fe --orbital d
python3 analyze_magnetization.py -o OUTCAR -e Ni --orbital d
python3 analyze_magnetization.py -o OUTCAR -e Co --orbital d
```

### For a broad first inspection

Use the total projected moment:

```bash
python3 analyze_magnetization.py -o OUTCAR -e Ce --orbital tot
```

## Typical output

The script reports, depending on the selected options:

- species and atom ranges
- final magnetic summary by species
- ranked list of atoms of the selected element
- median value for the chosen component
- atoms classified as outliers within the species
- atoms close to or far from a target moment
- evolution by ionic step for tracked atoms
- initial/final/min/max values during the run

## Limitations

- The script reads `magnetization (x)` blocks from `OUTCAR`; non-standard or incomplete files may fail.
- The analysis is based on projected local moments and depends on the PAW partitioning.
- A target value must be chosen by the user according to the chemical system and the type of orbital of interest.


## Author note

This script is intended as a practical post-processing utility for magnetic VASP calculations, where the goal is not only to identify atoms close to an expected magnetic moment, but also to detect chemically meaningful differences within the same atomic species and to monitor how local moments evolve during structural relaxation.
