# Configuration File Builder

Welcome to the Configuration File Builder! The tabs on the left (currently under development) will take you to the builder for each of the specific config files. Once in the builder, you will be prompted to enter setup information for your regionalization run, or you can scroll to the bottom to fill in default values. Once done, hit 'download' to save the generated configuration YAML file to your local system.

Example files and schemas for all configuration fields and subfields are included below.
## Schema Reference and Sample YAML Config Files

  - [General configurations (shared by formulation & parameter regionalizations)](#general-configurations-shared-by-formulation--parameter-regionalizations)
    - [Example File (config_general.yaml)](#example-file-config_generalyaml)
    - [Schema Reference (config_general - general)](#schema-reference-config_general---general)
    - [Schema Reference (config_general - id_col)](#schema-reference-config_general---id_col)
    - [Schema Reference (config_general - layer_name)](#schema-reference-config_general---layer_name)
    - [Schema Reference (config_general - logging)](#schema-reference-config_general---logging)
  - [Specific configurations for formulation regionalization (formreg)](#specific-configurations-for-formulation-regionalization-formreg)
    - [Example File (config_formreg.yaml)](#example-file-config_formregyaml)
    - [Schema Reference (config_formreg - general)](#schema-reference-config_formreg---general)
    - [Schema Reference (config_formreg - spatial_unit)](#schema-reference-config_formreg---spatial_unit)
    - [Schema Reference (config_formreg - best_formulation)](#schema-reference-config_formreg---best_formulation)
    - [Schema Reference (config_formreg - summary_score)](#schema-reference-config_formreg---summary_score)
    - [Schema Reference (config_formreg - metric_eval_period)](#schema-reference-config_formreg---metric_eval_period)
    - [Schema Reference (config_formreg - metrics)](#schema-reference-config_formreg---metrics)
    - [Schema Reference (config_formreg - formulation_cost)](#schema-reference-config_formreg---formulation_cost)
    - [Schema Reference (config_formreg - output)](#schema-reference-config_formreg---output)
    - [Schema Reference (config_formreg - BaseOutputConfig)](#schema-reference-config_formreg---baseoutputconfig)
  - [Specific configurations for parameter regionalization (parreg)](#specific-configurations-for-parameter-regionalization-parreg)
    - [Example File (config_parreg.yaml)](#example-file-config_parregyaml)
    - [Schema Reference (config_parreg - general)](#schema-reference-config_parreg---general)
    - [Schema Reference (config_parreg - donor)](#schema-reference-config_parreg---donor)
    - [Schema Reference (config_parreg - metric_eval_period)](#schema-reference-config_parreg---metric_eval_period)
    - [Schema Reference (config_parreg - metric_threshold)](#schema-reference-config_parreg---metric_threshold)
    - [Schema Reference (config_parreg - attr_datasets_config)](#schema-reference-config_parreg---attr_datasets_config)
    - [Schema Reference (config_parreg - attr_datasets)](#schema-reference-config_parreg---attr_datasets)
    - [Schema Reference (config_parreg - snow_cover)](#schema-reference-config_parreg---snow_cover)
    - [Schema Reference (config_parreg - algorithms)](#schema-reference-config_parreg---algorithms)
    - [Schema Reference (config_parreg - algo_general)](#schema-reference-config_parreg---algo_general)
    - [Schema Reference (config_parreg - gower)](#schema-reference-config_parreg---gower)
    - [Schema Reference (config_parreg - kmeans)](#schema-reference-config_parreg---kmeans)
    - [Schema Reference (config_parreg - kmedoids)](#schema-reference-config_parreg---kmedoids)
    - [Schema Reference (config_parreg - birch)](#schema-reference-config_parreg---birch)
    - [Schema Reference (config_parreg - hdbscan)](#schema-reference-config_parreg---hdbscan)
    - [Schema Reference (config_parreg - output)](#schema-reference-config_parreg---output)
    - [Schema Reference (config_parreg - BaseOutputConfig)](#schema-reference-config_parreg---baseoutputconfig)

### General configurations (shared by formulation & parameter regionalizations)

#### Example File (config_general.yaml)
```yaml
general:
  run_name: 'test' #----------------------------------------------------------------------------Name of the run, used to create output folders and files.
  domain: 'conus' #-----------------------------------------------------------------------------Which National Water Model Domain this run uses.
  vpu_list: ['09'] #----------------------------------------------------------------------------List of vector processing units (VPUs) within the domain or 'all' to process all.
  base_dir: '/root/nwm-region-mgr/data/' #------------------------------------------------------Path to base directory for input/output files.
  ngen_hydrofabric_file: '{base_dir}/inputs/hydrofabric/vpu_09.gpkg' #--------------------------Path to NextGen hydrofabric file. Can be: 1) a single file path (Path or str), e.g., 'vpu_01.gpkg' or 2) a dictionary mapping VPU strings to file paths, e.g., {'09': 'vpu_09.gpkg'}.If providing a string with placeholders like {vpu_list}, they will be substituted accordingly and expanded to a dictionary mapping each VPU to its corresponding file. This file must include columns 'divide_id', 'vpuid' and 'geometry'.
  gage_divide_cwt_file: '{base_dir}/inputs/calib_gage_divide_{domain}.parquet' #----------------Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'.
  donor_gage_file: '{base_dir}/inputs/gages_nwm4_calib_all.csv' #-------------------------------Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'.
  calval_stats_file: ['stat_calval_all_{domain}.csv', 'stat_calval_all_{domain}.parquet'] #-----Path to CSV or parquet file with calibration/validation statistics for all calibration gages and formulations, e.g., 'stat_calval_all_conus.parquet', 'stat_calval_all_conus.csv'. Must include columns for 'gage_id', 'formulation', and relevant metrics to be used for formulation and parameter regionalization.
  calib_param_file: ['calib_params_{domain}.csv', 'calib_params_{domain}.parquet'] #------------Path to CSV or parquet file containing calibrated parameters for all calibration gages and formulations in the domain. Must include columns for 'gage_id', 'formulation', and calibrated parameters.
  approach_calib_basins: ['regionalization', 'summary_score'] #---------------------------------Strategy for assigning formulations to calibrated basins. Valid options are 'regionalization' (assign the formulation chosen for the region) or 'summary_score' (assign based on formulation summary scores for the calibrated basin).
  id_col: #-------------------------------------------------------------------------------------Dictionary mapping column names for unique identifiers in all applicable files.
    divide: 'divide_id' #-----------------------------------------------------------------------Column name for divide (catchment) ID.
    gage: 'gage_id' #---------------------------------------------------------------------------Column name for gage (basin) ID.
    huc12: 'huc_12' #---------------------------------------------------------------------------Column name for HUC12 ID.
    vpu: 'vpuid' #------------------------------------------------------------------------------Column name for VPU ID.
    drainage_area: 'areasqkm' #-----------------------------------------------------------------Column name for drainage area.
  layer_name: #---------------------------------------------------------------------------------Dictionary mapping layer names for hydrofabric files. Identifies the layer in each hydrofabric file to be used during regionalization.
    huc12: 'WBDSnapshot_National' #-------------------------------------------------------------Layer name for HUC12 hydrofabric file.
    ngen: 'divides' #---------------------------------------------------------------------------Layer name for NextGen hydrofabric file.
  logging: #------------------------------------------------------------------------------------Logging configuration for the application.
    level: 'info' #-----------------------------------------------------------------------------Logging level.
    log_to_file: True #-------------------------------------------------------------------------Whether to log to a file. If set to True, logging messages will be written to the specified log file, in addition to the console.
    file: 'logs/{run_name}.log' #---------------------------------------------------------------Path to the log file. If not provided, logging will be written to console only.
```
#### Schema Reference (config_general - general)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| run_name | str | test | test | Name of the run, used to create output folders and files. |
| domain | str = conus \| ak \| hi \| prvi | conus | conus | Which National Water Model Domain this run uses. |
| vpu_list | List[str] \| str | PydanticUndefined | ['09'] | List of vector processing units (VPUs) within the domain or 'all' to process all. |
| base_dir | str | PydanticUndefined | /root/nwm-region-mgr/data/ | Path to base directory for input/output files. |
| ngen_hydrofabric_file | Path \| str \| Dict[str, Path] \| Dict[str, str] | PydanticUndefined | {base_dir}/inputs/hydrofabric/vpu_09.gpkg | Path to NextGen hydrofabric file. Can be: 1) a single file path (Path or str), e.g., 'vpu_01.gpkg' or 2) a dictionary mapping VPU strings to file paths, e.g., {'09': 'vpu_09.gpkg'}.If providing a string with placeholders like {vpu_list}, they will be substituted accordingly and expanded to a dictionary mapping each VPU to its corresponding file. This file must include columns 'divide_id', 'vpuid' and 'geometry'. |
| gage_divide_cwt_file | Path \| str | PydanticUndefined | {base_dir}/inputs/calib_gage_divide_{domain}.parquet | Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'. |
| donor_gage_file | Path \| str | PydanticUndefined | {base_dir}/inputs/gages_nwm4_calib_all.csv | Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'. |
| calval_stats_file | Path \| str | PydanticUndefined | ['stat_calval_all_{domain}.csv', 'stat_calval_all_{domain}.parquet'] | Path to CSV or parquet file with calibration/validation statistics for all calibration gages and formulations, e.g., 'stat_calval_all_conus.parquet', 'stat_calval_all_conus.csv'. Must include columns for 'gage_id', 'formulation', and relevant metrics to be used for formulation and parameter regionalization. |
| calib_param_file | Path \| str | PydanticUndefined | ['calib_params_{domain}.csv', 'calib_params_{domain}.parquet'] | Path to CSV or parquet file containing calibrated parameters for all calibration gages and formulations in the domain. Must include columns for 'gage_id', 'formulation', and calibrated parameters. |
| approach_calib_basins | str = regionalization \| summary_score | PydanticUndefined | ['regionalization', 'summary_score'] | Strategy for assigning formulations to calibrated basins. Valid options are 'regionalization' (assign the formulation chosen for the region) or 'summary_score' (assign based on formulation summary scores for the calibrated basin). |
| id_col | FieldCrosswalk | divide='divide_id' gage='gage_id' huc12='huc_12' vpu='vpuid' drainage_area='areasqkm' | {'divide': 'divide_id', 'gage': 'gage_id', 'huc12': 'huc_12', 'vpu': 'vpuid', 'drainage_area': 'areasqkm'} | Dictionary mapping column names for unique identifiers in all applicable files. |
| layer_name | LayerCrosswalk | huc12='WBDSnapshot_National' ngen='divides' | {'huc12': 'WBDSnapshot_National', 'ngen': 'divides'} | Dictionary mapping layer names for hydrofabric files. Identifies the layer in each hydrofabric file to be used during regionalization. |
| logging | LoggingConfig | level='info' log_to_file=False file=None | {'level': 'info', 'log_to_file': True, 'file': 'logs/{run_name}.log'} | Logging configuration for the application. |
#### Schema Reference (config_general - id_col)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| divide | str | divide_id | divide_id | Column name for divide (catchment) ID. |
| gage | str | gage_id | gage_id | Column name for gage (basin) ID. |
| huc12 | str | huc_12 | huc_12 | Column name for HUC12 ID. |
| vpu | str | vpuid | vpuid | Column name for VPU ID. |
| drainage_area | str | areasqkm | areasqkm | Column name for drainage area. |
#### Schema Reference (config_general - layer_name)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| huc12 | str | WBDSnapshot_National | WBDSnapshot_National | Layer name for HUC12 hydrofabric file. |
| ngen | str | divides | divides | Layer name for NextGen hydrofabric file. |
#### Schema Reference (config_general - logging)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| level | str = debug \| info \| warning \| error \| critical | info | debug | Logging level. |
| log_to_file | bool | False | False | Whether to log to a file. If set to True, logging messages will be written to the specified log file, in addition to the console. |
| file | str \| NoneType | None | logfile.log | Path to the log file. If not provided, logging will be written to console only. |
### Specific configurations for formulation regionalization (formreg)

#### Example File (config_formreg.yaml)
```yaml
general: #-----------------------------------------------------------------------------------------------General settings for formulation regionalization
  huc12_hydrofabric_file: 'NationalWBDSnapshot.gdb' #----------------------------------------------------Path to HUC12 hydrofabric file containing HUC12 polygons for spatial discretization.
  divide_huc12_cwt_file: 'cwt_divide_huc12_{domain}.csv' #-----------------------------------------------("Path to crosswalk file between HUC12 basins and NextGen catchments, with columns 'divide_id' and 'huc_12'.",)
  calib_basins_only: False #-----------------------------------------------------------------------------Whether to run formulation selection only for calibrated basins (based on summary score). Set to True to limit formulation selection to calibrated basins only; in such cases, parameter regionalization for uncalibrated catchments will not consider preferred formulations.
  formulation_to_include: ['noah-owp-modular cfe-s t-route', 'noah-owp-modular ueb cfe-x t-route'] #-----List of formulations to consider. If None, all available formulations are considered.  If 'all', all formulations are included.
  formulation_to_exclude: ['noah-owp-modular cfe-s t-route'] #-------------------------------------------List of formulations to exclude. If None, no formulations are excluded from available options.
  consider_cost: False #---------------------------------------------------------------------------------Whether to consider computational costs of formulations in the regionalization process.
spatial_unit: #------------------------------------------------------------------------------------------Spatial discretization settings for formulation regionalization.
  huc_level: ['huc2', 'huc4', 'huc6', 'huc8', 'huc10', 'huc12'] #----------------------------------------("USGS HUC level used for spatial discretization (e.g., 'huc8'). A single formulation is selected per spatial unit given the spatial discretization level. Accepted formats: 'huc8', 'HUC8', 'huc-8'.",)
  nmin_calib_basin: 5 #----------------------------------------------------------------------------------Minimum number of calibration basins required per spatial unit for valid formulation selection.
  basin_fill_method: 'upscaling' #-----------------------------------------------------------------------Method to handle spatial units with too few calibration basins. Options: 'upscaling' (by upscaling to a coarser spatial unit), and 'nearest-neighbor' (by pooling basins from neighboring units).
  best_formulation: #------------------------------------------------------------------------------------Strategy to determine the best formulation for each spatial unit.
    method: 'total_score' #------------------------------------------------------------------------------("Method to determine the best formulation, options: 'total_score', 'average_score', which selects the formulation with the highest total or average summary score across all subdivisions (e.g., basins or divides as specified by the 'type' field), respectively.",)
    type: 'divide' #-------------------------------------------------------------------------------------Type of subdivision to use for computing total or average score, options: 'basin', 'divide'.
    tolerance: 0.05 #------------------------------------------------------------------------------------('Tolerance (on scale of 0.0 to 1.0) for the summary score. Formulations within this tolerance of the best score are considered equally good.',)
summary_score: #-----------------------------------------------------------------------------------------Summary score computation configuration for formulation regionalization.
  metric_eval_period: #----------------------------------------------------------------------------------Evaluation period of metrics to be used for screening donors.
    col_name: evalPeriod
    value: valid
  metrics: #---------------------------------------------------------------------------------------------Dictionary of metrics used in the summary score, keyed by metric name. Metric names must match columns in the calibration/validation stats file. Weights must sum to 1.0. Refer to schema of MetricConfig for individual metric settings.
    cor:
      upper: 1.0
      lower: -0.5
      orientation: positive
      weight: 0.5
    kge:
      upper: 1.0
      lower: -0.5
      orientation: positive
      weight: 0.5
formulation_cost: #--------------------------------------------------------------------------------------Computational cost configuration for each formulation.
  file: 'formulation_costs_secs_per_catchment.csv' #-----------------------------------------------------Path to CSV file with formulation costs. If provided, costs will be read from this file.
  costs: #-----------------------------------------------------------------------------------------------Dictionary of formulation costs, keyed by formulation name. If `file` is provided, this is ignored.
    noah-owp-modular ueb cfe-x t-route: 10
output: #------------------------------------------------------------------------------------------------Output configuration for formulation regionalization.
  formulation: #-----------------------------------------------------------------------------------------Output configurations for the selected formulations.
    save: True #-----------------------------------------------------------------------------------------Whether to save output files
    path: '{base_dir}/outputs/{run_name}/formulations' #-------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
    stem: 'form_{domain}_vpu{vpu_list}' #----------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
    stem_suffix: '_pars' #-------------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
    format: 'parquet' #----------------------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
    plots: #---------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
      spatial_map: True
      histogram: True
    plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
  config_final: #----------------------------------------------------------------------------------------Output configuration for the final configuration file after processing, with placeholders resolved.
    save: True #-----------------------------------------------------------------------------------------Whether to save output files
    path: '{base_dir}/outputs/{run_name}/config_formreg_final.yaml' #------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
    stem: ['form_{domain}_vpu{vpu_list}'] #--------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
    stem_suffix: ['_pars'] #-----------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
    format: ['parquet', 'csv', 'yaml'] #-----------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
    plots: #---------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
      histogram: True
      spatial_map: True
      columns_to_plot: ['param1', 'param2']
    plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
  summary_score: #---------------------------------------------------------------------------------------Output configurations for the summary score.
    save: True #-----------------------------------------------------------------------------------------Whether to save output files
    path: '{base_dir}/outputs/{run_name}/summary_score' #------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
    stem: 'score_{domain}_vpu{vpu_list}' #---------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
    stem_suffix: '_all_gages' #--------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
    format: 'parquet' #----------------------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
    plots: #---------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
      histogram: True
      spatial_map: True
    plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
```
#### Schema Reference (config_formreg - general)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| huc12_hydrofabric_file | str \| Path \| NoneType | None | NationalWBDSnapshot.gdb | Path to HUC12 hydrofabric file containing HUC12 polygons for spatial discretization. |
| divide_huc12_cwt_file | str \| NoneType | None | cwt_divide_huc12_{domain}.csv | ("Path to crosswalk file between HUC12 basins and NextGen catchments, with columns 'divide_id' and 'huc_12'.",) |
| calib_basins_only | bool | False | False | Whether to run formulation selection only for calibrated basins (based on summary score). Set to True to limit formulation selection to calibrated basins only; in such cases, parameter regionalization for uncalibrated catchments will not consider preferred formulations. |
| formulation_to_include | List[str] \| NoneType | None | ['noah-owp-modular cfe-s t-route', 'noah-owp-modular ueb cfe-x t-route'] | List of formulations to consider. If None, all available formulations are considered.  If 'all', all formulations are included. |
| formulation_to_exclude | List[str] \| NoneType | None | ['noah-owp-modular cfe-s t-route'] | List of formulations to exclude. If None, no formulations are excluded from available options. |
| consider_cost | bool | True | False | Whether to consider computational costs of formulations in the regionalization process. |
#### Schema Reference (config_formreg - spatial_unit)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| huc_level | str | huc8 | ['huc2', 'huc4', 'huc6', 'huc8', 'huc10', 'huc12'] | ("USGS HUC level used for spatial discretization (e.g., 'huc8'). A single formulation is selected per spatial unit given the spatial discretization level. Accepted formats: 'huc8', 'HUC8', 'huc-8'.",) |
| nmin_calib_basin | int | 3 | 5 | Minimum number of calibration basins required per spatial unit for valid formulation selection. |
| basin_fill_method | str = upscaling \| nearest-neighbor | upscaling | upscaling | Method to handle spatial units with too few calibration basins. Options: 'upscaling' (by upscaling to a coarser spatial unit), and 'nearest-neighbor' (by pooling basins from neighboring units). |
| best_formulation | BestFormulation | <factory> | {'method': 'total_score', 'type': 'divide', 'tolerance': 0.05} | Strategy to determine the best formulation for each spatial unit. |
#### Schema Reference (config_formreg - best_formulation)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| method | str = total_score \| average_score | total_score | total_score | ("Method to determine the best formulation, options: 'total_score', 'average_score', which selects the formulation with the highest total or average summary score across all subdivisions (e.g., basins or divides as specified by the 'type' field), respectively.",) |
| type | str = basin \| divide | PydanticUndefined | basin | Type of subdivision to use for computing total or average score, options: 'basin', 'divide'. |
| tolerance | float | 0.05 | 0.05 | ('Tolerance (on scale of 0.0 to 1.0) for the summary score. Formulations within this tolerance of the best score are considered equally good.',) |
#### Schema Reference (config_formreg - summary_score)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| metric_eval_period | MetricEvalPeriod \| NoneType | None | {'col_name': 'evalPeriod', 'value': 'valid'} | Evaluation period of metrics to be used for screening donors. |
| metrics | Dict[str, MetricConfig] | PydanticUndefined | {'cor': {'upper': 1.0, 'lower': -0.5, 'orientation': 'positive', 'weight': 0.5}, 'kge': {'upper': 1.0, 'lower': -0.5, 'orientation': 'positive', 'weight': 0.5}} | Dictionary of metrics used in the summary score, keyed by metric name. Metric names must match columns in the calibration/validation stats file. Weights must sum to 1.0. Refer to schema of MetricConfig for individual metric settings. |
#### Schema Reference (config_formreg - metric_eval_period)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| col_name | str \| NoneType | None | evalPeriod | Name of the column in the donor stats file that contains the evaluation period. No filtering by evaluation period if None. |
| value | str \| NoneType | None | full | Value of the evaluation period to filter donor stats. No filtering by evaluation period if None. |
#### Schema Reference (config_formreg - metrics)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| upper | float \| NoneType | None | 1 | Upper bound for scaling and normalization, must be greater than lower bound. |
| lower | float \| NoneType | None | 0 | Lower bound for scaling and normalization, must be less than upper bound. |
| orientation | str = positive \| negative | positive | positive | Orientation of the metric, either 'positive' or 'negative'. |
| weight | float | 0.0 | 0.25 | Weight of the metric in the summary score, must be between 0.0 and 1.0. If 0.0, the metric is ignored. |
| absolute | bool | False | False | Whether to use the absolute value of the metric (e.g., for bias) for normalization. |
#### Schema Reference (config_formreg - formulation_cost)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| file | str \| NoneType | None | formulation_costs_secs_per_catchment.csv | Path to CSV file with formulation costs. If provided, costs will be read from this file. |
| costs | Dict[str, float] \| NoneType | None | {'noah-owp-modular ueb cfe-x t-route': 10} | Dictionary of formulation costs, keyed by formulation name. If `file` is provided, this is ignored. |
#### Schema Reference (config_formreg - output)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| formulation | BaseOutputConfig | <factory> | {'save': True, 'path': '{base_dir}/outputs/{run_name}/formulations', 'stem': 'form_{domain}_vpu{vpu_list}', 'stem_suffix': '_pars', 'format': 'parquet', 'plots': {'spatial_map': True, 'histogram': True}} | Output configurations for the selected formulations. |
| config_final | BaseOutputConfig | PydanticUndefined | {'save': True, 'path': '{base_dir}/outputs/{run_name}/config_formreg_final.yaml'} | Output configuration for the final configuration file after processing, with placeholders resolved. |
| summary_score | BaseOutputConfig | PydanticUndefined | {'save': True, 'path': '{base_dir}/outputs/{run_name}/summary_score', 'stem': 'score_{domain}_vpu{vpu_list}', 'stem_suffix': '_all_gages', 'format': 'parquet', 'plots': {'histogram': True, 'spatial_map': True}} | Output configurations for the summary score. |
#### Schema Reference (config_formreg - BaseOutputConfig)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| save | bool | True | [True, False] | Whether to save output files |
| path | Path \| str | PydanticUndefined | ['{base_dir}/outputs/{run_name}/formulations'] | Path to save output file or files. If a directory, the 'stem' and 'format' must be specified. |
| stem | str \| Dict[str, str] \| NoneType | None | ['form_{domain}_vpu{vpu_list}'] | File stem for output files, used to create unique file names based on the path. |
| stem_suffix | str \| NoneType | None | ['_pars'] | Suffix for the file stem, used to create unique file names based on the path for specific needs. |
| format | str \| NoneType | None | ['parquet', 'csv', 'yaml'] | File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file. |
| plots | Dict[str, Any] \| NoneType | None | {'histogram': True, 'spatial_map': True, 'columns_to_plot': ['param1', 'param2']} | Configuration for output plots, if applicable. |
| plot_path | str \| NoneType | None | ['{base_dir}/outputs/{run_name}/formulations/plots'] | Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path. |
### Specific configurations for parameter regionalization (parreg)

#### Example File (config_parreg.yaml)
```yaml
general:
  general: #-------------------------------------------------------------------------------------------------------------------------General configuration settings specific to parameter regionalization.
    n_procs: -1 #--------------------------------------------------------------------------------------------------------------------Number of processors to use for parallel processing. Set to -1 to use all available processors.
    attr_dataset_list: ['ngen', 'streamcat'] #---------------------------------------------------------------------------------------List of attribute dataset names to use. Valid options include 'ngen', 'hlr', 'streamcat'.
    algorithm_list: ['gower', 'kmeans'] #--------------------------------------------------------------------------------------------Algorithms to use. Valid options ('gower', 'urf', 'kmeans', 'kmedoids', 'hdbscan', 'birch').
    manual_pairings_file: 'pairs_kmeans_conus_vpu09.parquet' #-----------------------------------------------------------------------Path to the manual pairings file. If provided, this file will be used to specify manual donor-receiver pairings, overriding the algorithmic selections.
  donor: #---------------------------------------------------------------------------------------------------------------------------Configuration for donor selection.
    buffer_km: 100.0 #---------------------------------------------------------------------------------------------------------------Size of buffer (in km) around current VPU to identify qualified donors.
    metric_eval_period: #------------------------------------------------------------------------------------------------------------Evaluation period of metrics to be used for screening donors.
      col_name: eval_period
      value: full
    metric_threshold: #--------------------------------------------------------------------------------------------------------------Dictionary of metric thresholds to be used for screening donors. Each key is a metric name, and the value is a MetricThreshold object specifying the min, max, and absolute settings. Refer to schema of MetricThreshold for details.
      cor:
        min: 0.4
        max: None
        absolute: False
      kge:
        min: 0.2
        max: None
        absolute: False
  attr_datasets: #-------------------------------------------------------------------------------------------------------------------Configuration for attribute datasets available for use in regionalization.
    ngen: #--------------------------------------------------------------------------------------------------------------------------Configuration for NGEN attribute dataset.(https://lynker-spatial.s3-us-west-2.amazonaws.com/hydrofabric/v2.2/hfv2.2-data_model.html).
      attr_select_file: '{base_dir}/inputs/attr_config/attr_selection_ngen.csv' #----------------------------------------------------Path to file where selection of attributes to use during regionalization may be found.
      attr_data_file: '{base_dir}/inputs/attr_datasets/ngen/attr_ngen_{domain}.parquet' #--------------------------------------------Path to file where attribute data may be found.
      base_attr_list: ['elevation', 'slope', 'aspect'] #-----------------------------------------------------------------------------Small list of basic attributes during a 2nd round of pairing if no donor is found using the full set of selected attributes during the first round.
    hlr: #---------------------------------------------------------------------------------------------------------------------------Configuration for Hydrologic Landscape Regions (HLR) attribute dataset (https://www.usgs.gov/publications/hydrologic-landscape-regions-united-states).
      attr_select_file: '{base_dir}/inputs/attr_config/attr_selection_hlr.csv' #-----------------------------------------------------Path to file where selection of attributes to use during regionalization may be found.
      attr_data_file: '{base_dir}/inputs/attr_datasets/hlr/attr_hlr_{domain}.parquet' #----------------------------------------------Path to file where attribute data may be found.
      base_attr_list: ['PPT', 'SAND'] #----------------------------------------------------------------------------------------------Small list of basic attributes during a 2nd round of pairing if no donor is found using the full set of selected attributes during the first round.
    streamcat: #---------------------------------------------------------------------------------------------------------------------Configuration for StreamCat attribute dataset (https://www.epa.gov/national-aquatic-resource-surveys/streamcat-dataset).
      attr_select_file: '{base_dir}/inputs/attr_config/attr_selection_streamcat.csv' #-----------------------------------------------Path to file where selection of attributes to use during regionalization may be found.
      attr_data_file: '{base_dir}/inputs/attr_datasets/streamcat/attr_streamcat_{domain}.parquet' #----------------------------------Path to file where attribute data may be found.
      base_attr_list: ['Precip_Minus_EVT', 'Elev', 'BFI'] #--------------------------------------------------------------------------Small list of basic attributes during a 2nd round of pairing if no donor is found using the full set of selected attributes during the first round.
  snow_cover: #----------------------------------------------------------------------------------------------------------------------Configuration for snow cover data to be used in determining whether catchments are snow-driven.
    consider_snowness: True #--------------------------------------------------------------------------------------------------------Whether to consider snow driven and non-snow driven catchments separately in the regionalization process. If True, snow-driven receivers will only consider snow-driven donors and non-snow-driven receivers will only consider non-snow-driven donors.
    snow_cover_file: 'vpu{vpu_list}_snow_frac.parquet' #-----------------------------------------------------------------------------Path to the snow cover data file, or a dictionary with VPU as keys and file paths as values.
    column: 'snow_pc_hydroatlas' #---------------------------------------------------------------------------------------------------Column name in the snow cover data file that contains the snow cover percentage.
    threshold: '20' #----------------------------------------------------------------------------------------------------------------Threshold value for snow cover percentage to determine if a catchment is considered snow-driven.
  output: #--------------------------------------------------------------------------------------------------------------------------Configuration for parameter regionalization output.
    pairs: #-------------------------------------------------------------------------------------------------------------------------Configuration for saving donor-receiver pairs.
      save: True #-------------------------------------------------------------------------------------------------------------------Whether to save output files
      path: '{base_dir}/outputs/{run_name}/pairs' #----------------------------------------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
      stem: 'pairs_{algorithm_list}_{domain}_vpu{vpu_list}' #------------------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
      stem_suffix: '_mswm' #---------------------------------------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
      format: 'parquet' #------------------------------------------------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
      plots: #-----------------------------------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
        spatial_map: True
        histogram: True
        columns_to_plot: ['distSpatial', 'distAttr']
      plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #--------------------------------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
    params: #------------------------------------------------------------------------------------------------------------------------Configuration for saving regionalized parameters.
      save: True #-------------------------------------------------------------------------------------------------------------------Whether to save output files
      path: '{base_dir}/outputs/{run_name}/params' #---------------------------------------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
      stem: 'formulation_params_{algorithm_list}_{domain}_vpu{vpu_list}' #-----------------------------------------------------------File stem for output files, used to create unique file names based on the path.
      stem_suffix: ['_pars'] #-------------------------------------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
      format: 'csv' #----------------------------------------------------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
      plots: #-----------------------------------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
        histogram: True
        spatial_map: True
        columns_to_plot: ['param1', 'param2']
      plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #--------------------------------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
    attr_data_final: #---------------------------------------------------------------------------------------------------------------("Configuration for saving and plotting final attribute data used in regionalization. Note only selected attributes are saved, and attribute names are prefixed with the name of the corresponding attribute source (e.g., 'Elev' in StreamCat becomes 'streamcat_Elev').",)
      save: True #-------------------------------------------------------------------------------------------------------------------Whether to save output files
      path: '{base_dir}/outputs/{run_name}/attr_data_final' #------------------------------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
      stem: 'attr_{domain}_vpu{vpu_list}' #------------------------------------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
      stem_suffix: ['_pars'] #-------------------------------------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
      format: 'parquet' #------------------------------------------------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
      plots: #-----------------------------------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
        spatial_map: True
        histogram: True
        columns_to_plot: ['streamcat_Elev', 'streamcat_BFI', 'streamcat_Precip_Minus_EVT', 'hlr_PMPE', 'hlr_SAND', 'hlr_TAVE']
      plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #--------------------------------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
    config_final: #------------------------------------------------------------------------------------------------------------------Configuration for saving final configuration file used in regionalization.
      save: True #-------------------------------------------------------------------------------------------------------------------Whether to save output files
      path: '{base_dir}/outputs/{run_name}/config_parreg_final.yaml' #---------------------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
      stem: ['form_{domain}_vpu{vpu_list}'] #----------------------------------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
      stem_suffix: ['_pars'] #-------------------------------------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
      format: 'yaml' #---------------------------------------------------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
      plots: #-----------------------------------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
        histogram: True
        spatial_map: True
        columns_to_plot: ['param1', 'param2']
      plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #--------------------------------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
    spatial_distance: #--------------------------------------------------------------------------------------------------------------Configuration for saving spatial distance data.
      save: True #-------------------------------------------------------------------------------------------------------------------Whether to save output files
      path: '{base_dir}/outputs/{run_name}/spatial_distance' #-----------------------------------------------------------------------Path to save output file or files. If a directory, the 'stem' and 'format' must be specified.
      stem: ['form_{domain}_vpu{vpu_list}'] #----------------------------------------------------------------------------------------File stem for output files, used to create unique file names based on the path.
      stem_suffix: ['_pars'] #-------------------------------------------------------------------------------------------------------Suffix for the file stem, used to create unique file names based on the path for specific needs.
      format: 'parquet' #------------------------------------------------------------------------------------------------------------File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file.
      plots: #-----------------------------------------------------------------------------------------------------------------------Configuration for output plots, if applicable.
        histogram: True
        spatial_map: True
        columns_to_plot: ['param1', 'param2']
      plot_path: ['{base_dir}/outputs/{run_name}/formulations/plots'] #--------------------------------------------------------------Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path.
  algorithms: #----------------------------------------------------------------------------------------------------------------------Algorithm configuration class.  See specific algorithms for additional arguments.
    gower: #-------------------------------------------------------------------------------------------------------------------------Configurations for the distance-based algorithm Gower.
      max_spa_dist: 1500.0 #---------------------------------------------------------------------------------------------------------Maximum spatial distance (km) to consider a donor suitable
      n_donor_max: 3 #---------------------------------------------------------------------------------------------------------------Maximum number of donors to keep that satisfy all criteria
      min_var_pca: 0.8 #-------------------------------------------------------------------------------------------------------------Minimum total variance explained by chosen PCA components
      min_attr_dist: 0.1 #-----------------------------------------------------------------------------------------------------------Minimum attribute distance. If one or more donors have a distance to receiver smaller than this threshold, stop searching.
      max_attr_dist: 0.25 #----------------------------------------------------------------------------------------------------------Maximum attribute distance. Donors with distance to receiver larger than this value are discarded, unless no donor smaller than this threshold is available.
      min_spa_dist: 200.0 #----------------------------------------------------------------------------------------------------------Starting distance (km) to iteratively search for donors in the neighborhood
      zero_spa_dist: 1.0 #-----------------------------------------------------------------------------------------------------------Distance threshold (in km) where receiver adopts a donor directly (i.e., donor/receiver are considered overlapping each other)
    urf: #---------------------------------------------------------------------------------------------------------------------------Configurations for the distance-based algorithm Unsupervised Random Forest (URF)
      max_spa_dist: 1500.0 #---------------------------------------------------------------------------------------------------------Maximum spatial distance (km) to consider a donor suitable
      n_donor_max: 3 #---------------------------------------------------------------------------------------------------------------Maximum number of donors to keep that satisfy all criteria
      min_var_pca: 0.8 #-------------------------------------------------------------------------------------------------------------Minimum total variance explained by chosen PCA components
      pca: False #-------------------------------------------------------------------------------------------------------------------Whether to perform PCA on the attribute data before building the forest. Preliminary testing indicates limited difference in results with/without PCA.
      n_trees: 500 #-----------------------------------------------------------------------------------------------------------------Number of trees in the random forest.
      max_depth: 3 #-----------------------------------------------------------------------------------------------------------------Maximum depth of each tree. If None, nodes are expanded until all leaves are pure.
      min_attr_dist: 0.1 #-----------------------------------------------------------------------------------------------------------Minimum attribute distance. If one or more donors have a distance to receiver smaller than this threshold, stop searching.
      max_attr_dist: 0.25 #----------------------------------------------------------------------------------------------------------Maximum attribute distance. Donors with distance to receiver larger than this value are discarded, unless no donor smaller than this threshold is available.
      min_spa_dist: 200.0 #----------------------------------------------------------------------------------------------------------Starting distance (km) to iteratively search for donors in the neighborhood
      zero_spa_dist: 1.0 #-----------------------------------------------------------------------------------------------------------Distance threshold (in km) where receiver adopts a donor directly (i.e., donor/receiver are considered overlapping each other)
    kmeans: #------------------------------------------------------------------------------------------------------------------------Configurations for the clustering algorithm K-means
      max_spa_dist: 1500.0 #---------------------------------------------------------------------------------------------------------Maximum spatial distance (km) to consider a donor suitable
      n_donor_max: 3 #---------------------------------------------------------------------------------------------------------------Maximum number of donors to keep that satisfy all criteria
      min_var_pca: 0.8 #-------------------------------------------------------------------------------------------------------------Minimum total variance explained by chosen PCA components
      n_iter_max: 100 #--------------------------------------------------------------------------------------------------------------Maximum number of iterations for the algorithm.
      init: 'k-means++' #------------------------------------------------------------------------------------------------------------Method for initialization.
      n_init: 3 #--------------------------------------------------------------------------------------------------------------------Number of times the k-means algorithm will be run with different centroid seeds.
    kmedoids: #----------------------------------------------------------------------------------------------------------------------Configurations for the clustering algorithm K-medoids
      max_spa_dist: 1500.0 #---------------------------------------------------------------------------------------------------------Maximum spatial distance (km) to consider a donor suitable
      n_donor_max: 3 #---------------------------------------------------------------------------------------------------------------Maximum number of donors to keep that satisfy all criteria
      min_var_pca: 0.8 #-------------------------------------------------------------------------------------------------------------Minimum total variance explained by chosen PCA components
      n_iter_max: 100 #--------------------------------------------------------------------------------------------------------------Maximum number of iterations for the algorithm.
      init: 'random' #---------------------------------------------------------------------------------------------------------------Method for initialization.
    hdbscan: #-----------------------------------------------------------------------------------------------------------------------('Configurations for the clustering algorithm Hierarchical Density Based Spatial Clustering of Applications with Noise (HDBSCAN)',)
      max_spa_dist: 1500.0 #---------------------------------------------------------------------------------------------------------Maximum spatial distance (km) to consider a donor suitable
      n_donor_max: 20 #--------------------------------------------------------------------------------------------------------------Maximum number of donors to keep that satisfy all criteria.
      min_var_pca: 0.8 #-------------------------------------------------------------------------------------------------------------Minimum total variance explained by chosen PCA components
      min_cluster_size: 3 #----------------------------------------------------------------------------------------------------------Minimum size of clusters (to avoid being considered noise)
    birch: #-------------------------------------------------------------------------------------------------------------------------('Configurations for the clustering algorithm Balanced Iterative Reducing and Clustering using Hierarchies (BIRCH)',)
      max_spa_dist: 1500.0 #---------------------------------------------------------------------------------------------------------Maximum spatial distance (km) to consider a donor suitable
      n_donor_max: 3 #---------------------------------------------------------------------------------------------------------------Maximum number of donors to keep that satisfy all criteria
      min_var_pca: 0.8 #-------------------------------------------------------------------------------------------------------------Minimum total variance explained by chosen PCA components
      branching_factor: 50 #---------------------------------------------------------------------------------------------------------Branching factor for the BIRCH algorithm.
      min_thresh: 1.5 #--------------------------------------------------------------------------------------------------------------Minimum threshold for the BIRCH algorithm. The algorithm will iterate through thresholds between min_thresh and max_thresh to identify a suitable threshold.
      max_thresh: 4.0 #--------------------------------------------------------------------------------------------------------------Maximum threshold for the BIRCH algorithm. The algorithm will iterate through thresholds between min_thresh and max_thresh to identify a suitable threshold.
      max_resample: 20 #-------------------------------------------------------------------------------------------------------------Maximum number of resamples.
```
#### Schema Reference (config_parreg - general)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| n_procs | int | -1 | -1 | Number of processors to use for parallel processing. Set to -1 to use all available processors. |
| attr_dataset_list | List[str = ngen \| hlr \| streamcat] | ['ngen'] | ['ngen', 'streamcat'] | List of attribute dataset names to use. Valid options include 'ngen', 'hlr', 'streamcat'. |
| algorithm_list | List[str = gower \| urf \| kmeans \| kmedoids \| hdbscan \| birch] | ['gower'] | ['gower', 'kmeans'] | Algorithms to use. Valid options ('gower', 'urf', 'kmeans', 'kmedoids', 'hdbscan', 'birch'). |
| manual_pairings_file | Path \| str \| NoneType | None | pairs_kmeans_conus_vpu09.parquet | Path to the manual pairings file. If provided, this file will be used to specify manual donor-receiver pairings, overriding the algorithmic selections. |
#### Schema Reference (config_parreg - donor)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| buffer_km | float \| NoneType | 0.0 | 100.0 | Size of buffer (in km) around current VPU to identify qualified donors. |
| metric_eval_period | MetricEvalPeriod \| NoneType | None | {'col_name': 'eval_period', 'value': 'full'} | Evaluation period of metrics to be used for screening donors. |
| metric_threshold | Dict[str, MetricThreshold] | None | {'cor': {'min': 0.4, 'max': None, 'absolute': False}, 'kge': {'min': 0.2, 'max': None, 'absolute': False}} | Dictionary of metric thresholds to be used for screening donors. Each key is a metric name, and the value is a MetricThreshold object specifying the min, max, and absolute settings. Refer to schema of MetricThreshold for details. |
#### Schema Reference (config_parreg - metric_eval_period)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| col_name | str \| NoneType | None | evalPeriod | Name of the column in the donor stats file that contains the evaluation period. No filtering by evaluation period if None. |
| value | str \| NoneType | None | full | Value of the evaluation period to filter donor stats. No filtering by evaluation period if None. |
#### Schema Reference (config_parreg - metric_threshold)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| min | float \| NoneType | None | None | Minimum threshold for the metric. If None, no minimum threshold is applied. |
| max | float \| NoneType | None | None | Maximum threshold for the metric. If None, no maximum threshold is applied. |
| absolute | bool \| NoneType | False | False | If True, apply the absolute value of the metric before applying the thresholds. |
#### Schema Reference (config_parreg - attr_datasets_config)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| attr_list | list \| NoneType | None | None | List of attributes to use from this dataset. If not provided, attributes will be determined from attr_select_file. Either this field or attr_select_file must be provided.If both are provided, attr_list takes priority. |
| attr_select_file | Path \| str \| NoneType | None | ['attr_selection_ngen.csv'] | Path to file where selection of attributes to use during regionalization may be found. |
| attr_data_file | Path \| str \| NoneType | None | ['attr_ngen_{domain}.parquet'] | Path to file where attribute data may be found. |
| base_attr_list | list \| NoneType | None | ['elevation', 'slope', 'aspect'] | Small list of basic attributes during a 2nd round of pairing if no donor is found using the full set of selected attributes during the first round. |
#### Schema Reference (config_parreg - attr_datasets)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| ngen | AttrDatasetConfig | PydanticUndefined | {'attr_list': None, 'attr_select_file': '{base_dir}/inputs/attr_config/attr_selection_ngen.csv', 'attr_data_file': '{base_dir}/inputs/attr_datasets/ngen/attr_ngen_{domain}.parquet', 'base_attr_list': ['elevation', 'slope', 'aspect']} | Configuration for NGEN attribute dataset.(https://lynker-spatial.s3-us-west-2.amazonaws.com/hydrofabric/v2.2/hfv2.2-data_model.html). |
| hlr | AttrDatasetConfig | PydanticUndefined | {'attr_list': None, 'attr_select_file': '{base_dir}/inputs/attr_config/attr_selection_hlr.csv', 'attr_data_file': '{base_dir}/inputs/attr_datasets/hlr/attr_hlr_{domain}.parquet', 'base_attr_list': ['PPT', 'SAND']} | Configuration for Hydrologic Landscape Regions (HLR) attribute dataset (https://www.usgs.gov/publications/hydrologic-landscape-regions-united-states). |
| streamcat | AttrDatasetConfig | PydanticUndefined | {'attr_list': None, 'attr_select_file': '{base_dir}/inputs/attr_config/attr_selection_streamcat.csv', 'attr_data_file': '{base_dir}/inputs/attr_datasets/streamcat/attr_streamcat_{domain}.parquet', 'base_attr_list': ['Precip_Minus_EVT', 'Elev', 'BFI']} | Configuration for StreamCat attribute dataset (https://www.epa.gov/national-aquatic-resource-surveys/streamcat-dataset). |
#### Schema Reference (config_parreg - snow_cover)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| consider_snowness | bool \| NoneType | True | True | Whether to consider snow driven and non-snow driven catchments separately in the regionalization process. If True, snow-driven receivers will only consider snow-driven donors and non-snow-driven receivers will only consider non-snow-driven donors. |
| snow_cover_file | Path \| str \| Dict[str, Path \| str] \| NoneType | None | vpu{vpu_list}_snow_frac.parquet | Path to the snow cover data file, or a dictionary with VPU as keys and file paths as values. |
| column | str \| NoneType | snow_pc_hydroatlas | snow_pc_hydroatlas | Column name in the snow cover data file that contains the snow cover percentage. |
| threshold | float \| NoneType | None | 20 | Threshold value for snow cover percentage to determine if a catchment is considered snow-driven. |
#### Schema Reference (config_parreg - algorithms)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| gower | Gower | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 min_attr_dist=0.1 max_attr_dist=0.2 min_spa_dist=100.0 zero_spa_dist=1.0 | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 min_attr_dist=0.1 max_attr_dist=0.2 min_spa_dist=100.0 zero_spa_dist=1.0 | Configurations for the distance-based algorithm Gower. |
| urf | URF | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 pca=False n_trees=500 max_depth=3 min_attr_dist=None max_attr_dist=None min_spa_dist=None zero_spa_dist=None | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 pca=False n_trees=500 max_depth=3 min_attr_dist=None max_attr_dist=None min_spa_dist=None zero_spa_dist=None | Configurations for the distance-based algorithm Unsupervised Random Forest (URF) |
| kmeans | KMeans | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 n_iter_max=100 init='k-means++' n_init=None | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 n_iter_max=100 init='k-means++' n_init=None | Configurations for the clustering algorithm K-means |
| kmedoids | KMedoids | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 n_iter_max=None init='random' | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 n_iter_max=None init='random' | Configurations for the clustering algorithm K-medoids |
| hdbscan | HDBSCAN | max_spa_dist=1000.0 n_donor_max=20 min_var_pca=0.9 min_cluster_size=3 | max_spa_dist=1000.0 n_donor_max=20 min_var_pca=0.9 min_cluster_size=3 | ('Configurations for the clustering algorithm Hierarchical Density Based Spatial Clustering of Applications with Noise (HDBSCAN)',) |
| birch | Birch | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 branching_factor=50 min_thresh=1.5 max_thresh=4.0 max_resample=20 | max_spa_dist=1000.0 n_donor_max=3 min_var_pca=0.9 branching_factor=50 min_thresh=1.5 max_thresh=4.0 max_resample=20 | ('Configurations for the clustering algorithm Balanced Iterative Reducing and Clustering using Hierarchies (BIRCH)',) |
#### Schema Reference (config_parreg - algo_general)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| max_spa_dist | float \| NoneType | 1000.0 | 1500.0 | Maximum spatial distance (km) to consider a donor suitable |
| n_donor_max | int \| NoneType | 3 | 3 | Maximum number of donors to keep that satisfy all criteria |
| min_var_pca | float \| NoneType | 0.9 | 0.8 | Minimum total variance explained by chosen PCA components |
#### Schema Reference (config_parreg - gower)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| max_spa_dist | float \| NoneType | 1000.0 | 1500.0 | Maximum spatial distance (km) to consider a donor suitable |
| n_donor_max | int \| NoneType | 3 | 3 | Maximum number of donors to keep that satisfy all criteria |
| min_var_pca | float \| NoneType | 0.9 | 0.8 | Minimum total variance explained by chosen PCA components |
| min_attr_dist | float \| NoneType | 0.1 | 0.1 | Minimum attribute distance. If one or more donors have a distance to receiver smaller than this threshold, stop searching. |
| max_attr_dist | float \| NoneType | 0.2 | 0.25 | Maximum attribute distance. Donors with distance to receiver larger than this value are discarded, unless no donor smaller than this threshold is available. |
| min_spa_dist | float \| NoneType | 100.0 | 200.0 | Starting distance (km) to iteratively search for donors in the neighborhood |
| zero_spa_dist | float \| NoneType | 1.0 | 1.0 | Distance threshold (in km) where receiver adopts a donor directly (i.e., donor/receiver are considered overlapping each other) |
#### Schema Reference (config_parreg - kmeans)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| max_spa_dist | float \| NoneType | 1000.0 | 1500.0 | Maximum spatial distance (km) to consider a donor suitable |
| n_donor_max | int \| NoneType | 3 | 3 | Maximum number of donors to keep that satisfy all criteria |
| min_var_pca | float \| NoneType | 0.9 | 0.8 | Minimum total variance explained by chosen PCA components |
| n_iter_max | int \| NoneType | 100 | 100 | Maximum number of iterations for the algorithm. |
| init | str = k-means++ \| random \| NoneType | k-means++ | k-means++ | Method for initialization. |
| n_init | int \| NoneType | None | 3 | Number of times the k-means algorithm will be run with different centroid seeds. |
#### Schema Reference (config_parreg - kmedoids)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| max_spa_dist | float \| NoneType | 1000.0 | 1500.0 | Maximum spatial distance (km) to consider a donor suitable |
| n_donor_max | int \| NoneType | 3 | 3 | Maximum number of donors to keep that satisfy all criteria |
| min_var_pca | float \| NoneType | 0.9 | 0.8 | Minimum total variance explained by chosen PCA components |
| n_iter_max | int \| NoneType | None | 100 | Maximum number of iterations for the algorithm. |
| init | str = random \| huristic \| k-medoids++ \| build \| NoneType | random | random | Method for initialization. |
#### Schema Reference (config_parreg - birch)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| max_spa_dist | float \| NoneType | 1000.0 | 1500.0 | Maximum spatial distance (km) to consider a donor suitable |
| n_donor_max | int \| NoneType | 3 | 3 | Maximum number of donors to keep that satisfy all criteria |
| min_var_pca | float \| NoneType | 0.9 | 0.8 | Minimum total variance explained by chosen PCA components |
| branching_factor | int \| NoneType | 50 | 50 | Branching factor for the BIRCH algorithm. |
| min_thresh | float \| NoneType | 1.5 | 1.5 | Minimum threshold for the BIRCH algorithm. The algorithm will iterate through thresholds between min_thresh and max_thresh to identify a suitable threshold. |
| max_thresh | float \| NoneType | 4.0 | 4.0 | Maximum threshold for the BIRCH algorithm. The algorithm will iterate through thresholds between min_thresh and max_thresh to identify a suitable threshold. |
| max_resample | int \| NoneType | 20 | 20 | Maximum number of resamples. |
#### Schema Reference (config_parreg - hdbscan)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| max_spa_dist | float \| NoneType | 1000.0 | 1500.0 | Maximum spatial distance (km) to consider a donor suitable |
| n_donor_max | int \| NoneType | 20 | 20 | Maximum number of donors to keep that satisfy all criteria. |
| min_var_pca | float \| NoneType | 0.9 | 0.8 | Minimum total variance explained by chosen PCA components |
| min_cluster_size | int \| NoneType | 3 | 3 | Minimum size of clusters (to avoid being considered noise) |
#### Schema Reference (config_parreg - output)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| pairs | BaseOutputConfig | <factory> | {'save': True, 'path': '{base_dir}/outputs/{run_name}/pairs', 'stem': 'pairs_{algorithm_list}_{domain}_vpu{vpu_list}', 'stem_suffix': '_mswm', 'format': 'parquet', 'plots': {'spatial_map': True, 'histogram': True, 'columns_to_plot': ['distSpatial', 'distAttr']}} | Configuration for saving donor-receiver pairs. |
| params | BaseOutputConfig | <factory> | {'save': True, 'path': '{base_dir}/outputs/{run_name}/params', 'stem': 'formulation_params_{algorithm_list}_{domain}_vpu{vpu_list}', 'format': 'csv'} | Configuration for saving regionalized parameters. |
| attr_data_final | BaseOutputConfig | <factory> | {'save': True, 'path': '{base_dir}/outputs/{run_name}/attr_data_final', 'stem': 'attr_{domain}_vpu{vpu_list}', 'format': 'parquet', 'plots': {'spatial_map': True, 'histogram': True, 'columns_to_plot': ['streamcat_Elev', 'streamcat_BFI', 'streamcat_Precip_Minus_EVT', 'hlr_PMPE', 'hlr_SAND', 'hlr_TAVE']}} | ("Configuration for saving and plotting final attribute data used in regionalization. Note only selected attributes are saved, and attribute names are prefixed with the name of the corresponding attribute source (e.g., 'Elev' in StreamCat becomes 'streamcat_Elev').",) |
| config_final | BaseOutputConfig | <factory> | {'save': True, 'path': '{base_dir}/outputs/{run_name}/config_parreg_final.yaml', 'format': 'yaml'} | Configuration for saving final configuration file used in regionalization. |
| spatial_distance | BaseOutputConfig | <factory> | {'save': True, 'path': '{base_dir}/outputs/{run_name}/spatial_distance', 'format': 'parquet'} | Configuration for saving spatial distance data. |
#### Schema Reference (config_parreg - BaseOutputConfig)
| Field | Type(s) | Default | Example(s) | Description |
| --- | --- | --- | --- | --- |
| save | bool | True | [True, False] | Whether to save output files |
| path | Path \| str | PydanticUndefined | ['{base_dir}/outputs/{run_name}/formulations'] | Path to save output file or files. If a directory, the 'stem' and 'format' must be specified. |
| stem | str \| Dict[str, str] \| NoneType | None | ['form_{domain}_vpu{vpu_list}'] | File stem for output files, used to create unique file names based on the path. |
| stem_suffix | str \| NoneType | None | ['_pars'] | Suffix for the file stem, used to create unique file names based on the path for specific needs. |
| format | str \| NoneType | None | ['parquet', 'csv', 'yaml'] | File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file. |
| plots | Dict[str, Any] \| NoneType | None | {'histogram': True, 'spatial_map': True, 'columns_to_plot': ['param1', 'param2']} | Configuration for output plots, if applicable. |
| plot_path | str \| NoneType | None | ['{base_dir}/outputs/{run_name}/formulations/plots'] | Path to save output plots, if applicable. If not specified, plots will be saved in a subfolder 'plots' in the defined output path. |

:::{toctree}
:maxdepth: 2
:hidden:

General<general>
Formulation Regionalization<formreg>
Parameter Regionalization<parreg>
:::