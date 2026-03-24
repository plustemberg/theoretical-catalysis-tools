# DOS tools for VASP

Small command-line toolkit to process `DOSCAR` files from VASP with an emphasis on surface-science and catalysis workflows.

## Files

- `vasp_dos_tools.py`  
  Core parser/helper module.
- `dos_info.py`  
  Prints a summary of the DOS format, species, orbitals, and basic metadata.
- `dos_split.py`  
  Exports total DOS and atom-resolved PDOS blocks to text files.
- `dos_sum.py`  
  Sums PDOS over arbitrary atom selections and orbital groups.
- `dos_metrics.py`  
  Computes orbital integrals and band centers in a chosen energy window.
- `dos_gap.py`  
  Estimates VBM/CBM/gap from the total DOS using a threshold.
- `dos_layers.py`  
  Groups slab atoms into layers according to the z coordinate from `CONTCAR`.
- `dos_plot.py`  
  Quick PNG plotter for total DOS or selected PDOS.
- `compare_dos.py`
  Automatic comparison of DOS/PDOS from two calculations.

## Requirements

python3

For plotting:

- `matplotlib`

No external VASP-specific python3 package is required.

## General philosophy

- energies are written as `E - E_F`
- `E_F` is taken from the DOSCAR header
- `OUTCAR` is used mainly to detect `ISPIN` and `LORBIT`
- `CONTCAR` is used to map atom indices to species and slab layers

## Usage examples

### 1. Inspect the DOS format

```bash
python3 dos_info.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR
```

### 2. Export the full total DOS and selected atomic PDOS blocks

```bash
python3 dos_split.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --outdir dos_export --atoms "1-4,O"
```

This writes:

- `dos_export/DOS_total.dat`
- `dos_export/atom_1.dat`, `atom_2.dat`, ...

### 3. Sum PDOS over all atoms of one element

```bash
python3 dos_sum.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --atoms Mg --orbitals s,p,d --output Mg_spd.dat
```

```bash
python3 dos_sum.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --atoms O --orbitals p --output O_p.dat
```

### 4. Sum only selected m-components

```bash
python3 dos_sum.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --atoms "1-8" --orbitals dz2,dxz,dx2-y2 --output top_Mg_d_components.dat
```

### 5. Compute a band center in an energy window

```bash
python3 dos_metrics.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --atoms O --orbitals p --emin -8 --emax 2
```

Typical use cases:

- O `p`-band center
- metal `d`-band center
- selected `d` components such as `dz2`

### 6. Estimate a gap from the total DOS

```bash
python3 dos_gap.py --doscar DOSCAR --threshold 0.05
```

The threshold should be chosen carefully. For broadened DOS, the gap estimate depends strongly on the threshold.

### 7. Group slab atoms into layers

```bash
python3 dos_layers.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --tol 0.20
```

This is useful before summing PDOS for top-layer vs subsurface atoms.

### 8. Plot total DOS

```bash
python3 dos_plot.py --doscar DOSCAR --output total_dos.png --emin -8 --emax 6
```

### 9. Plot selected PDOS

```bash
python3 dos_plot.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --atoms O --orbitals p --emin -8 --emax 4 --output O_p.png
```

```bash
python3 dos_plot.py --doscar DOSCAR --outcar OUTCAR --contcar CONTCAR --atoms "1-8" --orbitals dz2,dxz,dx2-y2 --emin -6 --emax 4 --output selected_d_components.png
```

## Atom selection syntax

The `--atoms` flag accepts:

- single indices: `5`
- ranges: `1-8`
- comma-separated lists: `1,3,5-8`
- element names from `CONTCAR`: `Mg`, `O`
- mixed selections: `1-4,O`

## Orbital selection syntax

Accepted examples depend on the detected projected DOS columns.

Typical examples for `LORBIT = 11` and `spd`-resolved PDOS:

- grouped channels: `s`, `p`, `d`
- specific components: `py`, `pz`, `px`, `dxy`, `dyz`, `dz2`, `dxz`, `dx2-y2`
- multiple requests: `dz2,dxz,dx2-y2`

For spin-polarized DOS, the tools are written to handle channels such as:

- `s_up`, `s_down`
- `p_up`, `p_down`
- `d_up`, `d_down`

and also the individual m-resolved channels with `_up` / `_down` suffixes when present.

## compare_dos.py

Automatic comparison of DOS/PDOS from two calculations.

Useful cases:
- clean surface vs adsorbate-covered surface
- stoichiometric vs reduced model
- PBE vs r2SCAN
- ferromagnetic vs non-magnetic solution
- two different local environments for the same atom set

Examples:

```bash
python3 compare_dos.py \
  --doscar-a DOSCAR.clean --outcar-a OUTCAR.clean --contcar-a CONTCAR.clean \
  --doscar-b DOSCAR.ads   --outcar-b OUTCAR.ads   --contcar-b CONTCAR.ads \
  --emin -8 --emax 3 --output-prefix clean_vs_ads
```

```bash
python3 compare_dos.py \
  --doscar-a DOSCAR.A --outcar-a OUTCAR.A --contcar-a CONTCAR.A \
  --doscar-b DOSCAR.B --outcar-b OUTCAR.B --contcar-b CONTCAR.B \
  --atoms Ni --orbitals d --emin -8 --emax 2 --normalize max \
  --output-prefix Ni_d_compare
```

Outputs:
- `PREFIX.png`: overlay plot of A and B
- `PREFIX_metrics.txt`: integrated weights, band centers, band-center shift, and shape-difference metrics
- `PREFIX_LABEL.dat`: common-grid data file for each compared label


