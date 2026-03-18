# MN5 multi-job submission helper (`submit_all_mn5_vg.sh`)

This script is intended to **submit several jobs in parallel/batch on MareNostrum 5 (MN5)** by walking through a root directory, finding matching submission scripts inside subfolders, and launching them with `sbatch`.

It is useful when you have many calculation folders prepared already and want to submit them in a single command instead of entering each directory manually.

In addition to submitting jobs, the script can also:

- skip folders that were already submitted;
- force resubmission;
- limit how many jobs are submitted;
- do a dry run;
- save a small `sacct` summary;
- write metadata for each submitted job into `slurm_jobid.txt`.

The script content below is the one provided by the user in `submit_all_mn5_vg.sh` fileciteturn3file0.

---

## What this script does

The script scans a root directory recursively and searches for a submission script matching a given file name or glob pattern.

For each matching script, it:

1. enters the corresponding folder;
2. checks whether the job was already submitted (`.submitted` marker);
3. determines which Slurm account to use;
4. submits the job with `sbatch`;
5. stores submission metadata in `slurm_jobid.txt`;
6. optionally saves a one-line `sacct` report.

---

## Typical use case

Suppose you have a directory tree like this:

```text
project/
├── calc_01/
│   └── mn5-script_vasp6.5.1.sh
├── calc_02/
│   └── mn5-script_vasp6.5.1.sh
├── calc_03/
│   └── mn5-script_vasp6.5.1.sh
```

Instead of going folder by folder and running `sbatch`, you can execute this script once from `project/` and submit all jobs at once.

---

## How to use it

### Basic syntax

```bash
bash submit_all_mn5_vg.sh [options] [ROOT_DIR]
```

If `ROOT_DIR` is omitted, the script uses the current directory (`.`).

### Basic example

```bash
bash submit_all_mn5_vg.sh .
```

This will recursively search from the current directory for the default script name:

```bash
mn5-script_vasp6.5.1.sh
```

and submit every matching job.

### Submit using a specific Slurm account

```bash
bash submit_all_mn5_vg.sh --account icp22 .
```

### Use a different script name or pattern

```bash
bash submit_all_mn5_vg.sh --script "mn5-script_v544*.sh" .
```

### Dry run

```bash
bash submit_all_mn5_vg.sh --dry-run .
```

This only prints what would be submitted, without actually launching jobs.

### Limit the number of submitted jobs

```bash
bash submit_all_mn5_vg.sh --limit 10 .
```

### Force resubmission

```bash
bash submit_all_mn5_vg.sh --force .
```

This ignores existing `.submitted` markers.

### Remove `.submitted` markers before scanning

```bash
bash submit_all_mn5_vg.sh --reset .
```

### Save a minimal `sacct` report after submission

```bash
bash submit_all_mn5_vg.sh --sacct .
```

---

## Command-line options

The script supports the following options:

```text
-a, --account ACCOUNT   Use this Slurm account.
-S, --script GLOB       Script name or glob to search.
-n, --dry-run           Show what would be submitted.
-l, --limit N           Submit at most N jobs.
-f, --force             Re-submit even if .submitted exists.
-s, --sacct             Save a one-line sacct TSV after submission.
-r, --reset             Remove .submitted markers before scanning.
-h, --help              Print help.
```

---

## Variables used by the script

### User-configurable variables

These are the main variables that control behavior:

- `ACCOUNT`  
  Slurm account to use. It is initialized from the environment variable `MN5_ACCOUNT` if present.

- `SCRIPT_GLOB`  
  File name or pattern used to search submission scripts. Default:
  ```bash
  mn5-script_vasp6.5.1.sh
  ```
  It is initialized from the environment variable `MN5_SCRIPT` if present.

- `ROOT_DIR`  
  Root directory from which recursive scanning starts. Default:
  ```bash
  .
  ```

### Internal control flags

- `DRY_RUN=0`  
  If set to `1`, the script does not submit jobs and only reports what it would do.

- `LIMIT=0`  
  Maximum number of jobs to submit. `0` means no limit.

- `FORCE=0`  
  If set to `1`, submission is performed even when `.submitted` exists.

- `DO_SACCT=0`  
  If set to `1`, the script stores a simple `sacct_<jobid>.tsv` file.

- `DO_RESET=0`  
  If set to `1`, all `.submitted` markers under `ROOT_DIR` are deleted before scanning.

### Environment variables

The script allows two environment overrides:

```bash
export MN5_ACCOUNT=icp22
export MN5_SCRIPT=mn5-script_vasp6.5.1.sh
```

Then you can run:

```bash
bash submit_all_mn5_vg.sh .
```

---

## Files created by the script

For each submitted job, the script may generate:

- `.submitted`  
  marker file indicating that the directory was already submitted;

- `slurm_jobid.txt`  
  YAML-like snapshot with job ID, submission time, directory, selected `#SBATCH` parameters, hashes of input files, and VASP version;

- `sacct_<jobid>.tsv`  
  optional Slurm accounting summary if `--sacct` is used.

---

## Account selection logic

The effective Slurm account is chosen in this order:

1. command-line option `--account`;
2. `#SBATCH --account=...` inside the job script;
3. no account specified.

So the command-line value overrides the one written inside each submission script.

---

## Notes

- The script looks for a file matching `SCRIPT_GLOB` using `find`.
- A folder is skipped if `.submitted` exists, unless `--force` is used.
- Metadata are saved in `slurm_jobid.txt`, even when the submission script already contains the relevant `#SBATCH` directives.
- The variable
  ```bash
  vasp_ver="6.5.1"
  ```
  is hardcoded in the current version of the script, so if you use it for another VASP version, this should be updated or auto-detected.

---

## Recommended examples on MN5

### Submit all folders using the default script name

```bash
bash submit_all_mn5_vg.sh /path/to/calculations
```

### Submit all folders using another script pattern

```bash
bash submit_all_mn5_vg.sh --script "mn5-script_v544*.sh" /path/to/calculations
```

### Check first without submitting

```bash
bash submit_all_mn5_vg.sh --dry-run --script "mn5-script_vasp6.5.1.sh" /path/to/calculations
```

### Submit only the first 5 jobs

```bash
bash submit_all_mn5_vg.sh --limit 5 /path/to/calculations
```

### Re-submit everything after removing markers

```bash
bash submit_all_mn5_vg.sh --reset --force /path/to/calculations
```

---

## Full script

```bash
#!/usr/bin/env bash
# submit_all_mn5.sh — Walk subfolders, submit sbatch, and log metadata (YAML).
# Now supports:
#   -a, --account ACCOUNT   Override account (else auto-detect from #SBATCH; else omit)
#   -S, --script GLOB       Script name/pattern to find (default: mn5-script_vasp6.5.1.sh)
# Other options kept:
#   -n, --dry-run | -l, --limit N | -f, --force | -s, --sacct | -r, --reset | -h, --help

set -euo pipefail

ACCOUNT="${MN5_ACCOUNT:-}"                     # optional; can be set via env
SCRIPT_GLOB="${MN5_SCRIPT:-mn5-script_vasp6.5.1.sh}"

DRY_RUN=0; LIMIT=0; FORCE=0; DO_SACCT=0; DO_RESET=0
ROOT_DIR="."

usage() {
  cat <<EOF2
Usage: $0 [options] [ROOT_DIR]
  -a, --account ACCOUNT   Use this Slurm account (overrides script). If omitted, try to auto-detect from #SBATCH; if none, submit without --account.
  -S, --script GLOB       File name or glob to search (default: ${SCRIPT_GLOB})
  -n, --dry-run           Show what would be submitted
  -l, --limit N           Submit at most N jobs
  -f, --force             Re-submit even if .submitted exists
  -s, --sacct             After submission, save a one-line sacct TSV
  -r, --reset             Remove .submitted markers under ROOT_DIR before scanning
  -h, --help              This help
Environment overrides: MN5_ACCOUNT, MN5_SCRIPT
EOF2
  exit 0
}

# Parse CLI
while [[ $# -gt 0 ]]; do
  case "$1" in
    -a|--account) ACCOUNT="$2"; shift 2 ;;
    -S|--script)  SCRIPT_GLOB="$2"; shift 2 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -l|--limit)   LIMIT="${2:-0}"; shift 2 ;;
    -f|--force)   FORCE=1; shift ;;
    -s|--sacct)   DO_SACCT=1; shift ;;
    -r|--reset)   DO_RESET=1; shift ;;
    -h|--help)    usage ;;
    *) ROOT_DIR="$1"; shift ;;
  esac
done

[[ -d "$ROOT_DIR" ]] || { echo "ERROR: Root directory not found: $ROOT_DIR" >&2; exit 1; }

echo "Root: $ROOT_DIR"
echo "Script pattern: $SCRIPT_GLOB"
echo "Account: ${ACCOUNT:-<auto/none>}"
[[ $DRY_RUN -eq 1 ]] && echo "[DRY-RUN] No jobs will be submitted."
[[ $FORCE -eq 1 ]] && echo "[FORCE] Ignoring .submitted markers."
[[ $LIMIT -gt 0 ]] && echo "Submission limit: $LIMIT"
if [[ $DO_RESET -eq 1 ]]; then
  echo "[RESET] Removing .submitted under $ROOT_DIR"
  find "$ROOT_DIR" -type f -name .submitted -print -delete
fi

found_count=0; submitted=0; skipped=0

# Helper: extract value from #SBATCH lines
get_val_from_sbatch_lines() {
  local key="$1"; shift
  local lines="$*"
  echo "$lines" | sed -n "s/.*--$(printf '%s' "$key")\([= ]\)\([^[:space:]]\+\).*/\2/p" | tail -n1
}

# Main loop
while IFS= read -r -d '' script_path; do
  ((found_count++)) || true
  job_dir="$(dirname "$script_path")"
  script_file="$(basename "$script_path")"

  if [[ $FORCE -eq 0 && -e "$job_dir/.submitted" ]]; then
    echo "Skipping (already submitted): $job_dir"
    ((skipped++)) || true
    continue
  fi

  # Decide account: CLI > #SBATCH > none
  sb_lines="$(grep -E '^[[:space:]]*#SBATCH' "$script_path" || true)"
  account_eff="$ACCOUNT"
  if [[ -z "${account_eff}" ]]; then
    account_eff="$(get_val_from_sbatch_lines account "$sb_lines" || true)"
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    if [[ -n "$account_eff" ]]; then
      echo "[DRY-RUN] Would submit in: $job_dir -> sbatch --account=\"$account_eff\" $script_file"
    else
      echo "[DRY-RUN] Would submit in: $job_dir -> sbatch $script_file"
    fi
    continue
  fi

  echo "Submitting in: $job_dir (script: $script_file; account: ${account_eff:-none})"
  pushd "$job_dir" >/dev/null

  # Build sbatch command; use --parsable for clean JobID
  if [[ -n "$account_eff" ]]; then
    cmd=(sbatch --parsable --account="$account_eff" "$script_file")
  else
    cmd=(sbatch --parsable "$script_file")
  fi

  if ! output="$("${cmd[@]}")"; then
    echo "ERROR: sbatch failed in $job_dir"
    popd >/dev/null
    continue
  fi

  jobid_raw="$output"; jobid="${jobid_raw%%_*}"; array_id=""
  [[ "$jobid_raw" == *_* ]] && array_id="${jobid_raw#*_}"

  # Parse useful #SBATCH fields for the YAML
  sb_partition="$(get_val_from_sbatch_lines partition "$sb_lines")"
  sb_qos="$(get_val_from_sbatch_lines qos "$sb_lines")"
  sb_name="$(get_val_from_sbatch_lines job-name "$sb_lines")"
  sb_nodes="$(get_val_from_sbatch_lines nodes "$sb_lines")"
  sb_ntasks="$(get_val_from_sbatch_lines ntasks "$sb_lines")"
  sb_ntpn="$(get_val_from_sbatch_lines ntasks-per-node "$sb_lines")"
  sb_cpt="$(get_val_from_sbatch_lines cpus-per-task "$sb_lines")"
  sb_gpus="$(get_val_from_sbatch_lines gpus "$sb_lines")"
  sb_mem="$(get_val_from_sbatch_lines mem "$sb_lines")"
  sb_time="$(get_val_from_sbatch_lines time "$sb_lines")"
  sb_dep="$(get_val_from_sbatch_lines dependency "$sb_lines")"
  sb_out="$(get_val_from_sbatch_lines output "$sb_lines")"
  sb_err="$(get_val_from_sbatch_lines error "$sb_lines")"

  # Hashes (ignore if files don’t exist)
  incar_sha1="$(sha1sum INCAR 2>/dev/null | awk '{print $1}')"     || true
  kpoints_sha1="$(sha1sum KPOINTS 2>/dev/null | awk '{print $1}')" || true
  poscar_sha1="$(sha1sum POSCAR 2>/dev/null | awk '{print $1}')"   || true
  potcar_md5="$(md5sum POTCAR 2>/dev/null | awk '{print $1}')"     || true
  script_sha256="$(sha256sum "$script_file" | awk '{print $1}')"   || true

  now="$(date -Iseconds)"; wd="$(pwd)"; usr="$(whoami)"; hst="$(hostname)"
  sbatch_cmd="sbatch"
  [[ -n "$account_eff" ]] && sbatch_cmd+=" --account=$account_eff"
  sbatch_cmd+=" $script_file"

  vasp_ver="6.5.1"  # adjust if you want to auto-detect

  # Write YAML snapshot
  {
    echo "job_id: ${jobid}"
    [[ -n "$array_id" ]] && echo "array_task_id: ${array_id}" || echo "array_task_id: null"
    echo "submitted_at: $now"
    echo "workdir: $wd"
    echo "user: $usr"
    echo "host: $hst"
    echo "sbatch_cmd: \"$sbatch_cmd\""
    echo "script:"
    echo "  path: $script_file"
    echo "  sha256: ${script_sha256:-null}"
    echo "sbatch_directives:"
    echo "  account: ${account_eff:-null}"
    echo "  partition: ${sb_partition:-null}"
    echo "  qos: ${sb_qos:-null}"
    echo "  job_name: ${sb_name:-null}"
    echo "  nodes: ${sb_nodes:-null}"
    echo "  ntasks: ${sb_ntasks:-null}"
    echo "  ntasks_per_node: ${sb_ntpn:-null}"
    echo "  cpus_per_task: ${sb_cpt:-null}"
    echo "  gpus: ${sb_gpus:-null}"
    echo "  mem: ${sb_mem:-null}"
    echo "  time: \"${sb_time:-null}\""
    echo "  dependency: ${sb_dep:-null}"
    echo "  output: ${sb_out:-null}"
    echo "  error: ${sb_err:-null}"
    echo "inputs:"
    echo "  INCAR_sha1: ${incar_sha1:-null}"
    echo "  KPOINTS_sha1: ${kpoints_sha1:-null}"
    echo "  POSCAR_sha1: ${poscar_sha1:-null}"
    echo "  POTCAR_md5: ${potcar_md5:-null}"
    echo "vasp:"
    echo "  version: \"${vasp_ver}\""
  } > slurm_jobid.txt

  date -Iseconds > .submitted
  echo "OK: Submitted job $jobid (details in slurm_jobid.txt)"

  if [[ $DO_SACCT -eq 1 ]]; then
    for attempt in 1 2 3; do
      if sacct -j "$jobid" -n -P --format=JobID,State,ExitCode,Elapsed,TotalCPU,AllocTRES%50 > "sacct_${jobid}.tsv" 2>/dev/null; then
        echo "sacct saved to sacct_${jobid}.tsv"
        break
      fi
      sleep 1
    done
  fi

  popd >/dev/null
  ((submitted++)) || true
  if [[ $LIMIT -gt 0 && $submitted -ge $LIMIT ]]; then
    echo "Submission limit reached ($LIMIT)."; break; fi
done < <(find "$ROOT_DIR" -type f -name "$SCRIPT_GLOB" -print0)

echo "----------------------------------------"
echo "Scripts found:   $found_count"
echo "Submitted:       $submitted"
echo "Skipped:         $skipped"
[[ $DRY_RUN -eq 1 ]] && echo "(dry-run: 0 submissions executed)"
echo "Done."
```
