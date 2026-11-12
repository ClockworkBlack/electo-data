#!/bin/bash
# The app's icon and opening screen as the image files the Android and iOS projects take, drawn from the SVGs here.
# Run by hand after changing an SVG (needs rsvg-convert and ImageMagick); the results are committed, so a build needs
# neither.   bash app/icon/make.sh
set -e
cd "$(dirname "$0")"
A=../android-patches/res; I=../ios-patches
BG='#F3F5F7'
rm -rf "$A"/mipmap-?dpi "$A"/mipmap-x*dpi "$A"/drawable*; mkdir -p "$A/values" "$I"
# Android: the icon (square and round for Android 7.1 and older; a foreground on a plain background for newer)
for d in mdpi:48:108 hdpi:72:162 xhdpi:96:216 xxhdpi:144:324 xxxhdpi:192:432; do
  IFS=: read -r name px fg <<< "$d"; mkdir -p "$A/mipmap-$name"
  rsvg-convert -w "$px" -h "$px" icon.svg -o "$A/mipmap-$name/ic_launcher.png"
  rsvg-convert -w "$px" -h "$px" icon-round.svg -o "$A/mipmap-$name/ic_launcher_round.png"
  rsvg-convert -w "$fg" -h "$fg" icon-fg.svg -o "$A/mipmap-$name/ic_launcher_foreground.png"
done
# (the background colour is in res/values/electo.xml, used by res/mipmap-anydpi-v26/ic_launcher*.xml; keep it the same as BG)
grep -q "$BG" "$A/values/electo.xml" || { echo "res/values/electo.xml does not carry $BG"; exit 1; }
# the opening screen: the mark in the middle of the site's background, one image per screen shape
splash() { # width height file
  local w=$1 h=$2 out=$3 m=$(( ($1 < $2 ? $1 : $2) * 34 / 100 ))
  rsvg-convert -w "$m" -h "$m" icon-fg.svg -o /tmp/electo-mark.png
  convert -size "${w}x${h}" "xc:$BG" /tmp/electo-mark.png -gravity center -composite -alpha off -strip "PNG24:$out"
}
mkdir -p "$A/drawable"; splash 480 320 "$A/drawable/splash.png"
for d in mdpi:320:480 hdpi:480:800 xhdpi:720:1280 xxhdpi:960:1600 xxxhdpi:1280:1920; do
  IFS=: read -r name w h <<< "$d"; mkdir -p "$A/drawable-port-$name" "$A/drawable-land-$name"
  splash "$w" "$h" "$A/drawable-port-$name/splash.png"; splash "$h" "$w" "$A/drawable-land-$name/splash.png"
done
# iOS: one 1024-pixel icon with no transparency, and one square opening image (the project shows its middle)
rsvg-convert -w 1024 -h 1024 icon.svg -o /tmp/electo-icon.png
convert /tmp/electo-icon.png -background "$BG" -alpha remove -alpha off -strip "PNG24:$I/AppIcon-512@2x.png"
splash 2732 2732 "$I/splash-2732x2732.png"
rm -f /tmp/electo-mark.png /tmp/electo-icon.png
du -sh "$A" "$I" | sed 's/^/icon files: /'
