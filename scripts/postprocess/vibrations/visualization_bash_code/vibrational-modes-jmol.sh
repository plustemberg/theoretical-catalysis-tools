#------------------------------------------------
# This script generates a vibrational animation
# that can be visualized with Jmol.
#
# Current example: CO adsorbed on MgO
# Required input files: OUTCAR and CONTCAR
# Output files:
#   - frequency-values.dat
#   - vibrational-modes.xyz
#------------------------------------------------

#------------------------------------------------
# The number of normal modes is counted
#------------------------------------------------
grep 'THz' OUTCAR > frequency-values.dat
wc -l frequency-values.dat > nfre.dat
nfre=` awk ' NR==1,NR==1 {print($1)}' nfre.dat`
echo Nfs = $nfre

rm nfre.dat

#------------------------------------------------


#------------------------------------------------
# VIBRATIONAL MODES
#------------------------------------------------
nMg=` awk ' NR==7,NR==7 {print($1)}' CONTCAR`
nO=` awk ' NR==7,NR==7 {print($2)}' CONTCAR`
nC=` awk ' NR==7,NR==7 {print($3)}' CONTCAR`

N_atomos=`bc <<!
$nMg + $nO + $nC
!`

echo Nº de Átomos = $N_atomos 

naa=`bc <<!
$N_atomos+1
!`


grep -A$naa 'THz' OUTCAR > modes_0
sed '/ THz /{N;d;}' modes_0 > modes_1

rm modes_0 

for (( i = 1 ; i <= $nfre ; i++ ))
do

echo Iteration Nº = $i / $nfre 

nn=`bc <<!
($i-1)*($N_atomos + 1.) + $N_atomos
!`


head -n $nn modes_1 > pru-$i
tail -n $N_atomos pru-$i >> modes-$i


awk ' NR==('1'),NR==('$nMg') {print "Mg",$1,$2,$3,$4,$5,$6}' modes-$i >> ver-$i
awk ' NR==('$nMg+1'), NR==('$nO+$nMg') {print "O",$1,$2,$3,$4,$5,$6}' modes-$i >> ver-$i
awk ' NR==('$nMg+$nO+1'), NR==('$nO+$nMg+$nC') {print "C",$1,$2,$3,$4,$5,$6}' modes-$i >> ver-$i


echo   $N_atomos  >> vibrational-modes.xyz
echo       >> vibrational-modes.xyz
cat ver-$i >> vibrational-modes.xyz

done


rm modes*
rm pru* ver*








