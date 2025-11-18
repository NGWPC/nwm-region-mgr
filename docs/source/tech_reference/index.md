# Technical Reference

The following pages contain detailed descriptions of process workflow and algorithms.

:::{toctree}
:maxdepth: 1
:caption: Subsections

Input Data<input_data>
Formulation Regionalization<formreg>
Parameter Regionalization<parreg>
Outputs<output_data>
:::

## Output Structure

```bash
.
├── attr_data_final                     # Catchment-level attribute datasets used for regionalization
│   ├── attr_conus_vpu01.parquet        # Final attribute table for CONUS VPU 01
│   └── plots                           # Diagnostic plots summarizing attribute distributions
│       ├── bar_attr_missing_count_conus_vpu01.png    # Bar chart of missing attribute counts
│       ├── hist_attr_conus_vpu01.png                 # Histogram of attribute distributions
│       └── map_attr_conus_vpu01.png                  # Spatial visualization of attribute values
├── config_formreg_final.yaml           # Log of configuration settings used for formulation regionalization
├── config_parreg_final.yaml            # Log of configuration settings used for parameter regionalization
├── formulations                        # Selected NextGen formulations (combinations of hydrologic models)
│   ├── form_conus_vpu01.parquet        # Selected formulations for CONUS VPU 01 divides
│   ├── form_conus_vpu01_slim.parquet   # Slimmed version containing only essential formulation fields
│   ├── form_conus_vpu02.parquet        # Selected formulations for CONUS VPU 02 divides
│   ├── form_conus_vpu02_slim.parquet   # Slimmed version containing only essential formulation fields
│   └── plots                           # Visual diagnostics of formulation selection
│       ├── hist_form_conus_vpu01.png                  # Histogram of formulation frequencies (VPU 01)
│       ├── hist_form_conus_vpu02.png                  # Histogram of formulation frequencies (VPU 02)
│       ├── map_form_conus_vpu01.png                   # Spatial distribution of selected formulations (VPU 01)
│       └── map_form_conus_vpu02.png                   # Spatial distribution of selected formulations (VPU 02)
├── pairs                               # Donor–receiver catchment pairings based on chosen algorithms
│   ├── pairs_gower_conus_vpu01.parquet # Table of attribute-based similarity scores (VPU 01)
│   └── plots                           # Diagnostics for donor–receiver pairing analysis
│       ├── hist_pairs_gower_conus_vpu01.png            # Histogram of Gower distances between pairs
│       ├── map_donors_conus_vpu01.png                  # Map of donor catchments (VPU 01)
│       └── map_pairs_gower_conus_vpu01.png             # Map showing donor–receiver pair linkages
├── spatial_distance                    # Purely geographic distances between donor and receiver catchments
│   └── donor_receiver_dist_conus_vpu01.parquet          # Centroid-to-centroid distances (VPU 01)
└── summary_score                       # Performance metrics of selected formulations
    ├── plots                           # Visual summaries of formulation performance
    │   ├── hist_score_conus_vpu01.png                   # Histogram of formulation scores (VPU 01)
    │   ├── hist_score_conus_vpu02.png                   # Histogram of formulation scores (VPU 02)
    │   ├── map_score_conus_vpu01.png                    # Spatial map of formulation scores (VPU 01)
    │   └── map_score_conus_vpu02.png                    # Spatial map of formulation scores (VPU 02)
    ├── score_conus_all_gages.parquet   # Combined formulation performance metrics across all gages
    ├── score_conus_vpu01.parquet       # Performance metrics by formulation (VPU 01)
    └── score_conus_vpu02.parquet       # Performance metrics by formulation (VPU 02)

```

