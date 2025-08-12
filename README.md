# ngen-regionalization

## Name
NGEN Regionalization

## Description
This repository includes packages for conducting formulation and parameter regionalizations for NextGen modules.
- parreg: parameter regionalization

### Clone & Build

1. clone ngen-regionalization from Gitlab

```bash
cd [NGEN_REG_ROOT]
git clone -b development --recurse-submodules https://gitlab.sh.nextgenwaterprediction.com/NGWPC/nwm-ngen/ngen-regionalization.git
```

2. create python venv

```bash
cd [VENV_ROOT]
/usr/bin/python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```
3. install parreg

```bash
cd [NGEN_REG_ROOT]/pkgs/parreg
pip install . #or use "pip install -e ." to install the package as an editable 
```
4. install formreg

```bash
cd [NGEN_REG_ROOT]/pkgs/formreg
pip install . #or use "pip install -e ." to install the package as an editable 
```
5. install utils

```bash
cd [NGEN_REG_ROOT]/pkgs/utils
pip install . #or use "pip install -e ." to install the package as an editable 
```

where [VENV_ROOT] and [NGEN_REG_ROOT] refer to the directory to install python venv and ngen-regionalization 
in your local workspace, respectively


### Usage

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




