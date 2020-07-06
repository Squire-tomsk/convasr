#!/bin/bash

BITRATE=$3
PREFIX=$2
DIR=$1

cp -r $DIR $DIR"_"$PREFIX

for f in "$DIR""_""$PREFIX"/*/*/*; do
  if [ -d "$f" ]; then
    for file in "$f"/*.wav; do
      (
      sourcefile=$file
      filename="${file%.*}"
      destfile="$filename.gsm"

      echo $sourcefile;
      ffmpeg -i $sourcefile -c:a libgsm -vn -ar 8000 -ac 1 -ab 13000 -f gsm $destfile
      rm $sourcefile
      ffmpeg -i $destfile -loglevel error -v quiet -acodec pcm_s16le -ar 8000 -ac 1 $sourcefile
      rm $destfile
      ) &
    done
    wait
  fi
done


