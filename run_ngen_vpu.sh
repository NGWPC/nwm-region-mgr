#!/bin/bash
# This script runs run_ngen_vpu.py script with various arguments
# Adjust the paths and parameters as needed for your setup
# Note this script must run with MSWM installed in the virtual environment
python run_ngen_vpu.py \
  --vpu vpu_09 \
  --run_name gower \
  --work_dir ~/repos/nwm-region-mgr/data/ \
  --start_time 2022-10-01T00:00:00 \
  --end_time 2022-10-01T10:00:00 \
  --par_file ~/repos/nwm-region-mgr/data/outputs/test3/params/formulation_params_gower_conus_vpu09.csv \
  --pair_file ~/repos/nwm-region-mgr/data/outputs/test3/pairs/pairs_gower_conus_vpu09_mswm.csv \
  --forcing_dir ~/repos/nwm-region-mgr/data/inputs/forcing/vpu_09 \
  --gpkg_file ~/repos/nwm-region-mgr/data/inputs/hydrofabric/gpkg_vpu/vpu_09_patch.gpkg \
  --config_template ~/repos/nwm-region-mgr/sample_files/configs/mswm.config.template \
  --ngen_venv_path ~/repos/ngen/venv \
  --nprocs 2 \