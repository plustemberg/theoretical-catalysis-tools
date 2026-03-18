# VASP on MN5: modules and job submission

Suggested filename: `mn5_vasp_modules_and_submission.md`

This note summarizes how to load the appropriate modules for different VASP builds on MareNostrum 5 (MN5) and how to submit a job with `sbatch`.

## 1. VASP 5.4.4 with Occupation Matrix control

For the Occupation Matrix build, load:

```bash
module purge
module load impi/2021.9.0 oneapi/2023.1 intel/2023.1 mkl/2022.1 ucx vasp/5.4.4-Occupation_matrix_v1.4
```

Run with:

```bash
srun /apps/GPP/VASP/5.4.4-Occupation_matrix_v1.4/INTEL/IMPI/bin/vasp_std
```

## 2. VASP 6.5.1 standard build

For the standard VASP 6.5.1 build, load:

```bash
module purge
module load mkl impi intel hdf5/1.10.11 ucx vasp/6.5.1
```

Run with:

```bash
srun /apps/GPP/VASP/6.5.1/INTEL/IMPI/bin/vasp_std
```

## 3. VASP 6.5.1 with VTST

If the VTST-enabled executable is available in your environment, first load:

```bash
module purge
module load mkl impi intel hdf5/1.10.11 ucx
module load oneapi vasp/6.5.1
```

Run with:

```bash
srun /apps/GPP/VASP/6.5.1/INTEL/IMPI/bin/vasp_std_vtst
```

## 4. Other variants seen in example scripts

In the example scripts, the following additional module/executable combinations also appear:

### VASP 5.4.4 VTST build

```bash
module purge
module load impi/2021.9.0 oneapi/2023.1 intel/2023.1 mkl/2022.1 ucx vasp/5.4.4_vtst
```

```bash
srun /apps/GPP/VASP/5.4.4_vtst/bin/vasp_std_vtst
```

### VASP 6.5.1 standard build from script

```bash
module purge
module load mkl impi intel hdf5/1.10.11 ucx vasp/6.5.1
```

```bash
srun /apps/GPP/VASP/6.5.1/INTEL/IMPI/bin/vasp_std
```

## 5. How to submit a VASP job on MN5

A typical workflow is:

1. Prepare a Slurm submission script, for example `job.sh`.
2. Set the resources with `#SBATCH` directives.
3. Load the modules corresponding to the VASP version you need.
4. Launch VASP with `srun`.
5. Submit the job with `sbatch job.sh`.

### Minimal example

```bash
#!/usr/bin/env bash
#SBATCH -J my_vasp_job
#SBATCH -D .
#SBATCH --nodes=2
#SBATCH --ntasks=224
#SBATCH --time=48:00:00
#SBATCH --output=job.%j.out
#SBATCH --error=job.%j.err
#SBATCH --qos=gp_resa

module purge
module load mkl impi intel hdf5/1.10.11 ucx vasp/6.5.1

srun /apps/GPP/VASP/6.5.1/INTEL/IMPI/bin/vasp_std
```

Submit with:

```bash
sbatch job.sh
```

## 6. Example Slurm directives used in MN5 scripts

Some directives used in the provided examples are:

```bash
#SBATCH -J job_name
#SBATCH -D .
#SBATCH --ntasks=224
#SBATCH --nodes=2
#SBATCH --time=72:00:00
#SBATCH --error=job.%j.err
#SBATCH --output=job.%j.out
#SBATCH --qos=gp_resa
```

Optional email notifications:

```bash
#SBATCH --mail-type=all
#SBATCH --mail-user=your_email@domain
```

## 7. Notes

- Use `module avail` to inspect available software modules on MN5.
- Keep the module stack consistent with the executable you call through `srun`.
- If you use a custom build such as VTST or Occupation Matrix control, make sure that both the loaded module and the executable path correspond to the same build.
- The exact number of nodes/tasks depends on the system size, functional, and parallelization strategy.

## 8. Source of the examples

The VTST 5.4.4 example is based on the uploaded MN5 script using `vasp/5.4.4_vtst` and `vasp_std_vtst`. The VASP 6.5.1 example is based on the uploaded MN5 script using `vasp/6.5.1` and `vasp_std`. The additional Occupation Matrix and VASP 6.5.1 VTST commands were taken from the command lines provided separately by the user.
