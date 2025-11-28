# User Guide

The steps below walk through package installation and workflow configuration.

## Installation

Installing nwm_region_mgr requires

 - Python 3.11
 - Python venv (typically included with Python)
 - git

Since nwm_region_mgr is not currently on PyPI, it must be installed from source. To download this repository, run

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

You will then be able to install nwm_region_mgr. There are a few download variants that users may be interested in.

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

Examples are available in `configs` or they may be developed with the [Config Builder](config_builder/index.md) on this website.

## Executing nwm_region_mgr

To run the regionalization script, you can use the following command.

```bash
python regionalization.py configs
```



