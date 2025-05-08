"""
This module defines classes for validating the configuration
"""

from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel, model_validator, ValidationError, Field, ConfigDict
from pathlib import Path
import yaml
import re
import pandas as pd
import pyarrow.parquet as pq
from .utils import check_columns

class GeneralConfig(BaseModel):

    """Configuration for the general section of the regionalization pipeline."""
    
    run_name: str = Field()
    """User-defined name for the run, used to name the output directory."""
   
    domain: str = Field()
    """NWM domain to run regionalization. Valid options include 'conus', 'ak', 'hi', 'prvi'."""

    vpu_list: Optional[Union[List[str], str]] = Field()
    """List of VPU codes to include. Can be a list or a single string (e.g., '01', ['01','02'])."""

    attr_dataset_list: List[str] = Field()
    """List of attribute dataset names to use. Valid options include 'ngen', 'hlr'."""

    algorithm_list: List[str] = Field()
    """Algorithms to use. Valid options ('gower', 'urf', 'kmeans', 'kmedoids', 'hdbscan', 'birch')."""

    base_dir: Path | str = Field()
    """Base directory for the regionalization run. All output files will be saved here. Recommended to store all inputs here too."""

    hydrofabric_file: Path | str | List[Path] | List[str] = Field()
    """Path to the hydrofabric file(s) of the domain/vpu(s). This file is used to determine the spatial structure of the data."""

class MetricEvalPeriod(BaseModel):
    col_name: str
    value: str
    """Configuration for the evaluation period of metrics to be used for screening donors."""

class MetricThreshold(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    absolute: Optional[bool] = None

    @model_validator(mode="after")
    def validate_either_field_exists(self):
        if not self.min and not self.max:
            raise ValueError(f"At least one of 'min' or 'max' must be provided.")
        return self

class DonorConfig(BaseModel):
    id_name: str
    donor_ngen_cwt_file: Path | str
    donor_gage_file: Path | str
    donor_stats_file: Optional[Path | str] = None
    metric_eval_period: Optional[MetricEvalPeriod] = None
    metric_threshold: Optional[Dict[str, MetricThreshold]] = None

        
    def check_files(self):
        """ Validate that the required columns are present in donor files. """

        check_columns(self.donor_ngen_cwt_file, [self.id_name])
        check_columns(self.donor_gage_file, [self.id_name])    

        # Skip metric validation if metric_threshold is empty or None
        if not self.metric_threshold:
            return self
        
        # Check if donor_stats_file is provided and exists
        if not self.donor_stats_file or not Path(self.donor_stats_file).exists():
            raise ValueError(f"donor_stats_file not found at: {self.donor_stats_file}")

        # Check if donor_stats_file has the required columns
        cols_metric = {k.lower() for k in self.metric_threshold.keys()}
        col_period = {self.metric_eval_period.col_name.lower()}
        cols_all = cols_metric.union(col_period | {self.id_name.lower()})        
        check_columns(self.donor_stats_file, cols_all)

    
    def screen_donors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Screen donors based on the metric thresholds and evaluation period."""
        
        if not self.metric_threshold:
            return df
        
        # Filter based on the evaluation period
        if self.metric_eval_period:
            periods = df[self.metric_eval_period.col_name].unique()
            if self.metric_eval_period.value not in periods:
                raise ValueError(f"Column {self.metric_eval_period.value} not found in {self.donor_stats_file}.")
            else:
                # Filter the DataFrame based on the evaluation period
                df = df[df[self.metric_eval_period.col_name] == self.metric_eval_period.value]

        # Apply metric thresholds
        for col, threshold in self.metric_threshold.items():
            if threshold.absolute:
                df[col] = df[col].abs()
            if threshold.min is not None:
                df = df[df[col] >= threshold.min]
            if threshold.max is not None:
                df = df[df[col] <= threshold.max]

        return df['gage_id'].unique().tolist()
    
class AttrDatasetConfig(BaseModel):
    attr_list: Optional[list] = None
    attr_select_file: Optional[Path | str] = None
    attr_data_file: Optional[Path | str] = None

    @model_validator(mode="after")
    def validate_either_field_exists(self):
        if not self.attr_list and not self.attr_select_file:
            raise ValueError(f"At least one of 'attr_list' or 'attr_select_file' must be provided."
                             " If both are provided, 'attr_list' takes priority.")
        return self
    
    
    def _get_selected_attrs(self):        
        """Private method to load the list of selected attributes."""

        # determine list of attributes to use from either attr_list or attr_select_file
        # if both are provided, attr_list takes priority
        if self.attr_list:            
            # make sure attr_list is valid
            attrs1 = [x for x in self.attr_list if x not in pq.ParquetFile(self.attr_data_file).schema.names]
            if attrs1:
                raise ValueError(f'These attributes {attrs1} are not found in {self.attr_data_file}')
        else:
            attr_select_path = Path(self.attr_select_file)
            if not attr_select_path.exists():
                raise FileNotFoundError(f"Select file not found: {self.attr_select_file}")

            df_attrs = pd.read_csv(attr_select_path)
            
            if 'select' not in df_attrs.columns or 'attr_name' not in df_attrs.columns:
                raise ValueError(f"Missing required columns 'select' and/or 'attr_name' in file: {self.attr_select_file}")
            
            self.attr_list = df_attrs[df_attrs['select'] == 1]['attr_name'].to_list()

    def get_attr_data(self) -> pd.DataFrame:
        """load attribute data filtered by selected attributes."""

        self._get_selected_attrs()

        if not self.attr_data_file:
            raise FileNotFoundError("No attr_data_file provided.")
        
        attr_data_path = Path(self.attr_data_file)
        if not attr_data_path.exists():
            raise FileNotFoundError(f"Attribute data file not found: {self.attr_data_file}")

        suffix = attr_data_path.suffix.lower()
        if suffix == '.csv':
            df_data = pd.read_csv(attr_data_path)
        elif suffix == '.parquet':
            df_data = pd.read_parquet(attr_data_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        missing_cols = set(self.attr_list) - set(df_data.columns)
        if missing_cols:
            raise ValueError(f"Missing attributes in data file: {missing_cols}")

        return df_data[['divide_id'] + self.attr_list]             

class AttrDatasets(BaseModel):
    hlr: Optional[AttrDatasetConfig] = None
    ngen: Optional[AttrDatasetConfig] = None
    hydroatlas: Optional[AttrDatasetConfig] = None
    streamcat: Optional[AttrDatasetConfig] = None
    nhdplus: Optional[AttrDatasetConfig] = None
    camels: Optional[AttrDatasetConfig] = None

class OutputSection(BaseModel):
    save: bool
    path: Path | str
    format: Optional[str] = None

    @model_validator(mode='after')
    def check_format_if_dir(cls, values):
        if not Path(values.path).suffix and not values.format:
            raise ValueError(f"'format' must be specified if 'path' is a directory: {Path(values.path)}")

        return values

class OutputConfig(BaseModel):
    pairs: OutputSection
    attr_data_final: OutputSection
    config_final: OutputSection


class AlgoGeneral(BaseModel):
    min_snow_frac: float
    max_spa_dist: float
    max_attr_diff: Dict[str, float]
    n_donor_max: int
    min_var_pca: float


class Gower(AlgoGeneral):
    min_attr_dist: float
    max_attr_dist: float
    min_spa_dist: float
    n_donor_max: int
    zero_spa_dist: float


class URF(AlgoGeneral):
    pca: bool
    n_trees: int
    max_depth: int
    min_attr_dist: float
    max_attr_dist: float
    min_spa_dist: float
    n_donor_max: int
    zero_spa_dist: float


class KMeans(AlgoGeneral):
    n_donor_max: int
    n_iter_max: int
    init: str
    n_init: int


class KMedoids(AlgoGeneral):
    n_donor_max: int
    n_iter_max: int
    init: str


class HDBSCAN(AlgoGeneral):
    n_donor_max: int
    min_cluster_size: int


class Birch(AlgoGeneral):
    n_donor_max: int
    branching_factor: int
    min_thresh: float
    max_thresh: float
    max_resample: int


class AlgorithmConfig(BaseModel):
    general: AlgoGeneral
    gower: Optional[Gower] = None
    urf: Optional[URF] = None
    kmeans: Optional[KMeans] = None
    kmedoids: Optional[KMedoids] = None
    hdbscan: Optional[HDBSCAN] = None
    birch: Optional[Birch] = None


class Config(BaseModel):
    general: GeneralConfig
    donor: DonorConfig
    attr_datasets: AttrDatasets
    output: OutputConfig
    algorithms: AlgorithmConfig

    @model_validator(mode='after')
    def check_required_algorithms_present(self):
        required = set(self.general.algorithm_list)
        defined = set(self.algorithms.model_dump(exclude_unset=True).keys())

        missing = required - defined
        if missing:
            raise ValueError(
                f"The following algorithms are listed in 'general.algorithm_list' "
                f"but missing from the 'algorithms' section: {missing}"
            )
        return self

    @model_validator(mode='after')
    def check_required_attr_datasets_present(self):
        required = set(self.general.attr_dataset_list)
        defined = set(self.attr_datasets.model_dump(exclude_unset=True).keys())

        missing = required - defined
        if missing:
            raise ValueError(
                f"The following attribute datasets are listed in 'general.attr_dataset_list' "
                f"but missing from the 'attr_datasets' section: {missing}"
            )
        return self