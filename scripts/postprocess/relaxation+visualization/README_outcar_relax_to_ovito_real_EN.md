# `outcar_relax_to_ovito_real.py`

Script to extract an ionic relaxation from a VASP `OUTCAR` and generate, in a single run:

- a multiframe `extxyz` trajectory that can be opened in **OVITO**
- a summary `.csv` file with energies, forces, and magnetization
- a **relative energy** vs ionic iteration plot
- a **maximum atomic force** vs ionic iteration plot
- a **total magnetization** vs ionic iteration plot, if the `OUTCAR` contains that information
- four PNG views of the final structure rendered with **real OVITO**:
  - `xy` (top)
  - `xz` (front)
  - `yz` (right)
  - `iso` (oblique)

The script works with:

- an `OUTCAR` file
- a calculation directory containing `OUTCAR`
- a root directory, using recursive mode to process all subdirectories containing `OUTCAR`

---

## 1. What the script does

### From the `OUTCAR`

The script searches for all ionic `POSITION ... TOTAL-FORCE` blocks and, for each ionic step, extracts:

- atomic positions
- Cartesian forces
- total energy (`TOTEN`)
- total magnetization, when present in the `OUTCAR`
- periodic cell, if available in the `OUTCAR`

### Generated files

By default, the output prefix is:

```text
relax
```

Therefore, in a calculation directory it usually generates:

```text
relax.extxyz
relax_summary.csv
relax_energy.png
relax_forces.png
relax_magnetization.png   # only if magnetization is present
relax_view_xy.png
relax_view_xz.png
relax_view_yz.png
relax_view_iso.png
```

### Energy reference

The energy plot and the CSV use:

```text
ΔE = E(i) - E(1)
```

That is:

- the first step is set to `0`
- in a normal relaxation, the last steps are typically negative relative to the first one

### Structure used for the PNG views

For the OVITO-rendered views, the script tries to use, in this order:

1. `CONTCAR`
2. `POSCAR`
3. the last frame extracted from the `OUTCAR`

This allows the PNG views to be generated even if no `CONTCAR` is available.

---

## 2. Requirements

### Python

The script is intended for Python 3 on Linux/WSL.

### Required Python packages

- `numpy`
- `matplotlib`
- `ovito`

Typical installation inside your virtual environment:

```bash
source ~/venvs/ase-env/bin/activate
python -m pip install -U pip
pip install -U numpy matplotlib ovito
```

### System libraries on Ubuntu / WSL

For `import ovito` to work in WSL/Ubuntu, in addition to the Python package, OpenGL/EGL system libraries are usually required.

On recent Ubuntu versions, install:

```bash
sudo apt update
sudo apt install -y libopengl0 libegl1 libgl1 libglx-mesa0
```

Then verify:

```bash
source ~/venvs/ase-env/bin/activate
python -c "import ovito; print('OVITO OK')"
```

If you see `OVITO OK`, the environment is ready.

---

## 3. Basic usage

### Case 1: pass an `OUTCAR` directly

```bash
python outcar_relax_to_ovito_real.py OUTCAR
```

### Case 2: pass a calculation directory

```bash
python outcar_relax_to_ovito_real.py .
```

The script will look for:

```text
./OUTCAR
```

### Case 3: use a custom prefix

```bash
python outcar_relax_to_ovito_real.py OUTCAR -o ni607_relax
```

This will generate:

```text
ni607_relax.extxyz
ni607_relax_summary.csv
ni607_relax_energy.png
...
```

---

## 4. Recursive usage

To process all subdirectories under a root folder that contain an `OUTCAR`:

```bash
python outcar_relax_to_ovito_real.py /path/to/root --recursive
```

Or from the current directory:

```bash
python outcar_relax_to_ovito_real.py . --recursive
```

In recursive mode:

- the script searches for all `OUTCAR` files
- each calculation is processed in its own directory
- the prefix used is `relax`
- one line per calculation is printed on screen, for example:

```text
[OK] /path/to/OUTCAR -> /path/to/relax
```

---

## 5. Available options

### `-o`, `--output-prefix`

Allows you to change the output prefix in non-recursive mode.

Example:

```bash
python outcar_relax_to_ovito_real.py OUTCAR -o my_relaxation
```

### `--recursive`

Processes all subdirectories containing `OUTCAR` recursively.

Example:

```bash
python outcar_relax_to_ovito_real.py . --recursive
```

### `--atom-scale`

Global scale factor for sphere size in the PNG images generated with OVITO.

Default value:

```text
1.20
```

Example:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --atom-scale 1.35
```

If you want the spheres to fill the gaps more, increase this value.

### `--renderer`

OVITO rendering engine.

Available options:

- `opengl`
- `tachyon`

Default:

```text
opengl
```

Examples:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --renderer opengl
python outcar_relax_to_ovito_real.py OUTCAR --renderer tachyon
```

### `--use-custom-colors`

Uses the `CUSTOM_ELEMENT_COLORS` dictionary defined in the script instead of OVITO's default colors.

Example:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --use-custom-colors
```

---

## 6. Custom colors

At the top of the script there is a dictionary like this:

```python
CUSTOM_ELEMENT_COLORS = {
    # 'Ce': (0.94, 0.91, 0.69),
    # 'O':  (1.00, 0.00, 0.00),
    # 'Ni': (0.00, 0.28, 1.00),
    # 'C':  (0.75, 0.75, 0.75),
    # 'H':  (1.00, 1.00, 1.00),
}
```

### How to use it

1. Edit the script and uncomment or add the elements you want.
2. Run the script with:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --use-custom-colors
```

### Example

```python
CUSTOM_ELEMENT_COLORS = {
    'Ce': (1.00, 1.00, 1.00),
    'O':  (1.00, 0.00, 0.00),
    'Ni': (0.00, 0.00, 1.00),
    'C':  (0.70, 0.70, 0.70),
    'H':  (0.95, 0.95, 0.95),
}
```

If you do **not** use `--use-custom-colors`, OVITO will use its default element colors based on the chemical names.

---

## 7. Terminal output

In non-recursive mode, at the end of the run the script prints a summary like:

```text
Directory               : /path/to/calculation
OUTCAR                  : /path/to/calculation/OUTCAR
Frames extracted        : 173
Atoms per frame         : 114
Output prefix           : /path/to/calculation/relax
Views generated from    : CONTCAR
Wrote                   : /path/to/calculation/relax.extxyz
Wrote                   : /path/to/calculation/relax_summary.csv
Wrote                   : /path/to/calculation/relax_energy.png
Wrote                   : /path/to/calculation/relax_forces.png
Wrote                   : /path/to/calculation/relax_magnetization.png
Wrote                   : /path/to/calculation/relax_view_xy.png
Wrote                   : /path/to/calculation/relax_view_xz.png
Wrote                   : /path/to/calculation/relax_view_yz.png
Wrote                   : /path/to/calculation/relax_view_iso.png
```

---

## 8. CSV format

The `*_summary.csv` file contains the columns:

```text
step
energy_eV
deltaE_vs_first_eV
max_force_eVA
rms_force_eVA
total_magnetization
```

### Meaning

- `step`: ionic iteration number
- `energy_eV`: total energy of that step
- `deltaE_vs_first_eV`: relative energy with respect to the first step
- `max_force_eVA`: maximum atomic force at that step
- `rms_force_eVA`: RMS force at that step
- `total_magnetization`: total magnetization, if present in the `OUTCAR`

---

## 9. `extxyz` trajectory

The `relax.extxyz` file contains all ionic steps and can be opened directly in OVITO.

Each frame includes:

- chemical species
- Cartesian positions
- forces
- global metadata such as:
  - `step`
  - `energy`
  - `delta_e`
  - `max_force`
  - `magnetization` when available

### Open in OVITO

From the OVITO GUI:

- `File -> Load File`
- select `relax.extxyz`

You will then be able to browse the entire relaxation frame by frame.

---

## 10. Interpretation of the PNG views

The files:

```text
relax_view_xy.png
relax_view_xz.png
relax_view_yz.png
relax_view_iso.png
```

correspond to:

- `xy`: top view
- `xz`: front view
- `yz`: side view
- `iso`: oblique orthographic view

### Visual style

- real OVITO rendering
- white background
- no bonds added by the script
- visible simulation cell in gray
- sphere size controlled by `--atom-scale`

---

## 11. Complete examples

### Example 1: run inside the calculation folder

```bash
cd /mnt/c/Trabajo/00_DATOS/GOFEE/NiOx/R2SCAN/CH4ads/Ni607/3/res1
source ~/venvs/ase-env/bin/activate
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR
```

### Example 2: use a custom prefix

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR -o ni607_ch4_relax
```

### Example 3: larger spheres

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR --atom-scale 1.35
```

### Example 4: use custom colors

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR --use-custom-colors
```

### Example 5: recursive mode

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py /mnt/c/Trabajo/00_DATOS/GOFEE/NiOx --recursive
```

---

## 12. Warnings and expected behavior in WSL

During OVITO rendering in WSL, you may see messages like:

```text
libEGL warning: ...
MESA: error: ZINK: failed to choose pdev
```

If the script still prints `Wrote : ...png` lines and the PNG files are generated correctly, these messages are only warnings from the WSL/MESA graphics backend and do not prevent the script from working.

You should only worry if:

- the PNG files are blank
- the script stops before writing the files
- OVITO raises a fatal error and terminates execution

---

## 13. Current limitations

- In file mode, the file must be named exactly `OUTCAR`.
- The script expects standard `POSITION ... TOTAL-FORCE` blocks in the `OUTCAR`.
- If the `OUTCAR` does not contain enough species metadata, the script may assign generic names such as `X` in the trajectory.
- Magnetization is only plotted if the `OUTCAR` contains the corresponding information.
- The final PNG appearance depends on the OVITO rendering engine and on your WSL graphics environment.

---

## 14. Troubleshooting

### Problem: `ImportError: libOpenGL.so.0`

Install the required system libraries:

```bash
sudo apt update
sudo apt install -y libopengl0 libegl1 libgl1 libglx-mesa0
```

### Problem: `python ... does nothing`

Check that:

- you are running the correct version of the script
- you are in the correct virtual environment
- a real `OUTCAR` exists in that directory

Correct example:

```bash
source ~/venvs/ase-env/bin/activate
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR
```

### Problem: `relax_magnetization.png` is not generated

This usually means that the `OUTCAR` does not contain total magnetization information that the script can parse.

### Problem: the spheres look too small

Increase the parameter:

```bash
--atom-scale
```

For example:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --atom-scale 1.35
```

### Problem: I want different colors

Edit `CUSTOM_ELEMENT_COLORS` and use:

```bash
--use-custom-colors
```
