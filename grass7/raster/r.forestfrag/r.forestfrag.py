#!/bin/sh
############################################################################
#
# MODULE:       r.forestfrag
#
# AUTHOR(S):    Emmanuel Sambale, Stefan Sylla, Paulo van Breugel
#
# PURPOSE:      Creates forest fragmentation index map from a forest-/
#		non-forest raster; The index map is based on Riitters,  
#               K., J. Wickham, R. O'Neill, B. Jones, and E. Smith. 2000. 
#               in: Global-scale patterns of forest fragmentation. 
#		Conservation Ecology 4(2): 3. [online] 
#		URL:http://www.consecol.org/vol4/iss2/art3/
# 
# NOTES		This addon is an adaptation of the r.forestfrag.sh addon, to 
#		work on GRASS 7.0 and to add the option to have the 
#		size of the moving window determined by the user. For now
#		it does not work on GRASS 6.4. Use r.forestfrag.sh instead.
#
# COPYRIGHT:    (C) 1997-2013 by the GRASS Development Team
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################

#%Module
#% description: creates forest fragmentation index from a GRASS raster map (where forest=1, non-forest=0) based on a method developed by Riitters et. al (2000). The index is computed using a moving window of user-defined size (default=3).
#% keywords: raster, forest, fragmentation-index, Riitters
#%End

#%Option
#% key: input
#% type: string
#% gisprompt: old,cell,raster
#% description: Name of forest raster map (where forest=1, non-forest=0)
#% required : yes
#%End

#%option
#% key: output
#% type: string
#% gisprompt: new
#% description: Name output layer
#% key_desc: name
#% required: yes
#%end

#%option
#% key: window
#% type: integer
#% description: Window size (odd number)
#% key_desc: number
#% answer : 3
#% required: yes
#%end

#%flag
#% key: r
#% description: Set region to raster?
#%end

#%flag
#%  key: t
#%  description: keep temporary maps
#%END

#%flag
#%  key: s
#%  description: Run r.report on output map
#%END

#%flag
#%  key: a
#%  description: shrink the output map?
#%END


# For testing purposes
#-----
#GIS_OPT_INPUT=ForestMosaic@Testing
#GIS_OPT_OUTPUT=FMtest
#GIS_OPT_WINDOW=3
#GIS_FLAG_R=0
#GIS_FLAG_T=1
#GIS_FLAG_S=1
#GIS_FLAG_A=1
#-----

#=======================================================================
## GRASS team recommandations
#=======================================================================

if [ -z "$GISBASE" ] ; then
    echo "You must be in GRASS GIS to run this program." 1>&2
    exit 1
fi

if [ "$1" != "@ARGS_PARSED@" ] ; then
    exec g.parser "$0" "$@"
fi

eval `g.findfile el=cell file=$GIS_OPT_INPUT`
if [ ! "$file" ] ; then
   echo "Raster map '$GIS_OPT_input' not found in mapset search path"
   exit 1
fi

#=======================================================================
## Prepare data
#=======================================================================

#set to current input map region (user option, default=current region)
#--------------------------------------------------------------------
if [ $GIS_FLAG_R -eq 1 ]; 
then
  echo "setting region to input map ..."
  g.region rast=$GIS_OPT_INPUT
fi 

# Set root name of temporary output files
#--------------------------------------------------------------------
tmpl=forestfrag$$_

# get map (assuming input-map is a cell-raster with forest=1, 
# and setting all other values to 0 (assuming to be non-forest=)
#--------------------------------------------------------------------
g.copy rast=${GIS_OPT_INPUT},${tmpl}
# recode forest-map: nonforest = 0, forest = 1
r.reclass in=${tmpl} out=${tmpl}A rules=- <<EOF
1 = 1
* = 0
end
EOF

#=======================================================================
# computing pf values
#=======================================================================

echo "computing pf values ..."

## let forested pixels be x and number of all pixels in moving window be y, then 
## pf=x/y"

# generate grid with pixel-value=number of forest-pixels in 3x3 moving-window: 
r.neighbors input=${tmpl}A output=${tmpl}A2 method=sum size=$GIS_OPT_WINDOW

# generate grid with pixel-value=number of pixels in moving window:
r.mapcalc "${tmpl}C3 = 1.0*$GIS_OPT_WINDOW^2" --overwrite

# create pf map
r.mapcalc file=- << EOF
${tmpl}A3 = 1.0 * ${tmpl}A2
${tmpl}pf = (${tmpl}A3/${tmpl}C3)
EOF

#=======================================================================
# computing pff values
#=======================================================================

echo "computing pff values ..."

## Considering pairs of pixels in cardinal directions in a 3x3 window, the total 
## number of adjacent pixel pairs is 12. Assuming that x pairs include at least 
## one forested pixel, and y of those pairs are forest-forest pairs, so pff equals 
## y/x"

# calculate number of 'forest-forest' pairs
#=======================================================================

echo "... calculate number of 'forest-forest' pairs"

SW=$GIS_OPT_WINDOW
tmpf=`g.tempfile pid=$$`
echo -n "${tmpl}F1 = " >> $tmpf

# Compute matrix dimensions
SWn=$(echo "($SW - 1) / 2" | bc)

# Write mapcalc expression to tmpf - rows
rsub=$(seq $SWn -1 -$SWn)
csub=$(seq -$SWn 1 $(echo "($SWn-1)" | bc))

for k in $rsub
do
  for l in $csub
  do
    echo -n "${tmpl}A[$k,$l]*${tmpl}A[$k,$(echo "$l+1" | bc)] + " >> $tmpf
   done
done

# Write mapcalc expression to tmpf - columns
rsub=$(seq -$SWn 1 $SWn)
csub=$(seq $SWn -1 $(echo "(-$SWn+1)" | bc))

for k in $rsub
do
  for l in $csub
  do
    echo -n "${tmpl}A[$l,$k]*${tmpl}A[$(echo "$l-1" | bc),$k] + " >> $tmpf
  done
done

echo -n "0" >> $tmpf
r.mapcalc file=$tmpf
unlink $tmpf

# number of 'forest-forest' pairs
#=======================================================================

tmpf2=`g.tempfile pid=$$$$`
echo -n "${tmpl}F2 = " >> $tmpf2

# Compute matrix dimensions
SWn=$(echo "($SW - 1) / 2" | bc)

# Write mapcalc expression to tmpf - rows
rsub=$(seq $SWn -1 -$SWn)
csub=$(seq -$SWn 1 $(echo "($SWn-1)" | bc))

for k in $rsub
do
  for l in $csub
  do
    echo -n "if((${tmpl}A[$k,$l]+${tmpl}A[$k,$(echo "$l+1" | bc)])>0,1) + " >> $tmpf2
   done
done

# Write mapcalc expression to tmpf - columns
rsub=$(seq -$SWn 1 $SWn)
csub=$(seq $SWn -1 $(echo "(-$SWn+1)" | bc))

for k in $rsub
do
  for l in $csub
  do
    echo -n "if((${tmpl}A[$l,$k]+${tmpl}A[$(echo "$l-1" | bc),$k])>0,1) + " >> $tmpf2
  done
done

echo -n "0" >> $tmpf2
r.mapcalc file=$tmpf2
unlink $tmpf2

# create pff map
r.mapcalc --overwrite file=- << EOF
${tmpl}F1 = 1.0 * ${tmpl}F1 
${tmpl}F2 = 1.0 * ${tmpl}F2
${tmpl}pff = ${tmpl}F1/${tmpl}F2
EOF

#=======================================================================
# computing fragmentation index
#=======================================================================

echo "computing fragmentation index ..."
# (1) patch                    pf < 0.4 
# (2) transitional             0.4 < pf < 0.6 
# (3) edge                     pf > 0.6 and pf - pff < 0 
# (4) perforated               pf > 0.6 and pf - pff > 0
# (5) interior for which       pf = 1.0 
# (6) undetermined             pf > 0.6 and pf = pff

r.mapcalc file=- << EOF
${tmpl}pf2 = ${tmpl}pf - ${tmpl}pff
${tmpl}f1 = if(${tmpl}pf<0.4,1,0)
${tmpl}f2 = if(${tmpl}pf>=0.4 && ${tmpl}pf<0.6,2,0)
${tmpl}f3 = if(${tmpl}pf>=0.6 && ${tmpl}pf2<0,3,0)
${tmpl}f4 = if(${tmpl}pf>0.6 && ${tmpl}pf2>0,4,0)
${tmpl}f5 = if(${tmpl}pf==1 && ${tmpl}pff==1,5,0)
${tmpl}f6 = if(${tmpl}pf>0.6 && ${tmpl}pf<1 && ${tmpl}pf2==0,6,0)
${tmpl}index = ${tmpl}f1+${tmpl}f2+${tmpl}f3+${tmpl}f4+${tmpl}f5+${tmpl}f6
${tmpl}indexfin2 = ( ${tmpl}A * ${tmpl}index )
EOF

#create categories
echo "creating colors and categories ... "
r.reclass ${tmpl}indexfin2 out=${tmpl}indexfin3 title="frag index" rules=- <<EOF
0 = 0 nonforest
1 = 1 patch
2 = 2 transitional
3 = 3 edge
4 = 4 perforated
5 = 5 interior
6 = 6 undef
EOF


# Shrink the region
g.region save=rforestfrag987654321 --overwrite
if [ $GIS_FLAG_A -eq 1 ]; 
then
  NSRES=`g.region -p -g | grep nsres= | cut -f2 -d"="`
  EWRES=`g.region -p -g | grep ewres= | cut -f2 -d"="`
  NSCOR=$(echo "$SW*$NSRES*0.5" | bc)
  EWCOR=$(echo "$SW*$EWRES*0.5" | bc)
  g.region n=n-$NSCOR s=s+$NSCOR e=e-$EWCOR w=w+$EWCOR
fi 

r.mapcalc "${GIS_OPT_OUTPUT} = ${tmpl}indexfin3"
r.null ${GIS_OPT_OUTPUT} null=0

#create color codes
r.colors ${GIS_OPT_OUTPUT} --quiet rules=- << EOF
0 255:255:0
1 215:48:39
2 252:141:89
3 254:224:139
4 217:239:139
5 26:152:80
6 145:207:96
EOF

#=======================================================================
# Clean up (user option: copy pf, pff, pf2 first)
#=======================================================================

if [ $GIS_FLAG_T -eq 1 ]; 
then
  g.copy rast=${tmpl}pf,${GIS_OPT_OUTPUT}_pf
  g.copy rast=${tmpl}pff,${GIS_OPT_OUTPUT}_pff
  g.copy rast=${tmpl}pf2,${GIS_OPT_OUTPUT}_pf2
fi 

echo "Deleting temporary files ...."
g.mremove -f -b --quiet rast=${tmpl}*

#=======================================================================
# computing fragmentation index
#=======================================================================
  
if [ $GIS_FLAG_S -eq 1 ]; 
then
  
  g.copy rast=${GIS_OPT_OUTPUT},${tmpl}_REPORT
  # Shrink the region if output map was not trimmed
  if [ $GIS_FLAG_A -eq 0 ]; 
  then
    NSRES=`g.region -p -g | grep nsres= | cut -f2 -d"="`
    EWRES=`g.region -p -g | grep ewres= | cut -f2 -d"="`
    NSCOR=$(echo "$SW*$NSRES*0.5" | bc)
    EWCOR=$(echo "$SW*$EWRES*0.5" | bc)
    g.region save=rforestfrag987654321
    g.region n=n-$NSCOR s=s+$NSCOR e=e-$EWCOR w=w+$EWCOR
  fi 

  echo "generate map reports ..."
  r.report map=${tmpl}_REPORT units=h,p -n
  echo "  "
  echo "------------------------------------------------------"
  echo "Please note in order to avoid edge effects, the region"
  echo "is reduced / shrinked with a number of raster cells"
  echo "equal to 1/2 the moving window size before running"
  echo "r.report, unless the user has already selected the "
  echo "option to trim the output map with number of cells equal"
  echo "to 1/2 the moving window size (default)."
  echo "------------------------------------------------------"
  echo "  "
fi

g.remove rast=${tmpl}_REPORT --quiet
g.region region=rforestfrag987654321
g.remove --quiet region=rforestfrag987654321 









