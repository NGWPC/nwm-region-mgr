# Configuration File Builder

Welcome to the Configuration File Builder! The tabs on the left will take you to the builder for each of the specific
config files. Once in the builder, you will be prompted to enter setup information for your regionalization run, or you
can scroll to the bottom to fill in default values.  Once done, hit "download" to save the generated configuration YAML
file to your local system.

Example files and schemas for all configuration fields and subfields are included below.

### config_general.yaml
#### Example File
```yaml
general:
  run_name: 'test' #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Name of the run, used to create output folders and files.
  domain: 'conus' #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Which National Water Model Domain this run uses.
  vpu_list: ['09'] #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------List of vector processing units (VPUs) within the domain or 'all' to process all.
  base_dir: '/root/nwm-region-mgr/data/' #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Path to base directory for input/output files.
  ngen_hydrofabric_file: ['{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '{base_dir}/inputs/hydrofabric/vpu_{vpu_list}.gpkg', {'09': '{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '10': '{base_dir}/inputs/hydrofabric/vpu_10.gpkg'}] #-----Path to NextGen hydrofabric file. Can be: 1) a single file path (Path or str), e.g., 'vpu_01.gpkg' or 2) a dictionary mapping VPU strings to file paths, e.g., {'09': 'vpu_09.gpkg'}.If providing a string with placeholders like {vpu_list}, they will be substituted accordingly and expanded to a dictionary mapping each VPU to its corresponding file. This file must include columns 'divide_id', 'vpuid' and 'geometry'.
  gage_divide_cwt_file: '{base_dir}/inputs/calib_gage_divide_{domain}.parquet' #----------------------------------------------------------------------------------------------------------------------------------------------------------Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'.
  donor_gage_file: '{base_dir}/inputs/gages_nwm4_calib_all.csv' #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'.
  calval_stats_file: ['stat_calval_all_{domain}.csv', 'stat_calval_all_{domain}.parquet'] #-----------------------------------------------------------------------------------------------------------------------------------------------Path to CSV or parquet file with calibration/validation statistics for all calibration gages and formulations, e.g., 'stat_calval_all_conus.parquet', 'stat_calval_all_conus.csv'. Must include columns for 'gage_id', 'formulation', and relevant metrics to be used for formulation and parameter regionalization.
  calib_param_file: ['calib_params_{domain}.csv', 'calib_params_{domain}.parquet'] #------------------------------------------------------------------------------------------------------------------------------------------------------Path to CSV or parquet file containing calibrated parameters for all calibration gages and formulations in the domain. Must include columns for 'gage_id', 'formulation', and calibrated parameters.
  approach_calib_basins: ['regionalization', 'summary_score'] #---------------------------------------------------------------------------------------------------------------------------------------------------------------------------Strategy for assigning formulations to calibrated basins. Valid options are 'regionalization' (assign the formulation chosen for the region) or 'summary_score' (assign based on formulation summary scores for the calibrated basin).
  id_col: #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Dictionary mapping column names for unique identifiers in all applicable files.
    divide: 'divide_id' #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Column name for divide (catchment) ID.
    gage: 'gage_id' #---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Column name for gage (basin) ID.
    huc12: 'huc_12' #---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Column name for HUC12 ID.
    vpu: 'vpuid' #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Column name for VPU ID.
    drainage_area: 'areasqkm' #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Column name for drainage area.
  layer_name: #---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Dictionary mapping layer names for hydrofabric files. Identifies the layer in each hydrofabric file to be used during regionalization.
    huc12: 'WBDSnapshot_National' #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Layer name for HUC12 hydrofabric file.
    ngen: 'divides' #---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Layer name for NextGen hydrofabric file.
  logging: #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Logging configuration for the application.
    level: 'debug' #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Logging level.
    log_to_file: False #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Whether to log to a file. If set to True, logging messages will be written to the specified log file, in addition to the console.
    file: 'logfile.log' #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------Path to the log file. If not provided, logging will be written to console only.
```
#### Schema Reference (general)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| run_name | str | Name of the run, used to create output folders and files. | test | test |
| domain | str = conus \| ak \| hi \| prvi | Which National Water Model Domain this run uses. | conus | conus |
| vpu_list | List[str] \| str | List of vector processing units (VPUs) within the domain or 'all' to process all. | PydanticUndefined | ['09'] |
| base_dir | str | Path to base directory for input/output files. | PydanticUndefined | /root/nwm-region-mgr/data/ |
| ngen_hydrofabric_file | Path \| str \| Dict[str, Path] \| Dict[str, str] | Path to NextGen hydrofabric file. Can be: 1) a single file path (Path or str), e.g., 'vpu_01.gpkg' or 2) a dictionary mapping VPU strings to file paths, e.g., {'09': 'vpu_09.gpkg'}.If providing a string with placeholders like {vpu_list}, they will be substituted accordingly and expanded to a dictionary mapping each VPU to its corresponding file. This file must include columns 'divide_id', 'vpuid' and 'geometry'. | PydanticUndefined | ['{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '{base_dir}/inputs/hydrofabric/vpu_{vpu_list}.gpkg', {'09': '{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '10': '{base_dir}/inputs/hydrofabric/vpu_10.gpkg'}] |
| gage_divide_cwt_file | Path \| str | Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'. | PydanticUndefined | {base_dir}/inputs/calib_gage_divide_{domain}.parquet |
| donor_gage_file | Path \| str | Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'. | PydanticUndefined | {base_dir}/inputs/gages_nwm4_calib_all.csv |
| calval_stats_file | Path \| str | Path to CSV or parquet file with calibration/validation statistics for all calibration gages and formulations, e.g., 'stat_calval_all_conus.parquet', 'stat_calval_all_conus.csv'. Must include columns for 'gage_id', 'formulation', and relevant metrics to be used for formulation and parameter regionalization. | PydanticUndefined | ['stat_calval_all_{domain}.csv', 'stat_calval_all_{domain}.parquet'] |
| calib_param_file | Path \| str | Path to CSV or parquet file containing calibrated parameters for all calibration gages and formulations in the domain. Must include columns for 'gage_id', 'formulation', and calibrated parameters. | PydanticUndefined | ['calib_params_{domain}.csv', 'calib_params_{domain}.parquet'] |
| approach_calib_basins | str = regionalization \| summary_score | Strategy for assigning formulations to calibrated basins. Valid options are 'regionalization' (assign the formulation chosen for the region) or 'summary_score' (assign based on formulation summary scores for the calibrated basin). | PydanticUndefined | ['regionalization', 'summary_score'] |
| id_col | FieldCrosswalk | Dictionary mapping column names for unique identifiers in all applicable files. | PydanticUndefined | {'divide': 'divide_id', 'gage': 'gage_id', 'huc12': 'huc_12', 'vpu': 'vpuid', 'drainage_area': 'areasqkm'} |
| layer_name | LayerCrosswalk | Dictionary mapping layer names for hydrofabric files. Identifies the layer in each hydrofabric file to be used during regionalization. | PydanticUndefined | {'huc12': 'WBDSnapshot_National', 'ngen': 'divides'} |
| logging | LoggingConfig | Logging configuration for the application. | PydanticUndefined | {'level': 'info', 'log_to_file': True, 'file': 'logs/{run_name}.log'} |
#### Schema Reference (id_col)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| divide | str | Column name for divide (catchment) ID. | divide_id | divide_id |
| gage | str | Column name for gage (basin) ID. | gage_id | gage_id |
| huc12 | str | Column name for HUC12 ID. | huc_12 | huc_12 |
| vpu | str | Column name for VPU ID. | vpuid | vpuid |
| drainage_area | str | Column name for drainage area. | areasqkm | areasqkm |
#### Schema Reference (layer_name)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| huc12 | str | Layer name for HUC12 hydrofabric file. | WBDSnapshot_National | WBDSnapshot_National |
| ngen | str | Layer name for NextGen hydrofabric file. | divides | divides |
#### Schema Reference (logging)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| level | str = debug \| info \| warning \| error \| critical | Logging level. | info | debug |
| log_to_file | bool | Whether to log to a file. If set to True, logging messages will be written to the specified log file, in addition to the console. | False | False |
| file | str \| NoneType | Path to the log file. If not provided, logging will be written to console only. | None | logfile.log |
### config_formreg.yaml
#### Example File
```yaml
general: #-----------------------------------------------------------------------------------------------General settings for the formulation regionalization application.
  huc12_hydrofabric_file: 'NationalWBDSnapshot.gdb' #----------------------------------------------------Path to HUC12 hydrofabric file containing HUC12 polygons for spatial discretization.
  divide_huc12_cwt_file: 'cwt_divide_huc12_{domain}.csv' #-----------------------------------------------Path to crosswalk file between HUC12 basins and NextGen catchments, with columns 'divide_id' and 'huc_12'.
  calib_basins_only: False #-----------------------------------------------------------------------------Whether to run formulation selection only for calibrated basins (based on summary score).
  formulation_to_include: ['noah-owp-modular cfe-s t-route', 'noah-owp-modular ueb cfe-x t-route'] #-----List of formulations to consider. If None, all formulations are included.  If 'all', all formulations are included.
  formulation_to_exclude: ['noah-owp-modular cfe-s t-route'] #-------------------------------------------List of formulations to exclude. If None, no formulations are excluded.
  consider_cost: False #---------------------------------------------------------------------------------Whether to consider computational costs of formulations in the regionalization process.
spatial_unit: #------------------------------------------------------------------------------------------Spatial discretization settings for the application.
  huc_level: ['huc2', 'huc4', 'huc6', 'huc8', 'huc10', 'huc12'] #----------------------------------------USGS HUC level used for discretization, e.g., 'huc8'. Accepted formats: 'huc8', 'HUC8', 'huc-8'.
  nmin_calib_basin: 5 #----------------------------------------------------------------------------------Minimum number of calibration basins required per spatial unit to consider it valid.
  basin_fill_method: 'upscaling' #-----------------------------------------------------------------------Method to handle spatial units with too few calibration basins. Options: 'upscaling' (by upscaling to a coarser spatial unit), and 'nearest-neighbor' (by pooling basins from neighboring units).
  best_formulation: #------------------------------------------------------------------------------------Strategy to determine the best formulation for each spatial unit.
    method: 'total_score' #------------------------------------------------------------------------------Method to determine the best formulation, options: 'total_score', 'total_count'.
    type: 'basin' #--------------------------------------------------------------------------------------Type of spatial unit for best formulation, options: 'basin', 'divide'.
    tolerance: 0.05 #------------------------------------------------------------------------------------Score tolerance as a fraction of the best score, must be between 0.0 and 1.0.
summary_score: #-----------------------------------------------------------------------------------------Summary score computation configuration for the application.
  metric_eval_period: #----------------------------------------------------------------------------------Evaluation period of metrics to be used for screening donors.
    col_name: evalPeriod
    value: valid
  metrics: #---------------------------------------------------------------------------------------------Dictionary of metrics used in the summary score, keyed by metric name. Metric names must match columns in the calibration/validation stats file. Weights must sum to 1.0.
    upper: 1 #-------------------------------------------------------------------------------------------Upper bound for scaling and normalization, must be greater than lower bound.
    lower: 0 #-------------------------------------------------------------------------------------------Lower bound for scaling and normalization, must be less than upper bound.
    orientation: 'positive' #----------------------------------------------------------------------------Orientation of the metric, either 'positive' or 'negative'.
    weight: 0.25 #---------------------------------------------------------------------------------------Weight of the metric in the summary score, must be between 0.0 and 1.0. If 0.0, the metric is ignored.
    absolute: False #------------------------------------------------------------------------------------Whether to use the absolute value of the metric for normalization.
formulation_cost: #--------------------------------------------------------------------------------------Computational cost configuration for each formulation.
  file: 'formulation_costs_secs_per_catchment.csv' #-----------------------------------------------------Path to CSV file with formulation costs. If provided, costs will be read from this file.
  costs: #-----------------------------------------------------------------------------------------------Dictionary of formulation costs, keyed by formulation name. If `file` is provided, this is ignored.
    noah-owp-modular ueb cfe-x t-route: 10
output: #------------------------------------------------------------------------------------------------Output configuration for the application.
  save: [True, False] #----------------------------------------------------------------------------------Whether to save output files
  path: ['{base_dir}/outputs/{run_name}/formulations'] #-------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
  stem: ['form_{domain}_vpu{vpu_list}'] #----------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
  stem_suffix: ['_pars'] #-------------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
  format: ['parquet', 'csv', 'yaml'] #-------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
  plots: #-----------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
    histogram: True
    spatial_map: True
    columns_to_plot: ['param1', 'param2']
  plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #--------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
```
#### Schema Reference (general)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| run_name | str | Name of the run, used to create output folders and files. | test | test |
| domain | str = conus \| ak \| hi \| prvi | Which National Water Model Domain this run uses. | conus | conus |
| vpu_list | List[str] \| str | List of vector processing units (VPUs) within the domain or 'all' to process all. | PydanticUndefined | ['09'] |
| base_dir | str | Path to base directory for input/output files. | PydanticUndefined | /root/nwm-region-mgr/data/ |
| ngen_hydrofabric_file | Path \| str \| Dict[str, Path] \| Dict[str, str] | Path to NextGen hydrofabric file. Can be: 1) a single file path (Path or str), e.g., 'vpu_01.gpkg' or 2) a dictionary mapping VPU strings to file paths, e.g., {'09': 'vpu_09.gpkg'}.If providing a string with placeholders like {vpu_list}, they will be substituted accordingly and expanded to a dictionary mapping each VPU to its corresponding file. This file must include columns 'divide_id', 'vpuid' and 'geometry'. | PydanticUndefined | ['{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '{base_dir}/inputs/hydrofabric/vpu_{vpu_list}.gpkg', {'09': '{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '10': '{base_dir}/inputs/hydrofabric/vpu_10.gpkg'}] |
| gage_divide_cwt_file | Path \| str | Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'. | PydanticUndefined | {base_dir}/inputs/calib_gage_divide_{domain}.parquet |
| donor_gage_file | Path \| str | Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'. | PydanticUndefined | {base_dir}/inputs/gages_nwm4_calib_all.csv |
| calval_stats_file | Path \| str | Path to CSV or parquet file with calibration/validation statistics for all calibration gages and formulations, e.g., 'stat_calval_all_conus.parquet', 'stat_calval_all_conus.csv'. Must include columns for 'gage_id', 'formulation', and relevant metrics to be used for formulation and parameter regionalization. | PydanticUndefined | ['stat_calval_all_{domain}.csv', 'stat_calval_all_{domain}.parquet'] |
| calib_param_file | Path \| str | Path to CSV or parquet file containing calibrated parameters for all calibration gages and formulations in the domain. Must include columns for 'gage_id', 'formulation', and calibrated parameters. | PydanticUndefined | ['calib_params_{domain}.csv', 'calib_params_{domain}.parquet'] |
| approach_calib_basins | str = regionalization \| summary_score | Strategy for assigning formulations to calibrated basins. Valid options are 'regionalization' (assign the formulation chosen for the region) or 'summary_score' (assign based on formulation summary scores for the calibrated basin). | PydanticUndefined | ['regionalization', 'summary_score'] |
| id_col | FieldCrosswalk | Dictionary mapping column names for unique identifiers in all applicable files. | PydanticUndefined | {'divide': 'divide_id', 'gage': 'gage_id', 'huc12': 'huc_12', 'vpu': 'vpuid', 'drainage_area': 'areasqkm'} |
| layer_name | LayerCrosswalk | Dictionary mapping layer names for hydrofabric files. Identifies the layer in each hydrofabric file to be used during regionalization. | PydanticUndefined | {'huc12': 'WBDSnapshot_National', 'ngen': 'divides'} |
| logging | LoggingConfig | Logging configuration for the application. | PydanticUndefined | {'level': 'info', 'log_to_file': True, 'file': 'logs/{run_name}.log'} |
| huc12_hydrofabric_file | str \| Path \| NoneType | Path to HUC12 hydrofabric file containing HUC12 polygons for spatial discretization. | None | NationalWBDSnapshot.gdb |
| divide_huc12_cwt_file | str \| NoneType | Path to crosswalk file between HUC12 basins and NextGen catchments, with columns 'divide_id' and 'huc_12'. | None | cwt_divide_huc12_{domain}.csv |
| calib_basins_only | bool | Whether to run formulation selection only for calibrated basins (based on summary score). | False | False |
| formulation_to_include | List[str] \| NoneType | List of formulations to consider. If None, all formulations are included.  If 'all', all formulations are included. | None | ['noah-owp-modular cfe-s t-route', 'noah-owp-modular ueb cfe-x t-route'] |
| formulation_to_exclude | List[str] \| NoneType | List of formulations to exclude. If None, no formulations are excluded. | None | ['noah-owp-modular cfe-s t-route'] |
| consider_cost | bool | Whether to consider computational costs of formulations in the regionalization process. | False | False |
#### Schema Reference (spatial_unit)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| huc_level | str | USGS HUC level used for discretization, e.g., 'huc8'. Accepted formats: 'huc8', 'HUC8', 'huc-8'. | huc8 | ['huc2', 'huc4', 'huc6', 'huc8', 'huc10', 'huc12'] |
| nmin_calib_basin | int | Minimum number of calibration basins required per spatial unit to consider it valid. | 3 | 5 |
| basin_fill_method | str = upscaling \| nearest-neighbor | Method to handle spatial units with too few calibration basins. Options: 'upscaling' (by upscaling to a coarser spatial unit), and 'nearest-neighbor' (by pooling basins from neighboring units). | upscaling | upscaling |
| best_formulation | BestFormulation | Strategy to determine the best formulation for each spatial unit. | PydanticUndefined | {'method': 'total_score', 'type': 'divide', 'tolerance': 0.05} |
#### Schema Reference (best_formulation)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| method | str = total_score \| total_count | Method to determine the best formulation, options: 'total_score', 'total_count'. | PydanticUndefined | total_score |
| type | str = basin \| divide | Type of spatial unit for best formulation, options: 'basin', 'divide'. | PydanticUndefined | basin |
| tolerance | float | Score tolerance as a fraction of the best score, must be between 0.0 and 1.0. | 0.05 | 0.05 |
#### Schema Reference (summary_score)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| metric_eval_period | MetricEvalPeriod \| NoneType | Evaluation period of metrics to be used for screening donors. | None | {'col_name': 'evalPeriod', 'value': 'valid'} |
| metrics | Dict[str, MetricConfig] | Dictionary of metrics used in the summary score, keyed by metric name. Metric names must match columns in the calibration/validation stats file. Weights must sum to 1.0. | PydanticUndefined | {'cor': {'upper': 1, 'lower': -0.5, 'orientation': 'positive', 'weight': 0.25}} |
#### Schema Reference (metric_eval_period)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| col_name | str | Name of the column in the donor stats file that contains the evaluation period. | PydanticUndefined | evalPeriod |
| value | str | Value of the evaluation period to filter the donor stats file. | PydanticUndefined | full |
#### Schema Reference (metric)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| upper | float \| NoneType | Upper bound for scaling and normalization, must be greater than lower bound. | None | 1 |
| lower | float \| NoneType | Lower bound for scaling and normalization, must be less than upper bound. | None | 0 |
| orientation | str = positive \| negative | Orientation of the metric, either 'positive' or 'negative'. | positive | positive |
| weight | float | Weight of the metric in the summary score, must be between 0.0 and 1.0. If 0.0, the metric is ignored. | 0.0 | 0.25 |
| absolute | bool | Whether to use the absolute value of the metric for normalization. | False | False |
#### Schema Reference (formulation_cost)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| file | str \| NoneType | Path to CSV file with formulation costs. If provided, costs will be read from this file. | None | formulation_costs_secs_per_catchment.csv |
| costs | Dict[str, float] \| NoneType | Dictionary of formulation costs, keyed by formulation name. If `file` is provided, this is ignored. | None | {'noah-owp-modular ueb cfe-x t-route': 10} |
### config_parreg.yaml
#### Example File
```yaml
general:
  general: #--------------------------------------------------------------General configuration settings specific to parameter regionalization.
    n_procs: '-1' #-------------------------------------------------------Number of processors to use for parallel processing. Set to -1 to use all available processors.
    attr_dataset_list: ['hlr'] #------------------------------------------List of attribute dataset names to use. Valid options include 'ngen', 'hlr'.
    algorithm_list: ['gower', 'kmeans'] #---------------------------------Algorithms to use. Valid options ('gower', 'urf', 'kmeans', 'kmedoids', 'hdbscan', 'birch').
    manual_pairings_file: 'pairs_kmeans_conus_vpu09.parquet' #------------Path to the manual pairings file. If provided, this file will be used to specify manual donor-receiver pairings.
  donor: #----------------------------------------------------------------Configuration for donor selection.
    buffer_km: 100.0 #----------------------------------------------------Size of buffer (in km) around current VPU to identify qualified donors.
    metric_eval_period: #-------------------------------------------------Evaluation period of metrics to be used for screening donors.
      col_name: eval_period
      value: full
    metric_threshold: #---------------------------------------------------Dictionary of metric thresholds to be used for screening donors.
      min: 0.4 #----------------------------------------------------------Minimum threshold for the metric. If None, no minimum threshold is applied.
      max: 0.9 #----------------------------------------------------------Maximum threshold for the metric. If None, no maximum threshold is applied.
      absolute: False #---------------------------------------------------If True, apply the absolute value of the metric before applying the thresholds.
  attr_datasets: #--------------------------------------------------------Configuration for attribute datasets that can be used in the regionalization process.
    attr_list: ['attr1'] #------------------------------------------------List of attributes to use from this dataset.
    attr_select_file: ['attr_selection_ngen.csv'] #-----------------------Path to file where attribute list may be found.
    attr_data_file: ['attr_ngen_{domain}.parquet'] #----------------------Path to file where attribute data may be found.
    base_attr_list: ['elevation', 'slope', 'aspect'] #--------------------List of 'base' attributes to use from this dataset.
  snow_cover: #-----------------------------------------------------------Configuration for snow cover data.
    consider_snowness: False #--------------------------------------------Whether to consider snow cover data in the regionalization process.
    snow_cover_file: 'vpu{vpu_list}_snow_frac.parquet' #------------------Path to the snow cover data file, or a dictionary with VPU as keys and file paths as values.
    column: 'snow_pc_hydroatlas' #----------------------------------------Column name in the snow cover data file that contains the snow cover percentage.
    threshold: '20' #-----------------------------------------------------Threshold value for snow cover percentage to determine if a catchment is considered snow-driven.
  output: #---------------------------------------------------------------Output configuration settings.
    save: [True, False] #-------------------------------------------------Whether to save output files
    path: ['{base_dir}/outputs/{run_name}/formulations'] #----------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
    stem: ['form_{domain}_vpu{vpu_list}'] #-------------------------------File stem for output files, used to create unique file names based on the path.
    stem_suffix: ['_pars'] #----------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
    format: ['parquet', 'csv', 'yaml'] #----------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
    plots: #--------------------------------------------------------------Configuration for output plots, if applicable.
      histogram: True
      spatial_map: True
      columns_to_plot: ['param1', 'param2']
    plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #-----Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
  algorithms: #-----------------------------------------------------------Algorithm configuration class.  See specific algorithms for additional arguments.
    algo_general: #-------------------------------------------------------Base config for all algorithms.
      min_snow_frac: PydanticUndefined
      max_spa_dist: PydanticUndefined
      max_attr_diff: PydanticUndefined
      n_donor_max: PydanticUndefined
      min_var_pca: PydanticUndefined
    gower: None
    urf: None
    kmeans: None
    kmedoids: None
    hdbscan: None
    birch: None
```
#### Schema Reference (general)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| run_name | str | Name of the run, used to create output folders and files. | test | test |
| domain | str = conus \| ak \| hi \| prvi | Which National Water Model Domain this run uses. | conus | conus |
| vpu_list | List[str] \| str | List of vector processing units (VPUs) within the domain or 'all' to process all. | PydanticUndefined | ['09'] |
| base_dir | str | Path to base directory for input/output files. | PydanticUndefined | /root/nwm-region-mgr/data/ |
| ngen_hydrofabric_file | Path \| str \| Dict[str, Path] \| Dict[str, str] | Path to NextGen hydrofabric file. Can be: 1) a single file path (Path or str), e.g., 'vpu_01.gpkg' or 2) a dictionary mapping VPU strings to file paths, e.g., {'09': 'vpu_09.gpkg'}.If providing a string with placeholders like {vpu_list}, they will be substituted accordingly and expanded to a dictionary mapping each VPU to its corresponding file. This file must include columns 'divide_id', 'vpuid' and 'geometry'. | PydanticUndefined | ['{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '{base_dir}/inputs/hydrofabric/vpu_{vpu_list}.gpkg', {'09': '{base_dir}/inputs/hydrofabric/vpu_09.gpkg', '10': '{base_dir}/inputs/hydrofabric/vpu_10.gpkg'}] |
| gage_divide_cwt_file | Path \| str | Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'. | PydanticUndefined | {base_dir}/inputs/calib_gage_divide_{domain}.parquet |
| donor_gage_file | Path \| str | Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'. | PydanticUndefined | {base_dir}/inputs/gages_nwm4_calib_all.csv |
| calval_stats_file | Path \| str | Path to CSV or parquet file with calibration/validation statistics for all calibration gages and formulations, e.g., 'stat_calval_all_conus.parquet', 'stat_calval_all_conus.csv'. Must include columns for 'gage_id', 'formulation', and relevant metrics to be used for formulation and parameter regionalization. | PydanticUndefined | ['stat_calval_all_{domain}.csv', 'stat_calval_all_{domain}.parquet'] |
| calib_param_file | Path \| str | Path to CSV or parquet file containing calibrated parameters for all calibration gages and formulations in the domain. Must include columns for 'gage_id', 'formulation', and calibrated parameters. | PydanticUndefined | ['calib_params_{domain}.csv', 'calib_params_{domain}.parquet'] |
| approach_calib_basins | str = regionalization \| summary_score | Strategy for assigning formulations to calibrated basins. Valid options are 'regionalization' (assign the formulation chosen for the region) or 'summary_score' (assign based on formulation summary scores for the calibrated basin). | PydanticUndefined | ['regionalization', 'summary_score'] |
| id_col | FieldCrosswalk | Dictionary mapping column names for unique identifiers in all applicable files. | PydanticUndefined | {'divide': 'divide_id', 'gage': 'gage_id', 'huc12': 'huc_12', 'vpu': 'vpuid', 'drainage_area': 'areasqkm'} |
| layer_name | LayerCrosswalk | Dictionary mapping layer names for hydrofabric files. Identifies the layer in each hydrofabric file to be used during regionalization. | PydanticUndefined | {'huc12': 'WBDSnapshot_National', 'ngen': 'divides'} |
| logging | LoggingConfig | Logging configuration for the application. | PydanticUndefined | {'level': 'info', 'log_to_file': True, 'file': 'logs/{run_name}.log'} |
| n_procs | int | Number of processors to use for parallel processing. Set to -1 to use all available processors. | 1 | -1 |
| attr_dataset_list | List[str = ngen \| hlr] | List of attribute dataset names to use. Valid options include 'ngen', 'hlr'. | [] | ['hlr'] |
| algorithm_list | List[str = gower \| urf \| kmeans \| kmedoids \| hdbscan \| birch] | Algorithms to use. Valid options ('gower', 'urf', 'kmeans', 'kmedoids', 'hdbscan', 'birch'). | [] | ['gower', 'kmeans'] |
| manual_pairings_file | Path \| str \| NoneType | Path to the manual pairings file. If provided, this file will be used to specify manual donor-receiver pairings. | None | pairs_kmeans_conus_vpu09.parquet |
#### Schema Reference (donor)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| buffer_km | float \| NoneType | Size of buffer (in km) around current VPU to identify qualified donors. | 0.0 | 100.0 |
| metric_eval_period | MetricEvalPeriod \| NoneType | Evaluation period of metrics to be used for screening donors. | None | {'col_name': 'eval_period', 'value': 'full'} |
| metric_threshold | Dict[str, MetricThreshold] | Dictionary of metric thresholds to be used for screening donors. | None | {'cor': {'min': 0.4}} |
#### Schema Reference (metric_eval_period)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| col_name | str | Name of the column in the donor stats file that contains the evaluation period. | PydanticUndefined | evalPeriod |
| value | str | Value of the evaluation period to filter the donor stats file. | PydanticUndefined | full |
#### Schema Reference (metric_threshold)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| min | float \| NoneType | Minimum threshold for the metric. If None, no minimum threshold is applied. | None | 0.4 |
| max | float \| NoneType | Maximum threshold for the metric. If None, no maximum threshold is applied. | None | 0.9 |
| absolute | bool \| NoneType | If True, apply the absolute value of the metric before applying the thresholds. | False | False |
#### Schema Reference (attr_datasets_config)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| attr_list | list \| NoneType | List of attributes to use from this dataset. | None | ['attr1'] |
| attr_select_file | Path \| str \| NoneType | Path to file where attribute list may be found. | None | ['attr_selection_ngen.csv'] |
| attr_data_file | Path \| str \| NoneType | Path to file where attribute data may be found. | None | ['attr_ngen_{domain}.parquet'] |
| base_attr_list | list \| NoneType | List of 'base' attributes to use from this dataset. | None | ['elevation', 'slope', 'aspect'] |
#### Schema Reference (snow_cover)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| consider_snowness | bool \| NoneType | Whether to consider snow cover data in the regionalization process. | False | False |
| snow_cover_file | Path \| str \| Dict[str, Path \| str] \| NoneType | Path to the snow cover data file, or a dictionary with VPU as keys and file paths as values. | None | vpu{vpu_list}_snow_frac.parquet |
| column | str \| NoneType | Column name in the snow cover data file that contains the snow cover percentage. | None | snow_pc_hydroatlas |
| threshold | float \| NoneType | Threshold value for snow cover percentage to determine if a catchment is considered snow-driven. | None | 20 |
#### Schema Reference (algorithms)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| algo_general | AlgoGeneral | Base config for all algorithms. | PydanticUndefined | PydanticUndefined |
| gower | Gower \| NoneType | No description provided | None | None |
| urf | URF \| NoneType | No description provided | None | None |
| kmeans | KMeans \| NoneType | No description provided | None | None |
| kmedoids | KMedoids \| NoneType | No description provided | None | None |
| hdbscan | HDBSCAN \| NoneType | No description provided | None | None |
| birch | Birch \| NoneType | No description provided | None | None |
#### Schema Reference (algorithm)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| min_snow_frac | float | No description provided | PydanticUndefined | PydanticUndefined |
| max_spa_dist | float | No description provided | PydanticUndefined | PydanticUndefined |
| max_attr_diff | Dict[str, float] | No description provided | PydanticUndefined | PydanticUndefined |
| n_donor_max | int | No description provided | PydanticUndefined | PydanticUndefined |
| min_var_pca | float | No description provided | PydanticUndefined | PydanticUndefined |
#### Schema Reference (output)
| Field | Type(s) | Description | Default | Example(s) |
| --- | --- | --- | --- | --- |
| save | bool | Whether to save output files | True | [True, False] |
| path | Path \| str | Path to save output file or files. If a directory, the 'stem' and 'format' must be specified. | PydanticUndefined | ['{base_dir}/outputs/{run_name}/formulations'] |
| stem | str \| Dict[str, str] \| NoneType | File stem for output files, used to create unique file names based on the path. | None | ['form_{domain}_vpu{vpu_list}'] |
| stem_suffix | str \| NoneType | Suffix for the file stem, used to create unique file names based on the path for specific needs. | None | ['_pars'] |
| format | str \| NoneType | File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file. | None | ['parquet', 'csv', 'yaml'] |
| plots | Dict[str, Any] \| NoneType | Configuration for output plots, if applicable. | None | {'histogram': True, 'spatial_map': True, 'columns_to_plot': ['param1', 'param2']} |
| plot_path | str \| NoneType | Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path. | None | ['{base_dir}/outputs/{run_name}/formulations/plots'] |