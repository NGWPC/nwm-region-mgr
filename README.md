# Formulation and Parameter Regionalization for the NextGen Framework
[![License: BSD 2-Clause](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)](https://opensource.org/license/bsd-2-clause)
[![Release](https://img.shields.io/github/v/release/ngwpc/nwm-region-mgr)](https://github.com/NGWPC/nwm-region-mgr)
![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-orange.svg)
![Linter: Ruff](https://img.shields.io/badge/linter-ruff-orange)

<img src="docs/source/_images/overview.png" alt="overview" width="600"/>


`nwm_region_mgr` is a Python package for identifying optimal model formulations and parameter values in ungauged catchments. It leverages calibration data from gauged catchments and catchment attributes to improve hydrologic modeling and forecasting skill across regions, playing a key role in the NextGen and NWM ecosystem.


## Key Features

- **Formulation Regionalization** – Ranks NextGen model formulations for ungauged catchments based on performance at gauged sites in a region.
- **Parameter Regionalization** – Estimates parameter values by intelligently transferring calibrations across catchments based on similarity.
- **Clustering Methods** – Groups catchments with shared hydrologic characteristics using multiple clustering approaches.
- **Distance methods** – Identify donors using distance metrics that characterize catchment similarity/dissimilarity.
- **Diagnostic Plots** – Generates diagnostic plots and maps that explain formulation and parameter choices.
- **VPU-Based Regionalization** – Runs regionalization independently for individual VPUs and supports assembling results across multiple VPUs for domain-wide applications.
- **Customizable Configurations** – Full control of workflows via human-readable config files.

## User Guide

For detailed instructions on setting up and running the regionalization workflow, see the [User Guide](https://NGWPC.github.io/nwm-region-mgr/user_guide.html).