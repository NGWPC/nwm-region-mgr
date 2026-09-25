## Input Directory Structure

The input directory contains three subdirectories: `region`, `ngen`, and `eval`, which store the input files used by the regionalization, NGEN simulation, and evaluation steps, respectively. The directory tree below lists up to 10 files per directory; additional files are omitted from the listing.

```bash
inputs
├── eval      # inputs for the evaluation step including the crosswalk between evaluation sites and NextGen catchments
│   ├── usgs_ngen_crosswalk_ak.parquet
│   ├── usgs_ngen_crosswalk_conus.parquet
│   ├── usgs_ngen_crosswalk_hi.parquet
│   └── usgs_ngen_crosswalk_prvi.parquet
├── ngen      # inputs for the ngen simulation step
│   └── esmf_mesh
│   │   └── NWM
│   │   │   └── domain      # geogrid for different NWM domains required by ngen-forcing
│   │   │   │   ├── GEOGRID_LDASOUT_Spatial_Metadata_AK.nc
│   │   │   │   ├── GEOGRID_LDASOUT_Spatial_Metadata_CONUS.nc
│   │   │   │   ├── GEOGRID_LDASOUT_Spatial_Metadata_CONUS_debug_gauge_01123000.nc
│   │   │   │   ├── GEOGRID_LDASOUT_Spatial_Metadata_HI.nc
│   │   │   │   ├── GEOGRID_LDASOUT_Spatial_Metadata_PRVI.nc
│   │   │   │   ├── README.txt
│   │   │   │   ├── geo_em_Alaska.nc
│   │   │   │   ├── geo_em_CONUS.nc
│   │   │   │   ├── geo_em_CONUS_debug_gauge_01123000.nc
│   │   │   │   ├── geo_em_Hawaii.nc
│   │   │   │   └── ... (1 more files omitted)
└── region      # inputs for the regionalization step
│   ├── NHDPlusV21      # NHDPlusV21 hydrofabric data required by formulation regionalization
│   │   ├── NHDPlusNationalData
│   │   │   └── NationalWBDSnapshot.gdb
│   │   │   │   ├── a00000001.TablesByName.atx
│   │   │   │   ├── a00000001.freelist
│   │   │   │   ├── a00000001.gdbindexes
│   │   │   │   ├── a00000001.gdbtable
│   │   │   │   ├── a00000001.gdbtablx
│   │   │   │   ├── a00000002.freelist
│   │   │   │   ├── a00000002.gdbtable
│   │   │   │   ├── a00000002.gdbtablx
│   │   │   │   ├── a00000003.freelist
│   │   │   │   ├── a00000003.gdbindexes
│   │   │   │   └── ... (43 more files omitted)
│   │   ├── NHD_H_Alaska_State_GPKG.gpkg
│   │   └── README
│   ├── attr_config      # attribute selection for parameter regionalization
│   │   ├── attr_selection_hlr.csv
│   │   ├── attr_selection_hydroatlas.csv
│   │   ├── attr_selection_ngen.csv
│   │   └── attr_selection_streamcat.csv
│   ├── attr_datasets      # attribute datasets for parameter regionalization
│   │   ├── hlr
│   │   │   ├── attr_hlr_ak.parquet
│   │   │   ├── attr_hlr_conus.parquet
│   │   │   └── attr_hlr_hi.parquet
│   │   ├── hydroatlas
│   │   │   ├── attr_hydroatlas_ak.parquet
│   │   │   ├── attr_hydroatlas_conus.parquet
│   │   │   └── attr_hydroatlas_prvi.parquet
│   │   ├── ngen
│   │   │   ├── attr_ngen_ak.parquet
│   │   │   ├── attr_ngen_conus.parquet
│   │   │   ├── attr_ngen_hi.parquet
│   │   │   └── attr_ngen_prvi.parquet
│   │   └── streamcat
│   │   │   └── attr_streamcat_conus.parquet
│   ├── calval_stats      # pseudo calibration and validation statistics
│   │   ├── stat_calval_all_ak.parquet
│   │   ├── stat_calval_all_conus.parquet
│   │   ├── stat_calval_all_hi.parquet
│   │   └── stat_calval_all_prvi.parquet
│   ├── cwt_divide_gage      # crosswalk between NextGen catchments and calibration gages
│   │   ├── calib_gage_divide_ak.parquet
│   │   ├── calib_gage_divide_conus.parquet
│   │   ├── calib_gage_divide_hi.parquet
│   │   └── calib_gage_divide_prvi.parquet
│   ├── cwt_divide_huc12      # crosswalk between NextGen catchments and HUC12 watersheds
│   │   ├── cwt_huc12_divide_ak.csv
│   │   ├── cwt_huc12_divide_conus.csv
│   │   ├── cwt_huc12_divide_hi.csv
│   │   ├── cwt_huc12_divide_prvi.csv
│   │   ├── unmatched_catchments_ak.png
│   │   └── unmatched_catchments_conus.png
│   ├── hydrofabric      # hydrofabric data for each VPU
│   │   └── gpkg_vpu
│   │   │   ├── vpu_01.gpkg
│   │   │   ├── vpu_02.gpkg
│   │   │   ├── vpu_03N.gpkg
│   │   │   ├── vpu_03S.gpkg
│   │   │   ├── vpu_03W.gpkg
│   │   │   ├── vpu_04.gpkg
│   │   │   ├── vpu_05.gpkg
│   │   │   ├── vpu_06.gpkg
│   │   │   ├── vpu_07.gpkg
│   │   │   ├── vpu_08.gpkg
│   │   │   └── ... (14 more files omitted)
│   ├── manual_pairs      # sample manual pairs to be applied on top of the automatically generated pairs
│   │   ├── manual_pairs_vpu01_nhf.csv
│   │   ├── manual_pairs_vpu03S_nhf.csv
│   │   ├── manual_pairs_vpu19_nhf.csv
│   │   ├── manual_pairs_vpu20_nhf.csv
│   │   └── manual_pairs_vpu21_nhf.csv
│   ├── pseudo_calib_params      # pseudo calibration parameters
│   │   ├── sampled_params_ak.csv
│   │   ├── sampled_params_conus.csv
│   │   ├── sampled_params_hi.csv
│   │   └── sampled_params_prvi.csv
│   ├── formulation_costs_secs_per_catchment.csv
│   ├── gages_nwm4_calib_all.csv
│   └── stats_calib_valid_nwmv3.csv
```
