# MN5 VASP Relaxation Monitor

`mn5_vasp_relax_monitor.sh` is a lightweight Bash monitor for **VASP relaxation jobs running under Slurm on MareNostrum 5 (MN5)**.

It is intended to be launched **from within MN5**, and provides a compact live view of:

- Slurm job metadata
- the submission path in `HOME`
- the execution path in `SCRATCH`
- the requested computational resources
- the evolution of the relaxation by **ionic iteration**

In particular, it reports, for each ionic step:

- ionic iteration number
- number of electronic iterations actually used in that ionic step
- `E0`
- `dE`
- `mag`
- ionic step time (`t_ion`)
- force indicator from `OUTCAR` (`F_drift = ||total drift||`)

It also prints:

- Slurm job state
- elapsed runtime
- time limit
- number of nodes
- number of tasks and CPUs
- submission script path
- `SLURM WorkDir`
- `HOMEDIR`
- `WORKDIR`
- stdout/stderr paths

---

## 1. Why this script is useful

When a VASP relaxation is running on MN5, the standard queue commands (`squeue`, `scontrol`) tell you whether the job is active, but they do not directly summarize the **actual progress of the relaxation**.

This script fills that gap by combining information from:

- **Slurm**, through `scontrol show job`
- **OSZICAR**, to obtain ionic-step energies, electronic-iteration counts, and magnetization
- **OUTCAR**, to estimate the time spent in each ionic step and to extract the final `total drift` of that step

The result is a simple real-time monitor that is much more informative than checking `tail -f OUTCAR` manually.

---

## 2. Requirements

No Python installation is required.

The script only relies on standard Unix tools typically available on MN5:

- `bash`
- `awk`
- `sort`
- `tail`
- `mktemp`
- `date`
- `clear`
- `sleep`
- `scontrol`

### Important

This script is designed to run **inside MN5**, where Slurm commands are available.

If you try to launch it on your local laptop or outside the cluster, it will fail because `scontrol` will not be available.

---

## 3. Expected job layout

The monitor works best when your submission script defines explicit paths such as:

```bash
HOMEDIR="/gpfs/home/.../my_calculation"
WORKDIR="/gpfs/scratch/.../my_running_job"
```

A typical MN5 workflow is:

1. submit the job from a directory in `HOME`
2. define a scratch working directory in `WORKDIR`
3. copy or unpack the input files there
4. run VASP in `WORKDIR`
5. copy results back to `HOMEDIR`

The monitor reads:

- `HOMEDIR` and `WORKDIR` from the submission script, when possible
- the Slurm `WorkDir` as a fallback
- `OSZICAR` and `OUTCAR` from the resolved work directory

### Fallback behavior

If `WORKDIR` cannot be parsed from the submission script, the script falls back to:

- `WorkDir` returned by Slurm

If `WORKDIR` is defined in the submission script but does not exist, and Slurm `WorkDir` does exist, the script also falls back to the Slurm directory.

---

## 4. Installation

### Option A: use it from the current directory

```bash
chmod +x mn5_vasp_relax_monitor.sh
./mn5_vasp_relax_monitor.sh JOBID
```

### Option B: install it in `~/bin`

This is the most convenient option if you want to reuse it often.

```bash
mkdir -p ~/bin
cp mn5_vasp_relax_monitor.sh ~/bin/
chmod +x ~/bin/mn5_vasp_relax_monitor.sh
```

Then add `~/bin` to your `PATH` if it is not there already:

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

After that, you can call it from anywhere on MN5:

```bash
mn5_vasp_relax_monitor.sh JOBID
```

---

## 5. Basic usage

```bash
mn5_vasp_relax_monitor.sh JOBID
```

This launches the monitor in **continuous mode**, refreshing every 15 seconds by default.

### Syntax

```bash
mn5_vasp_relax_monitor.sh [-1] [-n LASTN] JOBID [REFRESH_SECONDS]
```

### Arguments and options

- `JOBID`  
  Numeric Slurm job ID.

- `REFRESH_SECONDS`  
  Optional refresh period in seconds. Default: `15`.

- `-1`  
  Run once and exit. Useful for a quick snapshot.

- `-n LASTN`  
  Show only the latest `LASTN` ionic steps. Default: `12`.

---

## 6. Usage examples

### Continuous monitoring with default refresh

```bash
mn5_vasp_relax_monitor.sh 19899205
```

### Continuous monitoring, refreshing every 30 seconds

```bash
mn5_vasp_relax_monitor.sh 19899205 30
```

### One-shot summary and exit

```bash
mn5_vasp_relax_monitor.sh -1 19899205
```

### Show the last 20 ionic steps, refresh every 10 seconds

```bash
mn5_vasp_relax_monitor.sh -n 20 19899205 10
```

### Show only the last 5 ionic steps in one-shot mode

```bash
mn5_vasp_relax_monitor.sh -1 -n 5 19899205
```

---

## 7. Example output

A typical output looks like this:

```text
Timestamp      : 2026-03-30 12:24:17
JobID          : 19899205
State          : RUNNING
RunTime        : 01:53:41
TimeLimit      : 3-00:00:00
Nodes          : 4
NTasks         : 448
NCPUs          : 448
Submit script  : /gpfs/home/.../mn5-script_vasp6.5.1.sh
SLURM WorkDir  : /gpfs/home/.../Ni6O9/1
HOMEDIR        : /gpfs/home/.../Ni6O9/1
WORKDIR        : /gpfs/scratch/.../R2.CH4ads.Ni6O9.1
StdOut         : /gpfs/home/.../job.19899205.out
StdErr         : /gpfs/home/.../job.19899205.err

Files present    : OSZICAR OUTCAR

Legend          : F_drift = ||total drift|| from OUTCAR ; t_ion = sum of OUTCAR LOOP real times per ionic step

  ion   NELM       F_drift          E0 (eV)        dE (eV)         mag    t_ion(s)
-----  -----   ------------   ----------------   --------------   ----------  ----------
   12     18      2.341e-03      -2404.721072    -5.657000e-04     6.0000      38.52
   13     15      1.908e-03      -2404.721125    -5.300000e-05     6.0000      31.14

Latest ionic step: ion=13  F_drift=1.908e-03  E0=-2404.721125  dE=-5.300000e-05  mag=6.0000  t_ion=31.14s
```

---

## 8. Meaning of each reported field

### Header section

- **Timestamp**  
  Current time when the monitor refreshed.

- **JobID**  
  Slurm job ID.

- **State**  
  Slurm state, for example `RUNNING`, `PENDING`, `COMPLETING`, `FAILED`, etc.

- **RunTime**  
  Elapsed wall time since the job started.

- **TimeLimit**  
  Maximum wall time requested in the Slurm script.

- **Nodes**  
  Number of nodes assigned to the job.

- **NTasks**  
  Number of MPI tasks requested by Slurm.

- **NCPUs**  
  Number of CPUs assigned by Slurm.

- **Submit script**  
  Path to the Slurm submission script detected by `scontrol`.

- **SLURM WorkDir**  
  The `WorkDir` stored by Slurm.

- **HOMEDIR**  
  Parsed from the submission script when available.

- **WORKDIR**  
  Parsed from the submission script when available, or replaced by Slurm `WorkDir` if needed.

- **StdOut / StdErr**  
  Paths to the Slurm output and error files.

### Ionic table

- **ion**  
  Ionic iteration index.

- **NELM**  
  Number of electronic SCF iterations actually used in that ionic step.

- **F_drift**  
  Euclidean norm of the `total drift` vector reported in `OUTCAR` for that ionic step.

  Mathematically:

  ```text
  F_drift = sqrt(dx^2 + dy^2 + dz^2)
  ```

  where `dx`, `dy`, and `dz` are the three components printed in the `total drift:` line.

  **Important:** this is **not** the maximum atomic force, nor the RMS force. It is specifically the norm of the `total drift` vector from `OUTCAR`.

- **E0 (eV)**  
  `E0` extracted from `OSZICAR` for that ionic step.

- **dE (eV)**  
  Energy change `dE` printed in `OSZICAR` for that ionic step.

- **mag**  
  Magnetization value printed in `OSZICAR`.

- **t_ion(s)**  
  Estimated total time spent in that ionic step, computed as the sum of `real time` values from the `LOOP:` or `LOOP+:` lines in `OUTCAR` corresponding to that ionic iteration.

### Latest ionic step

At the end of the table, the script prints a compact summary of the most recent ionic step.

This is useful when you want a quick answer to questions like:

- Is the energy still changing significantly?
- Is the magnetization stable?
- Is the ionic step taking longer than before?
- Is the drift decreasing?

---

## 9. How the script extracts the data

### 9.1 Slurm information

The script calls:

```bash
scontrol show job -o JOBID
```

From that one-line output it parses fields such as:

- `JobState`
- `RunTime`
- `TimeLimit`
- `NumNodes`
- `NumTasks`
- `NumCPUs`
- `Command`
- `StdOut`
- `StdErr`
- `WorkDir`

### 9.2 `HOMEDIR` and `WORKDIR`

If the submission script can be read, the script searches for lines of the form:

```bash
HOMEDIR="..."
WORKDIR="..."
```

and extracts their values.

### 9.3 Ionic-step data from `OSZICAR`

The script scans `OSZICAR` and:

- counts the number of electronic steps (`DAV:`, `RMM:`, `RMM-DIIS:`, etc.) before each ionic summary line
- detects ionic summary lines containing `F=` and `E0=`
- extracts:
  - ionic step index
  - SCF count used in that step
  - `E0`
  - `dE`
  - `mag`

### 9.4 Time and force indicator from `OUTCAR`

The script scans `OUTCAR` and:

- identifies the current ionic iteration from lines like `Iteration ...`
- sums the `real time` values from `LOOP:` / `LOOP+:` lines for that ionic step
- reads the last `total drift:` line for that ionic step and computes its norm

---

## 10. Interpretation tips

### `NELM`

- small `NELM` usually means the SCF is converging easily
- large `NELM` may indicate a difficult electronic structure or a problematic geometry
- if `NELM` frequently reaches the maximum allowed value, the relaxation may be poorly behaved

### `dE`

- values approaching zero indicate that the ionic relaxation is stabilizing
- large oscillations in `dE` may suggest geometry changes, spin changes, or unstable SCF behavior

### `mag`

- useful for magnetic systems such as transition-metal oxides, clusters, or reduced ceria systems
- sudden changes in `mag` can indicate electronic reorganization or spin-state changes

### `t_ion(s)`

- if it grows substantially with iteration number, the calculation may be getting harder to converge
- sudden jumps can also reflect I/O load, node performance variations, or difficult SCF cycles

### `F_drift`

- a decreasing trend is usually a good sign
- a persistently large drift can indicate that the calculation is still far from a well-relaxed state
- remember that this is **not** the standard convergence force criterion; it is only a convenient indicator taken from `OUTCAR`

---

## 11. Limitations

This script is intentionally simple and robust, but it has some important limitations.

### 11.1 It is designed for active jobs

It relies on:

```bash
scontrol show job -o JOBID
```

Therefore, it is mainly intended for **currently active jobs**.

If the job has already finished and Slurm no longer returns detailed information through `scontrol`, the script will not be able to build the header.

### 11.2 `F_drift` is not the maximum force

The force quantity shown is:

- the norm of `total drift` from `OUTCAR`

It is **not**:

- the maximum force on any atom
- the RMS force
- the convergence criterion directly used by VASP

If you want a version that reports **maximum atomic force per ionic step**, the script would need to be extended.

### 11.3 It assumes standard VASP output patterns

The parsing logic assumes common VASP formats for:

- `OSZICAR`
- `OUTCAR`
- Slurm job metadata

If your VASP version or workflow prints very different output, adaptation may be needed.

### 11.4 It assumes a standard scratch workflow

The script works best when:

- the job script defines `WORKDIR`
- `OSZICAR` and `OUTCAR` are produced in that directory

If your workflow writes files elsewhere, the monitor will need modification.

---

## 12. Troubleshooting

### Problem: `scontrol not found`

**Cause:** you are not running the script in an MN5 environment with Slurm available.

**Solution:** log into MN5 and run it there.

---

### Problem: `JOBID must be numeric`

**Cause:** the job ID argument contains non-numeric characters.

**Solution:** pass a valid Slurm numeric job ID, for example:

```bash
mn5_vasp_relax_monitor.sh 19899205
```

---

### Problem: `No pude obtener información con: scontrol show job -o JOBID`

**Cause:** the job may have already finished, been purged from live Slurm state, or the job ID is wrong.

**Solution:**

- verify the job ID with `squeue` or `sacct`
- use the script while the job is still active
- if needed, create a post-mortem version based on `sacct` and stored files

---

### Problem: `WORKDIR no existe todavía`

**Cause:** the scratch directory may not have been created yet, or the path was not resolved correctly.

**Solution:**

- wait until the job starts and creates the directory
- check whether your submission script defines `WORKDIR`
- verify the Slurm `WorkDir`

---

### Problem: `OSZICAR aún no existe o está vacío`

**Cause:** VASP has not started writing yet, or the job is still initializing.

**Solution:** wait a little longer and refresh.

---

### Problem: `No pude extraer iteraciones iónicas de OSZICAR todavía`

**Cause:** `OSZICAR` exists, but no ionic summary line has been written yet.

**Solution:** wait for the first ionic step to complete.

---

## 13. Recommended workflow on MN5

A practical workflow is:

1. submit your job with `sbatch`
2. get the job ID
3. once the job is running, launch the monitor in another terminal

Example:

```bash
sbatch mn5-script_vasp6.5.1.sh
squeue -u $USER
mn5_vasp_relax_monitor.sh 19899205
```

If you only want occasional checks:

```bash
mn5_vasp_relax_monitor.sh -1 -n 8 19899205
```

---

## 14. Suggested future improvements

Possible extensions include:

- reporting **maximum atomic force** instead of `total drift`
- estimating percentage of elapsed wall time with respect to `TimeLimit`
- warning if `OUTCAR` stops updating for too long
- auto-detecting the job ID from the current working directory
- supporting completed jobs through `sacct`
- colorized output for easier reading

---

## 15. File summary

### Script

- `mn5_vasp_relax_monitor.sh`  
  Main Bash monitor.

### Input sources read by the script

- Slurm job metadata through `scontrol`
- submission script referenced by Slurm
- `OSZICAR`
- `OUTCAR`

### No additional dependencies

- no Python
- no external packages
- no root installation needed

---

## 16. License and adaptation

You can adapt this script freely for your own MN5/VASP workflow.

If you modify your submission templates substantially, especially the way scratch paths are handled, it is a good idea to update the parsing rules accordingly.

---

## 17. Minimal quick reference

### Start continuous monitoring

```bash
mn5_vasp_relax_monitor.sh JOBID
```

### Single snapshot

```bash
mn5_vasp_relax_monitor.sh -1 JOBID
```

### Show more ionic steps

```bash
mn5_vasp_relax_monitor.sh -n 20 JOBID
```

### Change refresh period

```bash
mn5_vasp_relax_monitor.sh JOBID 30
```

---

## 18. Contact between script behavior and your MN5 template

This monitor is especially appropriate for MN5 job scripts that:

- define `HOMEDIR`
- define `WORKDIR` in scratch
- run VASP inside `WORKDIR`
- keep `OSZICAR` and `OUTCAR` there during execution
- optionally copy compressed results back to `HOMEDIR` at the end

That is exactly the kind of workflow commonly used to avoid heavy I/O in `HOME` while still preserving final outputs.

