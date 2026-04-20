#!/bin/bash
set -euo pipefail

id_type="gage_id"
version="v1"
#domain="CONUS"
domain="Puerto Rico"
#domain="Hawaii"
#domain="Alaska"

gages_file="$HOME/repos/nwm-region-mgr/data/inputs/region/gages_nwm4_calib_all.csv"
dest_dir="$HOME/data/hydrofabric/gpkg_nhf/${domain// /_}/"
failed_log="$dest_dir/failed_gages.txt"

mkdir -p "$dest_dir"
: > "$failed_log"

# safer iteration (avoids word-splitting issues)
while read -r gage; do
    dest_file="${dest_dir}/${gage}.gpkg"
    tmp_file="${dest_file}.tmp"

    if [[ -f "$dest_file" ]]; then
        echo "File for Gage $gage already exists, skipping."
        continue
    fi

    echo "Downloading GPKG for Gage $gage..."
    #url="https://edfs.oe.nextgenwaterprediction.com/api/${version}/hydrofabric/$gage/gpkg?id_type=${id_type}"
    url="http://edfs.test.nextgenwaterprediction.com/api/${version}/hydrofabric/${gage}/gpkg?id_type=gage_id&source=nhf&domain=${domain}&layers=divides&layers=flowpaths&layers=network&layers=nexus&layers=virtual_nexus&layers=virtual_flowpaths&layers=waterbodies&layers=gages&layers=reference_flowpaths&layers=hydrolocations%27"

    max_retries=3
    attempt=1
    success=false

    while [[ $attempt -le $max_retries ]]; do
        http_code=$(curl -s -w "%{http_code}" -L \
            --connect-timeout 10 --max-time 60 \
            -o "$tmp_file" "$url")

        if [[ "$http_code" == "200" ]]; then
            mv "$tmp_file" "$dest_file"
            success=true
            break
        fi

        echo "Attempt $attempt failed for $gage (HTTP $http_code)"

        if [[ "$http_code" =~ ^(502|503|504)$ ]]; then
            sleep 5
            ((attempt++))
        else
            break
        fi

    done

    if [[ "$success" = false ]]; then
        echo "Failed for gage: $gage (last HTTP $http_code)"
        rm -f "$dest_file"
        echo "$gage,$http_code" >> "$failed_log"
    fi

done < <(
python - <<EOF
import csv

with open("$gages_file", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["domain"] == "$domain":
            print(row["gage_id"])
EOF
)

echo "Done. Failed gages saved to: $failed_log"