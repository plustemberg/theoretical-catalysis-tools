#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Dynamic dipole intensities from VASP finite differences
#
# Full vector version + legacy x/y/z projections
#
# Usage:
#   ./dyndip_intensities_general_xyz_legacy.sh [OUTCAR] [POSCAR_or_CONTCAR]
#
# Default:
#   OUTCAR
#   CONTCAR if present, otherwise POSCAR
# ------------------------------------------------------------

OUTCAR_FILE="${1:-OUTCAR}"

if [[ $# -ge 2 ]]; then
    POS_FILE="$2"
else
    if [[ -f CONTCAR ]]; then
        POS_FILE="CONTCAR"
    else
        POS_FILE="POSCAR"
    fi
fi

if [[ ! -f "$OUTCAR_FILE" ]]; then
    echo "ERROR: OUTCAR file not found: $OUTCAR_FILE" >&2
    exit 1
fi

if [[ ! -f "$POS_FILE" ]]; then
    echo "ERROR: POSCAR/CONTCAR file not found: $POS_FILE" >&2
    exit 1
fi

tmpdir=$(mktemp -d dyndip_general_xyz.XXXXXX)
trap 'rm -rf "$tmpdir"' EXIT

datafile="$tmpdir/dyndip.data"
dipfile="$tmpdir/dipoles.dat"
freqfile="$tmpdir/freqs.dat"
selfile="$tmpdir/select.dat"
evfile="$tmpdir/evect.dat"
modes0="$tmpdir/modes_0"
modes1="$tmpdir/modes_1"

# ------------------------------------------------------------
# Basic quantities from OUTCAR
# ------------------------------------------------------------
nfree=$(awk '/NFREE[[:space:]]*=/{for(i=1;i<=NF;i++) if($i=="="){print $(i+1); exit}}' "$OUTCAR_FILE")
potim=$(awk '/POTIM[[:space:]]*=/{for(i=1;i<=NF;i++) if($i=="="){print $(i+1); exit}}' "$OUTCAR_FILE")
nions=$(awk '/NIONS[[:space:]]*=/{print $12; exit}' "$OUTCAR_FILE")
dof=$(awk '/Degrees of freedom DOF/{for(i=1;i<=NF;i++) if($i=="="){print $(i+1); exit}}' "$OUTCAR_FILE")
idipol=$(awk '/IDIPOL[[:space:]]*=/{for(i=1;i<=NF;i++) if($i=="="){print $(i+1); exit}}' "$OUTCAR_FILE")

if [[ -z "${nfree:-}" || -z "${potim:-}" || -z "${nions:-}" || -z "${dof:-}" ]]; then
    echo "ERROR: Failed to parse NFREE, POTIM, NIONS, or DOF from $OUTCAR_FILE" >&2
    exit 1
fi

if [[ "$nfree" != "2" && "$nfree" != "4" ]]; then
    echo "ERROR: Only NFREE=2 or NFREE=4 supported. Found NFREE=$nfree" >&2
    exit 1
fi

nmodes=$dof
expected_dipoles=$((1 + dof * nfree))

# ------------------------------------------------------------
# Dipole moments: FULL vector (mux muy muz)
# ------------------------------------------------------------
awk '
/dipolmoment/ {
    lastx=$2; lasty=$3; lastz=$4; seen=1
}
/EDIFF is reached/ {
    if (seen) print lastx, lasty, lastz
}
' "$OUTCAR_FILE" > "$dipfile"

ndip=$(wc -l < "$dipfile" | awk '{print $1}')
if [[ "$ndip" -ne "$expected_dipoles" ]]; then
    echo "ERROR: Number of dipole entries ($ndip) != expected (1 + DOF*NFREE = $expected_dipoles)" >&2
    exit 1
fi

# ------------------------------------------------------------
# Frequencies in cm^-1
# ------------------------------------------------------------
grep 'THz' "$OUTCAR_FILE" | head -n "$nmodes" | awk '
{
    imag = ($0 ~ /f\/i/ || $0 ~ /fi[[:space:]]*=/)
    val = ""
    for (i = 1; i <= NF; i++) {
        if ($i == "cm-1") {
            val = $(i-1)
            break
        }
    }
    if (val != "") {
        if (imag) val = -val
        print val
    }
}
' > "$freqfile"

nfreq_read=$(wc -l < "$freqfile" | awk '{print $1}')
if [[ "$nfreq_read" -ne "$nmodes" ]]; then
    echo "ERROR: Number of frequencies read ($nfreq_read) != DOF ($nmodes)" >&2
    exit 1
fi

# ------------------------------------------------------------
# Selective dynamics flags from POSCAR/CONTCAR
# ------------------------------------------------------------
awk -v nions="$nions" '
NR==6 {
    line6_is_int=1
    for(i=1;i<=NF;i++) if ($i !~ /^-?[0-9]+$/) line6_is_int=0
}
NR==7 {
    line7_is_int=1
    for(i=1;i<=NF;i++) if ($i !~ /^-?[0-9]+$/) line7_is_int=0
}
{
    lines[NR]=$0
}
END {
    if (line6_is_int) {
        counts_line = 6
        coord_line  = 7
    } else if (line7_is_int) {
        counts_line = 7
        coord_line  = 8
    } else {
        print "ERROR_COUNTS"
        exit 1
    }

    nat=0
    split(lines[counts_line], a)
    for (i in a) nat += a[i]

    if (nat != nions) {
        print "ERROR_NIONS", nat, nions
        exit 1
    }

    selective = 0
    if (lines[coord_line] ~ /^[[:space:]]*[Ss]/) {
        selective = 1
        coord_line++
    }

    first_pos = coord_line + 1

    if (selective) {
        for (i=0; i<nions; i++) {
            n = split(lines[first_pos+i], t)
            if (n < 6) {
                print "ERROR_FLAGS", first_pos+i
                exit 1
            }
            print t[4], t[5], t[6]
        }
    } else {
        for (i=1; i<=nions; i++) print "T T T"
    }
}
' "$POS_FILE" > "$selfile"

if grep -q '^ERROR_' "$selfile"; then
    echo "ERROR: Failed to parse Selective dynamics / atom counts from $POS_FILE" >&2
    cat "$selfile" >&2
    exit 1
fi

active_dof=$(awk '
{
    for(i=1;i<=3;i++) {
        if (toupper($i)=="T") c++
    }
}
END {print c+0}
' "$selfile")

if [[ "$active_dof" -ne "$dof" ]]; then
    echo "ERROR: Active Cartesian DOF from $POS_FILE ($active_dof) != DOF from OUTCAR ($dof)" >&2
    exit 1
fi

# ------------------------------------------------------------
# Eigenvectors from THz blocks
# ------------------------------------------------------------
naa=$((nions + 1))

grep -A"$naa" 'THz' "$OUTCAR_FILE" | grep -v '^--$' > "$modes0"
sed '/ THz /{N;d;}' "$modes0" > "$modes1"

: > "$evfile"
for ((m=1; m<=nmodes; m++)); do
    end=$((m * nions))
    head -n "$end" "$modes1" | tail -n "$nions" | awk '{print $4, $5, $6}' >> "$evfile"
done

nev=$(wc -l < "$evfile" | awk '{print $1}')
if [[ "$nev" -ne $((nmodes*nions)) ]]; then
    echo "ERROR: Number of eigenvector lines ($nev) != nmodes*nions ($((nmodes*nions)))" >&2
    exit 1
fi

# ------------------------------------------------------------
# Build unified data file
# ------------------------------------------------------------
{
    echo "nfree $nfree"
    echo "potim $potim"
    echo "nions $nions"
    echo "dof $dof"
    echo "idipol ${idipol:-NA}"

    echo "dipoles"
    cat "$dipfile"

    echo "freqs"
    cat "$freqfile"

    echo "select"
    cat "$selfile"

    echo "evect"
    cat "$evfile"
} > "$datafile"

# ------------------------------------------------------------
# Final projection
# ------------------------------------------------------------
awk '
/^nfree /  { nfree=$2 }
/^potim /  { potim=$2 }
/^nions /  { nions=$2 }
/^dof /    { dof=$2 }
/^idipol / { idipol=$2 }

/^dipoles$/ { section="dipoles"; i=1; next }
/^freqs$/   { section="freqs";   i=1; next }
/^select$/  { section="select";  i=1; next }
/^evect$/   { section="evect";   i=1; next }

section=="dipoles" {
    mux[i]=$1; muy[i]=$2; muz[i]=$3
    i++
    next
}

section=="freqs" {
    freq[i]=$1
    i++
    next
}

section=="select" {
    sel[i]=$1; sel[i+1]=$2; sel[i+2]=$3
    i+=3
    next
}

section=="evect" {
    ev[i]=$1; ev[i+1]=$2; ev[i+2]=$3
    i+=3
    next
}

END {
    ndip = 0
    for (k in mux) ndip++
    nev = 0
    for (k in ev) nev++

    if (nev != 3*nions*dof) {
        print "ERROR: wrong number of eigenvector components read in final AWK" > "/dev/stderr"
        exit 1
    }

    dip_index = 2   # dipole 1 = reference
    active_count = 0

    for (j=1; j<=3*nions; j++) {
        dmx[j]=0.0; dmy[j]=0.0; dmz[j]=0.0

        if (toupper(sel[j])=="T") {
            active_count++

            if (nfree == 2) {
                dmx[j] = (mux[dip_index+1] - mux[dip_index]) / (2.0*potim)
                dmy[j] = (muy[dip_index+1] - muy[dip_index]) / (2.0*potim)
                dmz[j] = (muz[dip_index+1] - muz[dip_index]) / (2.0*potim)
                dip_index += 2
            }
            else if (nfree == 4) {
                dmx[j] = (mux[dip_index] - 8.0*mux[dip_index+1] + 8.0*mux[dip_index+2] - mux[dip_index+3]) / (12.0*potim)
                dmy[j] = (muy[dip_index] - 8.0*muy[dip_index+1] + 8.0*muy[dip_index+2] - muy[dip_index+3]) / (12.0*potim)
                dmz[j] = (muz[dip_index] - 8.0*muz[dip_index+1] + 8.0*muz[dip_index+2] - muz[dip_index+3]) / (12.0*potim)
                dip_index += 4
            }
            else {
                print "ERROR: unsupported NFREE in final AWK" > "/dev/stderr"
                exit 1
            }
        }
    }

    if (active_count != dof) {
        print "ERROR: active DOF mismatch in final AWK" > "/dev/stderr"
        exit 1
    }

    print "# mode   freq(cm-1)        dmu_x          dmu_y          dmu_z          |dmu|^2         legacy_x      legacy_x^2       legacy_y      legacy_y^2       legacy_z      legacy_z^2"
    for (m=1; m<=dof; m++) {
        norm=0.0
        px=0.0; py=0.0; pz=0.0

        for (j=1; j<=3*nions; j++) {
            idx=(m-1)*3*nions + j
            norm += ev[idx]*ev[idx]
        }
        norm = sqrt(norm)

        if (norm > 1.0e-14) {
            for (j=1; j<=3*nions; j++) {
                idx=(m-1)*3*nions + j
                fac = ev[idx] / norm
                px += dmx[j] * fac
                py += dmy[j] * fac
                pz += dmz[j] * fac
            }
        }

        p2  = px*px + py*py + pz*pz
        px2 = px*px
        py2 = py*py
        pz2 = pz*pz

        printf "%4d %12.2f %14.6f %14.6f %14.6f %18.12f %14.6f %18.12f %14.6f %18.12f %14.6f %18.12f\n", \
               m, freq[m], px, py, pz, p2, px, px2, py, py2, pz, pz2
    }

    print ""
    print "# Summary"
    print "# NIONS  =", nions
    print "# DOF    =", dof
    print "# NFREE  =", nfree
    print "# POTIM  =", potim
    print "# IDIPOL =", idipol
    print "# dipoles parsed =", ndip
}
' "$datafile"