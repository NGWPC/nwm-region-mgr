#!/bin/bash
# Download GPKG files for all gages in the calibration set, using the NHF API.
set -euo pipefail

id_type="gage_id"
version="v1"
domain="CONUS"

gages_file="$HOME/repos/nwm-region-mgr/data/inputs/region/gages_nwm4_calib_all.csv"
dest_dir="$HOME/data/hydrofabric/gpkg_nhf/$domain/"
failed_log="$dest_dir/failed_gages.txt"

mkdir -p "$dest_dir"
: > "$failed_log"   # clear previous log

gages=$(awk -F',' 'NR>1 {gsub(/"/, "", $1); print $1}' "$gages_file")

for gage in $gages; do
    dest_file="${dest_dir}${gage}.gpkg"

    if [[ -f "$dest_file" ]]; then
        echo "File for Gage $gage already exists, skipping."
        continue
    fi

    echo "Downloading GPKG for Gage $gage..."
    url="https://edfs.oe.nextgenwaterprediction.com/api/${version}/hydrofabric/$gage/gpkg?id_type=${id_type}"

    # handle failure and log failed gages
    if ! curl -fL --progress-bar -o "$dest_file" "$url"; then
        echo "Failed for gage: $gage"

        # remove partial file if created
        rm -f "$dest_file"

        # log failure
        echo "$gage" >> "$failed_log"

        continue
    fi
done

echo "Done. Failed gages saved to: $failed_log"