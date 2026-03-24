#!/bin/bash
set -euo pipefail

id_type="gage_id"
version="v1"
domain="CONUS"

gages_file="$HOME/repos/nwm-region-mgr/data/inputs/region/gages_nwm4_calib_all.csv"
dest_dir="$HOME/data/hydrofabric/gpkg_nhf/$domain/"
failed_log="$dest_dir/failed_gages.txt"

mkdir -p "$dest_dir"
: > "$failed_log"

# safer iteration (avoids word-splitting issues)
while read -r gage; do
    dest_file="${dest_dir}${gage}.gpkg"

    if [[ -f "$dest_file" ]]; then
        echo "File for Gage $gage already exists, skipping."
        continue
    fi

    echo "Downloading GPKG for Gage $gage..."
    url="https://edfs.oe.nextgenwaterprediction.com/api/${version}/hydrofabric/$gage/gpkg?id_type=${id_type}"

    max_retries=3
    attempt=1
    success=false

    while [[ $attempt -le $max_retries ]]; do
        # capture HTTP status
        http_code=$(curl -s -w "%{http_code}" -L -o "$dest_file" "$url" || echo "000")

        if [[ "$http_code" == "200" ]]; then
            success=true
            break
        fi

        echo "Attempt $attempt failed for $gage (HTTP $http_code)"

        # retry only for transient errors
        if [[ "$http_code" =~ ^(502|503|504)$ ]]; then
            sleep 5
            ((attempt++))
        else
            # non-retryable error (e.g., 404)
            break
        fi
    done

    if [[ "$success" = false ]]; then
        echo "Failed for gage: $gage (last HTTP $http_code)"
        rm -f "$dest_file"
        echo "$gage,$http_code" >> "$failed_log"
    fi

done < <(awk -F',' 'NR>1 {gsub(/"/, "", $1); print $1}' "$gages_file")

echo "Done. Failed gages saved to: $failed_log"