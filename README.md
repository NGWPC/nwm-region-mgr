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

where [VENV_ROOT] and [NGEN_REG_ROOT] refer to the directory to install python venv and ngen-regionalization 
in your local workspace, respectively


### Usage

1) set up configuration yaml file (e.g., config.yaml)

Follow the sample config file (ngen-regionalization/sample_files/config.yaml) to set up the configurations 
for your regionalization application as needed.

Sample data can be downloaded from s3://ngwpc-dev/Yuqiong.Liu/data/ngen_reg/

2) run the regionalization script

```bash
python [NGEN_REG_ROOT]/ngen-regionalization/regionalization.py config.yaml
```

3) repeat the first two steps as many times as needed


