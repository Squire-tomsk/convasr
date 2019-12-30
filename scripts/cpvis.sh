set -e

INPUTFILE=$1
OUTPUTDIR=./data/html

EXT=${INPUTFILE##*.}
DATE=$(date +%Y%m%d_%H%M%S)

OUTPUTFILENAME=$(basename "$INPUTFILE").$DATE.$EXT

cp "$INPUTFILE" "$OUTPUTDIR/$OUTPUTFILENAME"

echo $OUTPUTFILENAME
