#!/usr/bin/env bash
# Monitor a VASP relaxation running under SLURM on MareNostrum 5 (MN5).
#
# Shows:
#   - job metadata from SLURM (state, runtime, timelimit, ntasks, nodes, submit script)
#   - HOMEDIR and WORKDIR parsed from the submission script when available
#   - per ionic iteration: NELM-used, force norm from OUTCAR total drift, E0, dE, mag, ionic time
#
# Usage:
#   mn5_vasp_relax_monitor.sh JOBID
#   mn5_vasp_relax_monitor.sh JOBID 20
#   mn5_vasp_relax_monitor.sh -1 JOBID         # one-shot summary
#   mn5_vasp_relax_monitor.sh -n 15 JOBID 10   # show last 15 ionic steps, refresh every 10 s

set -u

REFRESH=15
LASTN=12
ONESHOT=0

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") [-1] [-n LASTN] JOBID [REFRESH_SECONDS]

Options:
  -1          Print once and exit
  -n LASTN    Number of latest ionic iterations to show (default: ${LASTN})

Examples:
  $(basename "$0") 19899205
  $(basename "$0") -1 19899205
  $(basename "$0") -n 20 19899205 30
USAGE
}

while getopts ":1n:h" opt; do
  case "$opt" in
    1) ONESHOT=1 ;;
    n) LASTN="$OPTARG" ;;
    h) usage; exit 0 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 1 ;;
    :) echo "Option -$OPTARG requires an argument." >&2; usage; exit 1 ;;
  esac
done
shift $((OPTIND-1))

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

JOBID="$1"
if [[ $# -eq 2 ]]; then
  REFRESH="$2"
fi

if ! [[ "$JOBID" =~ ^[0-9]+$ ]]; then
  echo "ERROR: JOBID must be numeric." >&2
  exit 1
fi
if ! [[ "$REFRESH" =~ ^[0-9]+$ ]] || [[ "$REFRESH" -lt 1 ]]; then
  echo "ERROR: REFRESH_SECONDS must be a positive integer." >&2
  exit 1
fi
if ! [[ "$LASTN" =~ ^[0-9]+$ ]] || [[ "$LASTN" -lt 1 ]]; then
  echo "ERROR: LASTN must be a positive integer." >&2
  exit 1
fi

have_cmd() { command -v "$1" >/dev/null 2>&1; }

if ! have_cmd scontrol; then
  echo "ERROR: scontrol not found. Run this script inside MN5 with Slurm available." >&2
  exit 1
fi

get_field() {
  local line="$1" key="$2"
  awk -v key="$key" '
    {
      for (i = 1; i <= NF; i++) {
        if ($i ~ ("^" key "=")) {
          sub("^" key "=", "", $i)
          print $i
          exit
        }
      }
    }
  ' <<< "$line"
}

parse_var_from_script() {
  local var="$1" script="$2"
  [[ -r "$script" ]] || return 1
  awk -F= -v var="$var" '
    $0 ~ "^[[:space:]]*" var "=" {
      val = substr($0, index($0, "=") + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
      gsub(/^"|"$/, "", val)
      gsub(/^\047|\047$/, "", val)
      print val
      exit
    }
  ' "$script"
}

parse_oszicar() {
  local file="$1"
  [[ -s "$file" ]] || return 0
  awk '
    BEGIN { scf = 0 }
    /^[[:space:]]*(DAV:|RMM:|RMM-DIIS:|CGA:|SDA:|EDIAG:)/ { scf++; next }
    /F=/ && /E0=/ {
      ionic = $1
      Fv = E0 = dE = mag = "NA"
      for (i = 1; i <= NF; i++) {
        if ($i == "F=") Fv = $(i+1)
        if ($i == "E0=") E0 = $(i+1)
        if ($i == "mag=") mag = $(i+1)
        if ($i == "d" && $(i+1) == "E") {
          dE = $(i+2)
          sub(/^=/, "", dE)
        }
      }
      printf "%d %d %s %s %s %s\n", ionic, scf, Fv, E0, dE, mag
      scf = 0
    }
  ' "$file"
}

parse_outcar() {
  local file="$1"
  [[ -s "$file" ]] || return 0
  awk '
    {
      line = $0
      if (line ~ /Iteration[[:space:]]+[0-9]+\(/) {
        tmp = line
        sub(/^.*Iteration[[:space:]]+/, "", tmp)
        sub(/\(.*/, "", tmp)
        ion = tmp + 0
      }
      if (ion > 0 && (index(line, "LOOP+:") || index(line, "LOOP:")) && index(line, "real time")) {
        tmp = line
        sub(/^.*real time[[:space:]]+/, "", tmp)
        sub(/[[:space:]].*$/, "", tmp)
        t[ion] += tmp + 0.0
      }
      if (line ~ /total drift:/ && ion > 0) {
        x = $(NF-2) + 0.0
        y = $(NF-1) + 0.0
        z = $NF + 0.0
        f[ion] = sqrt(x*x + y*y + z*z)
      }
    }
    END {
      for (i in t) seen[i] = 1
      for (i in f) seen[i] = 1
      for (i in seen) {
        tt = (i in t ? t[i] : -1)
        ff = (i in f ? f[i] : -1)
        printf "%d %.6f %.10e\n", i, tt, ff
      }
    }
  ' "$file" | sort -n -k1,1
}

render_table() {
  local osz="$1" out="$2"
  awk '
    NR==FNR {
      time[$1] = $2
      force[$1] = $3
      next
    }
    {
      ion = $1
      nel = $2
      e0 = $4
      de = $5
      mag = $6
      t = (ion in time && time[ion] >= 0 ? sprintf("%.2f", time[ion]) : "NA")
      f = (ion in force && force[ion] >= 0 ? sprintf("%.3e", force[ion]) : "NA")
      printf "%5d  %5d  %12s  %16.6f  %14.6e  %10s  %10s\n", ion, nel, f, e0 + 0.0, de + 0.0, mag, t
    }
  ' "$out" "$osz" | tail -n "$LASTN"
}

print_header() {
  local now="$1" state="$2" runtime="$3" timelimit="$4" nodes="$5" ntasks="$6" ncpus="$7" script="$8" homedir="$9" workdir="${10}" stdout_path="${11}" stderr_path="${12}" workdir_slurm="${13}"
  echo "Timestamp      : $now"
  echo "JobID          : $JOBID"
  echo "State          : ${state:-UNKNOWN}"
  echo "RunTime        : ${runtime:-NA}"
  echo "TimeLimit      : ${timelimit:-NA}"
  echo "Nodes          : ${nodes:-NA}"
  echo "NTasks         : ${ntasks:-NA}"
  echo "NCPUs          : ${ncpus:-NA}"
  echo "Submit script  : ${script:-NA}"
  echo "SLURM WorkDir  : ${workdir_slurm:-NA}"
  echo "HOMEDIR        : ${homedir:-NA}"
  echo "WORKDIR        : ${workdir:-NA}"
  echo "StdOut         : ${stdout_path:-NA}"
  echo "StdErr         : ${stderr_path:-NA}"
}

render_once() {
  local jobline state runtime timelimit nodes ntasks ncpus command stdout_path stderr_path workdir_slurm
  local script_path homedir workdir oszicar outcar tmp_osz tmp_out

  jobline=$(scontrol show job -o "$JOBID" 2>/dev/null || true)
  if [[ -z "$jobline" ]]; then
    echo "No pude obtener información con: scontrol show job -o $JOBID"
    echo "Puede que el job ya no esté activo o que el JOBID no exista en este momento."
    return 1
  fi

  state=$(get_field "$jobline" "JobState")
  runtime=$(get_field "$jobline" "RunTime")
  timelimit=$(get_field "$jobline" "TimeLimit")
  nodes=$(get_field "$jobline" "NumNodes")
  ntasks=$(get_field "$jobline" "NumTasks")
  ncpus=$(get_field "$jobline" "NumCPUs")
  command=$(get_field "$jobline" "Command")
  stdout_path=$(get_field "$jobline" "StdOut")
  stderr_path=$(get_field "$jobline" "StdErr")
  workdir_slurm=$(get_field "$jobline" "WorkDir")

  script_path="$command"
  homedir=""
  workdir=""
  if [[ -n "$script_path" && -r "$script_path" ]]; then
    homedir=$(parse_var_from_script HOMEDIR "$script_path" || true)
    workdir=$(parse_var_from_script WORKDIR "$script_path" || true)
  fi

  if [[ -z "$workdir" ]]; then
    workdir="$workdir_slurm"
  elif [[ ! -d "$workdir" && -n "$workdir_slurm" && -d "$workdir_slurm" ]]; then
    workdir="$workdir_slurm"
  fi

  oszicar="${workdir%/}/OSZICAR"
  outcar="${workdir%/}/OUTCAR"

  print_header "$(date '+%F %T')" "$state" "$runtime" "$timelimit" "$nodes" "$ntasks" "$ncpus" "$script_path" "$homedir" "$workdir" "$stdout_path" "$stderr_path" "$workdir_slurm"
  echo

  if [[ ! -d "$workdir" ]]; then
    echo "WORKDIR no existe todavía o no se pudo resolver: $workdir"
    return 0
  fi

  echo "Files present    : $( [[ -s "$oszicar" ]] && echo -n 'OSZICAR ' )$( [[ -s "$outcar" ]] && echo -n 'OUTCAR' )"
  echo

  if [[ ! -s "$oszicar" ]]; then
    echo "OSZICAR aún no existe o está vacío en: $oszicar"
    return 0
  fi

  tmp_osz=$(mktemp)
  tmp_out=$(mktemp)
  parse_oszicar "$oszicar" > "$tmp_osz"
  if [[ -s "$outcar" ]]; then
    parse_outcar "$outcar" > "$tmp_out"
  else
    : > "$tmp_out"
  fi

  if [[ ! -s "$tmp_osz" ]]; then
    echo "No pude extraer iteraciones iónicas de OSZICAR todavía."
    rm -f "$tmp_osz" "$tmp_out"
    return 0
  fi

  echo "Legend          : F_drift = ||total drift|| from OUTCAR ; t_ion = sum of OUTCAR LOOP real times per ionic step"
  echo
  printf "%5s  %5s  %12s  %16s  %14s  %10s  %10s\n" "ion" "NELM" "F_drift" "E0 (eV)" "dE (eV)" "mag" "t_ion(s)"
  printf "%5s  %5s  %12s  %16s  %14s  %10s  %10s\n" "-----" "-----" "------------" "----------------" "--------------" "----------" "----------"
  render_table "$tmp_osz" "$tmp_out"
  echo

  last_ion=$(tail -n 1 "$tmp_osz" | awk '{print $1}')
  last_e0=$(tail -n 1 "$tmp_osz" | awk '{printf "%.6f", $4 + 0.0}')
  last_de=$(tail -n 1 "$tmp_osz" | awk '{printf "%.6e", $5 + 0.0}')
  last_mag=$(tail -n 1 "$tmp_osz" | awk '{print $6}')
  last_force=$(awk -v ion="$last_ion" '$1==ion{printf "%.3e", $3; found=1} END{if(!found) print "NA"}' "$tmp_out")
  last_time=$(awk -v ion="$last_ion" '$1==ion{printf "%.2f", $2; found=1} END{if(!found) print "NA"}' "$tmp_out")
  echo "Latest ionic step: ion=${last_ion}  F_drift=${last_force}  E0=${last_e0}  dE=${last_de}  mag=${last_mag}  t_ion=${last_time}s"

  rm -f "$tmp_osz" "$tmp_out"
  return 0
}

is_terminal_state() {
  local state="$1"
  [[ "$state" =~ ^(COMPLETED|FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE)$ ]]
}

if [[ "$ONESHOT" -eq 1 ]]; then
  render_once
  exit $?
fi

while true; do
  clear
  render_once || exit $?
  current_state=$(scontrol show job -o "$JOBID" 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i ~ /^JobState=/) {sub(/^JobState=/, "", $i); print $i; exit}}')
  if is_terminal_state "$current_state"; then
    echo
    echo "El job está en estado terminal: $current_state"
    exit 0
  fi
  sleep "$REFRESH"
done
