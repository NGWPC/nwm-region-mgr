#!/bin/bash

vpus=("01" "02" "03W" "03S" "03N" "04" "05" "06" "07" "08" "09" "10L" "10U" "11" "12" "13" "14" "15" "16" "17" "18")

# loop through vpus and create subset geopackages
for vpu in "${vpus[@]}"; do

    # check if gpkg file for the vpu directory exists, if not create it
    gpkg_file="$HOME/data/hydrofabric/gpkg_vpu/vpu_${vpu}_patch.gpkg"
    if [ -f "$gpkg_file" ]; then
        echo "GPKG file for VPU $vpu already exists, skipping..."
        continue
    else
        echo "Creating GPKG file for VPU $vpu..."
        python subset_conus_gpkg_by_vpu.py --vpu $vpu
    fi
done


