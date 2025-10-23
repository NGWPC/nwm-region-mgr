# nwm-region-mgr

## Name
NGEN/NWM Regionalization

## Description
This repository includes packages for conducting formulation and parameter regionalizations for NextGen modules,
as well as scripts/workflows to run ngen simulations and evaluation.
- parreg: parameter regionalization
- formreg: formulation regionalization
- utils: utility functions shared by parreg and formreg

## Clone & Build

### 1. clone ngen-region-mgr from Github

```bash
cd [NGEN_REG_ROOT]
git clone -b development --recurse-submodules https://github.com/NGWPC/nwm-region-mgr.git
```

### 2. create python venv

```bash
cd [VENV_ROOT]
/usr/bin/python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```
### 3. install nwm-region-mgr

```bash
cd [NGEN_REG_ROOT]
pip install . # to install formreg and utils only
# OR
pip install nwm_region_mgr[parreg] # to install formreg, utils, and parreg 
```

where [VENV_ROOT] and [NGEN_REG_ROOT] refer to the directory to install python venv and nwm-region-mgr 
in your local workspace, respectively


## STEP 1: Run regionalization to produce regionalized parameters and formulations

### 1) Set up configuration yaml files

Three yaml config files are needed to run regionalization
- **config_general.yaml**: general settings for the overall regionalization process.
- **onfig_formreg.yaml**: specific settings for the formulation regionalization process.
- **config_parreg.yaml**: specific settings for the parameter regionalization process.

Follow the sample [config files](https://github.com/NGWPC/nwm-region-mgr/tree/development/sample_files/configs) to set up the configurations for your regionalization application as needed.

Sample input data can be downloaded from **s3://ngwpc-dev/Yuqiong.Liu/repos/nwm-region-mgr**


### 2) Run the regionalization script

```bash
python [NGEN_REG_ROOT]/nwm-region-mgr/regionalization.py [COFIG_DIR]
```
Where: 
- [NGEN_REG_ROOT] refers to the directory where nwm-region-mgr is installed
- [COFIG_DIR] refers to the directory containing the three config files as noted in 1), e.g.,

```bash
python regionalization.py sample_files/configs
```

## STEP 2: Run NGEN simulation with regionalized parameters

### 1) Install [ngen](https://github.com/NGWPC/ngen) and all submodules in its own venv
You may want to follow the following Confluence pages:
- [Clone ngen](https://confluence.nextgenwaterprediction.com/display/NGWPC/Clone+NGWPC+GitHub+Code)
- [Build ngen](https://confluence.nextgenwaterprediction.com/display/NGWPC/Build+ngen+completely)
  
### 2) Install [mswm](https://github.com/NGWPC/nwm-msw-mgr) in its own venv

### 3) Activate MSWM venv, e.g.
```bash
source ~/repos/nwm-msw-mgr/venv/bin/activate
```
### 4) Set up MSWM configuration as shown in [run_ngen_vpu.sh](https://github.com/NGWPC/nwm-region-mgr/blob/development/run_ngen_vpu.sh)
Note you would need some

### 5) Run MSWM and ngen simulation
```bash
cd ~/repos/nwm-region-mgr
./run_ngen_vpu.sh
```
### 6) Check inputs, outputs and logs
All input, output and log files from running MSWM and NGEN can be found in *[work_dir]/regionalization/[run_name]/[vpu]* 
(as defined in **run_ngen_vpu.sh**)

### 7) If ngen fails at t-route
Check if all NGEN cat-*.csv and nex-*.csv output files are generated; if yes,
run t-route separately from the Output directory where ngen outputs are located, e.g.,
```bash
python -m nwm_routing -f -V4 ../Input/vpu_09_troute_config_region.yaml
```

## STEP 3: Evaluate NGEN simulation with nwm.verf

### 1) Donwload and install [nwm.verf](https://github.com/NGWPC/nwm-verf)
It is recommentded you install nwm.verf in its own venv. Note [nwm.eval](https://github.com/NGWPC/nwm-eval-mgr) needs to installed as a dependency

### 2) Set up configurations for evaluation
Follow example config at [config_eval.yaml](https://github.com/NGWPC/nwm-region-mgr/blob/development/sample_files/configs/config_eval.yaml)

Check out what metrics are currently supported [here](https://confluence.nextgenwaterprediction.com/display/NGWPC/Forecast+Verification+%28ngen-verf%29%3A+Configuration)

Sample input data can be downloaded from **s3://ngwpc-dev/Yuqiong.Liu/repos/nwm-verf** and are also available in [Github](https://github.com/NGWPC/nwm-verf/tree/development/data)

### 3) Activate venv for nwm.verf
```bash
source ~/repos/nwm-verf/venv/bin/activate
```
### 4) Run evaluation
```bash
python -m nwm.verf config_eval.yaml
```
### 5) Check outputs
Outputs from evaluation can be found in *[output_dir]* as specified in **config_eval.yaml**


## Test regionalization for other VPUs or different formulations

- Create pseudo forcing data by recycling existing forcing files, using this [script](https://github.com/NGWPC/nwm-region-mgr/blob/yliu_NGPWC-6984/util_scripts/run_create_pseudo_forcing_csv.sh)
- Create new pseduo calibration/validation stats for different formulations, using this [script](https://github.com/NGWPC/nwm-region-mgr/blob/yliu_NGPWC-6984/util_scripts/run_create_pseudo_calval_stats.sh)
- Create geopackages for a new VPU using this [script](https://github.com/NGWPC/nwm-region-mgr/blob/yliu_NGPWC-6984/util_scripts/subset_conus_gpkg_by_vpu.py)
- Create gage list files and NGEN divide-gage crosswalk file for a new domain using this [script](https://github.com/NGWPC/nwm-verf/blob/yliu_NGWPC-6986/utils/create_ngen_crosswalk_regionalization.py)
