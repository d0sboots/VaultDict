#!/bin/bash
# Simple utility for tracing pngs of the font glyphs. Records the settings I
# found that give the most faithful results, which took a lot of
# trial-and-error to find. Requires ImageMagick and potrace to do the actual
# tracing.
for a in "$@"; do
  OUT=`echo "$a"|sed s/.png$/.svg/`
  echo "Converting $a to $OUT..."
  convert "$a" -colorspace LinearGray -background black -alpha remove\
    -alpha off -filter triangle -resize 1024x1024 -blur 0x2\
    -threshold '72.5%' -negate -colorspace gray pbm:- |\
    potrace --svg --turdsize 8 --output "$OUT"
done
