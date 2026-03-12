#!/usr/bin/env bash
#-----------------------------------------------------------------------
# Dynamic dipole moments from finite-difference phonons in VASP
# Requires: IBRION=5, IDIPOL=3, LDIPOL=.TRUE.
# Supports NFREE = 2 or 4
#-----------------------------------------------------------------------

outfile='dyndip.data'
rm -f "$outfile" dipolread.dat modes_0 modes_1

#----------------------------
# Basic data from OUTCAR
#----------------------------
nfree=$(grep "NFREE  =" OUTCAR | awk '{print $3}' | tail -n 1)
potim=$(grep "POTIM  =" OUTCAR | awk '{print $3}' | tail -n 1)
nions=$(grep "NIONS" OUTCAR | awk '{print $12}' | tail -n 1)
nmodes=$(grep "   Degr" OUTCAR | awk '{print $6}' | tail -n 1)

echo "nfree $nfree" > "$outfile"
echo "potim $potim" >> "$outfile"
echo "nions $nions" >> "$outfile"

#----------------------------
# Dipoles from OUTCAR
#----------------------------
numdip=$((nmodes * nfree + 1))
echo "dipols $numdip" >> "$outfile"

grep -E 'EDIFF is reached|electrons x Angst' OUTCAR > dipolread.dat
grep 'EDIFF is reached' -B1 dipolread.dat | awk '/electrons x Angst/ {print $4}' >> "$outfile"
rm -f dipolread.dat

#----------------------------
# Frequencies from OUTCAR
# Use exactly nmodes entries
#----------------------------
echo "freqs" >> "$outfile"

grep 'THz' OUTCAR | head -n "$nmodes" | awk '
{
    imag = 0
    if ($0 ~ /f\/i/ || $0 ~ / fi / || $0 ~ /fi =/) imag = 1

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
' >> "$outfile"

#----------------------------
# Selective dynamics from POSCAR
#----------------------------
echo "select" >> "$outfile"

line8=$(sed -n '8p' POSCAR)

if [[ "$line8" =~ ^[Ss] ]]; then
    pos_start=10
    pos_end=$((pos_start + nions - 1))
    sed -n "${pos_start},${pos_end}p" POSCAR | awk '{print $4,$5,$6}' >> "$outfile"
else
    for ((i=1; i<=nions; i++)); do
        echo "T T T" >> "$outfile"
    done
fi

#----------------------------
# Eigenvectors from OUTCAR
# Use exactly nmodes blocks
#----------------------------
echo "evect" >> "$outfile"

awk -v nmodes="$nmodes" '
/NIONS/ {
    nions = $12
}

/X[[:space:]]+Y[[:space:]]+Z[[:space:]]+dx[[:space:]]+dy[[:space:]]+dz/ {
    ifreq++
    ion = 0
    take = (ifreq <= nmodes)
    next
}

take && ion < nions {
    ion++
    printf "%14.6f %14.6f %14.6f\n", $4, $5, $6
    if (ion == nions) take = 0
}
' OUTCAR >> "$outfile"

#----------------------------
# Final AWK processing
#----------------------------
awk '
/nfree/   { nfree=$2 }
/potim/   { potim=$2 }
/nions/   { nions=$2 }

e==1 && !/freqs/ {
    dipol[i]=$1
    i++
}

e==2 && !/select/ {
    freq[i]=$1
    i++
}

e==3 && !/evect/ {
    select[i]=$1
    select[i+1]=$2
    select[i+2]=$3
    i=i+3
}

e==4 {
    evect[i]=$1
    evect[i+1]=$2
    evect[i+2]=$3
    i=i+3
}

/dipols/ { e=1; i=1; ndip=$2 }
/freqs/  { e=2; i=1 }
/select/ { e=3; i=1 }
/evect/  { e=4; i=1 }

END {
    if (nfree == 2) idip=1
    else if (nfree == 4) idip=0
    else {
        print "only nfree=2 or 4 supported!!"
        exit
    }

    for (i=1; i<=3*nions; i++) {
        dipvec[i]=0
        if (select[i] == "t" || select[i] == "T") {
            idip = idip + nfree
            dipvec[i] = (dipol[idip] - dipol[idip-1]) / (2.0 * potim)
        }
    }

    nmodes = (ndip - 1) / nfree

    print "   #        freq(cm)   freq(THz) freq(meV)       dyndip        dyndip^2"
    for (m=1; m<=nmodes; m++) {
        dipmom=0.0
        norm=0.0

        for (k=1; k<=3*nions; k++) {
            idx = (m-1)*3*nions + k
            norm += evect[idx]^2
        }
        norm = sqrt(norm)

        if (norm > 1.0e-12) {
            for (j=1; j<=3*nions; j++) {
                idx = (m-1)*3*nions + j
                dipmom += dipvec[j] * evect[idx] / norm
            }
        }

        printf "%4d %14.2f %10.3f %10.3f %14.6f %14.12f\n", \
               m, freq[m], freq[m]*0.0299792, freq[m]*0.123986, dipmom, dipmom*dipmom
    }
}
' < "$outfile"