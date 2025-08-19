# User Guide

the steps below show how to install and use ngen-regionalization in your local environment. At the end, some example workflows are described.

## Installation

Installing ngen-regionalization requires

 - Python 3.11
 - Python venv (typically included with Python)
 - git

Since ngen-regionalization is not currently on PyPI, it must be installed from source. To download this repository, run

```bash
git clone https://github.com/NGWPC/nwm-region-mgr.git
cd nwm-region-mgr
```

To get the most up-to-date code, switch to the development branch.

```bash
git checkout development
```

Next, create a virtual environment to isolate the dependencies of this library from your base Python environment.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

You will then be able to install ngen-regionalization. There are a few download variants that users may be interested in.

```bash
# Regular package install
pip install .
# Install the package in edit mode (for development)
pip install -e .
# Install the additional dependencies for parameter regionalization
pip install .[parreg]
```

## Configuration Files

Users may control regionalization behavior by adjusting several configuration files.

 - config_general.yaml: contains general settings for the regionalization process.
 - config_formreg.yaml: contains specific settings for the formulation regionalization process.
 - config_parreg.yaml: contains specific settings for the parameter regionalization process.

Examples are available in `sample_files/configs` or they may be developed with the Config Builder on this website.

## Executing ngen-regionalization

To run the regionalization script, you can use the following command.

```bash
python regionalization.py sample_files/configs
```

## Output Structure

```bash
.
├── attr_data_final  # Description of folder
│   ├── attr_conus_vpu01.parquet  # Description of file
│   └── plots
│       ├── bar_attr_missing_count_conus_vpu01.png  # Description of plot
│       ├── hist_attr_conus_vpu01.png
│       └── map_attr_conus_vpu01.png
├── config_formreg_final.yaml
├── config_parreg_final.yaml
├── formulations
│   ├── form_conus_vpu01.parquet
│   ├── form_conus_vpu01_slim.parquet
│   ├── form_conus_vpu02.parquet
│   ├── form_conus_vpu02_slim.parquet
│   └── plots
│       ├── hist_form_conus_vpu01.png
│       ├── hist_form_conus_vpu02.png
│       ├── map_form_conus_vpu01.png
│       └── map_form_conus_vpu02.png
├── pairs
│   ├── pairs_gower_conus_vpu01.parquet
│   └── plots
│       ├── hist_pairs_gower_conus_vpu01.png
│       ├── map_donors_conus_vpu01.png
│       └── map_pairs_gower_conus_vpu01.png
├── spatial_distance
│   └── donor_receiver_dist_conus_vpu01.parquet
└── summary_score
    ├── plots
    │   ├── hist_score_conus_vpu01.png
    │   ├── hist_score_conus_vpu02.png
    │   ├── map_score_conus_vpu01.png
    │   └── map_score_conus_vpu02.png
    ├── score_conus_all_gages.parquet
    ├── score_conus_vpu01.parquet
    └── score_conus_vpu02.parquet
```


## Example Workflows

### Adjusting formulation summary score weights

Say that you reviewed the formulation results and found that nse and kge were doing a poor job assessing formulation performance.  You could adjust the weights and re-run.

```YAML
metrics:
cor:
    upper: 1.0
    lower: -0.5
    orientation: positive
    weight: 0.35
kge:
    upper: 1.0
    lower: -0.5
    orientation: positive
    weight: 0.05
nse:
    upper: 1.0
    lower: -0.5
    orientation: positive
    weight: 0.05
bias:
    upper: 300.0
    lower: 0.0
    orientation: negative
    weight: 0.35
    absolute: True
far:
    upper: 1.0
    lower: 0.0
    orientation: negative
    weight: 0.2
```

### Stopping snow cover check

Say snow cover is leading to too many basins without donors...
