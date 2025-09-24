# Formulation and Parameter Regionalization for the NextGen Framework
[![Build](https://img.shields.io/github/actions/workflow/status/ngwpc/nwm-region-mgr/ci.yaml?branch=main)](.github/workflows/ci.yml)
[![License](https://img.shields.io/github/license/ngwpc/nwm-region-mgr)](LICENSE)
[![Release](https://img.shields.io/github/v/release/ngwpc/nwm-region-mgr)](https://github.com/fema-ffrd/gpras/releases)
![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-orange.svg)
![Linter: Ruff](https://img.shields.io/badge/linter-ruff-orange)

`ngen-regionalization` is a Python package for identifying optimal model formulations and parameter values in **ungauged catchments**. It leverages calibration data from gauged catchments to improve hydrologic modeling and forecasting skill across regions, playing a key role in the NextGen and NWM ecosystem.


## Key Features

- **Formulation Regionalization** – Ranks NextGen model formulations for ungauged catchments based on similarity to gauged sites.
- **Parameter Regionalization** – Estimates parameter values by intelligently transferring calibrations across catchments.
- **Clustering Methods** – Groups catchments with shared hydrologic characteristics using multiple clustering approaches.
- **Diagnostic Plots** – Generates clear plots and maps that explain formulation and parameter choices.
- **Scalable Workflows** – Efficiently supports studies from individual watersheds to CONUS-wide applications.
- **Customizable Configurations** – Full control of workflows via human-readable config files.

```bash
cd [NGEN_REG_ROOT]
git clone -b development --recurse-submodules https://github.com/NGWPC/nwm-region-mgr.git
```

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


## Usage

1) set up configuration yaml files

Three yaml config files are needed to run regionalization
- config_general.yaml: contains general settings for the regionalization process.
- onfig_formreg.yaml: contains specific settings for the formulation regionalization process.
- config_parreg.yaml: contains specific settings for the parameter regionalization process.

Follow the sample config files (ngen-regionalization/sample_files/configs) to set up the configurations
for your regionalization application as needed.

Sample data can be downloaded from s3://ngwpc-dev/Yuqiong.Liu/data/ngen_reg/
- input data: ./inputs
- log file: ./logs/test1.log
- output files: ./outputs/test1

2) run the regionalization script

```bash
python [NGEN_REG_ROOT]/ngen-regionalization/regionalization.py [COFIG_DIR]
```
Where [NGEN_REG_ROOT] refers to the directory where ngen-regionalization is installed
[COFIG_DIR] refers to the directory containing the three config files as noted in 1), e.g.,

```bash
python regionalization.py sample_files/configs
```




