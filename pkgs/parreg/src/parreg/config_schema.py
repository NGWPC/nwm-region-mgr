"""Defines classes for validating the configuration."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pyarrow.parquet as pq
from pydantic import BaseModel, Field, model_validator

from .utils import check_columns, read_table, save_data

logger = logging.getLogger(__name__)


class GeneralConfig(BaseModel):
    """Configuration for the general section of the regionalization pipeline."""

    run_name: str = Field()
    """User-defined name for the run, used to name the output directory."""

    domain: str = Field()
    """NWM domain to run regionalization. Valid options include 'conus', 'ak', 'hi', 'prvi'."""

    vpu_list: Optional[Union[List[str], str]] = Field()
    """List of VPU codes to include. Can be a list or a single string (e.g., '01', ['01','02'])."""

    n_procs: int = Field()
    """Number of processors to use for parallel processing. Default is 1. Set to -1 to use all available processors."""

    attr_dataset_list: List[str] = Field()
    """List of attribute dataset names to use. Valid options include 'ngen', 'hlr'."""

    algorithm_list: List[str] = Field()
    """Algorithms to use. Valid options ('gower', 'urf', 'kmeans', 'kmedoids', 'hdbscan', 'birch')."""

    base_dir: Path | str = Field()
    """Base directory for the regionalization run. All output files will be saved here. 
    Recommended to store all inputs here too."""

    hydrofabric_file: Path | str | Dict[str, Path] | Dict[str, str] = Field()
    """Path to the hydrofabric file(s) of the domain/vpu(s). 
    This file is used to determine the spatial structure of the data."""

    id_name: Optional[str] = Field(default="divide_id")
    """Name of the id column of catchment divide in the hydrofabric file. Default is 'divide_id'. 
    id_name is used to identify catchments in the attribute datasets and the output files."""


class MetricEvalPeriod(BaseModel):
    """Configuration for the evaluation period of metrics to be used for screening donors."""

    col_name: str
    """Name of the column in the donor stats file that contains the evaluation period."""

    value: str
    """Value of the evaluation period to filter the donor stats file."""


class MetricThreshold(BaseModel):
    """Configuration for the thresholds of metrics to be used for screening donors."""

    min: Optional[float] = None
    """Minimum threshold for the metric. If None, no minimum threshold is applied."""

    max: Optional[float] = None
    """Maximum threshold for the metric. If None, no maximum threshold is applied."""

    absolute: Optional[bool] = False
    """If True, apply the absolute value of the metric before applying the thresholds."""

    @model_validator(mode="after")
    def validate_either_field_exists(self):
        """Validate that at least one of 'min' or 'max' is provided."""
        if not self.min and not self.max:
            raise ValueError("At least one of 'min' or 'max' must be provided.")
        return self


class DonorConfig(BaseModel):
    """Configuration for donor selection."""

    id_name: str = Field(default="gage_id")
    """Name of the column in the donor files that contains the unique identifier for each gage. Default is 'gage_id'.
    id_name is used to identify gages in the donor files."""

    donor_gage_file: Optional[Path | str] = None
    """Path to the gage file containing the gage IDs to be used as donors. 
    When not provided, initial donor gages will be inferred from donor_ngen_cwt_file instead."""

    donor_ngen_cwt_file: Path | str
    """Path to the crosswalk file mapping the donor gage_id with NextGen catchment divide_id."""

    donor_stats_file: Optional[Path | str] = None
    """Optional: Path to the donor stats file containing the metrics to be used for screening donors."""

    buffer_km: Optional[float] = 0.0
    """Optional: size of buffer (in km) around current VPU to identify qualified donors"""

    metric_eval_period: Optional[MetricEvalPeriod] = None
    """Optional: evaluation period of metrics to be used for screening donors."""

    metric_threshold: Optional[Dict[str, MetricThreshold]] = None
    """Optional: dictionary of metric thresholds to be used for screening donors."""

    def _check_files(self):
        """Validate that the required columns are present in donor files."""
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

    def get_qualified_donors(
        self, vpu: str = None, donors: list = None, id_name: str = "divide_id"
    ) -> list:
        """Screen donors based on the metric thresholds and evaluation period."""
        # check if the required files/columns are present
        self._check_files()

        # determine inital donor gages
        df_cwt = read_table(self.donor_ngen_cwt_file)
        if not donors:
            if self.donor_gage_file:
                logger.info(
                    f"Initial donors based on all gages in {self.donor_gage_file}"
                )
                df = read_table(self.donor_gage_file)
                donors = df[self.id_name].unique().tolist()
            else:
                logger.info(
                    f"Initial donors based on all gages in {self.donor_ngen_cwt_file}"
                )
                donors = df_cwt[self.id_name].unique().tolist()

        # donor_cats = df_cwt[id_name].unique().tolist()
        donor_cats = (
            df_cwt[df_cwt[self.id_name].isin(donors)][id_name].unique().tolist()
        )

        # filter by vpu if provided
        if vpu:
            if "vpuid" in df_cwt.columns:
                df_cwt = df_cwt[df_cwt["vpuid"] == vpu]
                donors0 = df_cwt[self.id_name].unique().tolist()
                donors = [d for d in donors if d in donors0]
                donor_cats = (
                    df_cwt[df_cwt[self.id_name].isin(donors)][id_name].unique().tolist()
                )
                logger.info(
                    f"Number of initial donors for VPU {vpu}: {len(donors)} gages, {len(donor_cats)} catchments"
                )
            else:
                raise ValueError(
                    f"Column 'vpuid' not found in {self.donor_ngen_cwt_file}. Cannot filter by VPU."
                )
        else:
            logger.info(
                f"Number of initial donors from all VPUs: {len(donors)} gages, {len(donor_cats)} catchments"
            )

        # if no metric thresholds are provided, return all gage_ids
        if not self.metric_threshold:
            logger.info(
                "No metric thresholds provided. Using all gages in the initial list as donors."
            )
            return {"gage_id": donors, id_name: donor_cats}

        # read the donor stats file
        df = read_table(self.donor_stats_file)

        # filter based on initial donors
        df = df[df[self.id_name].isin(donors)]
        if df.empty:
            logger.warning(
                f"No matching gages found in {self.donor_stats_file} for the initial donors. "
                f"Returning the initial list."
            )
            return {"gage_id": donors, id_name: donor_cats}
        else:
            if len(df) < len(donors):
                logger.warning(
                    f"Some gages in the initial list are not found in {self.donor_stats_file}. "
                    f"Only {len(df)} gages are found. Using these as donors."
                )

        # filter based on the evaluation period
        if self.metric_eval_period:
            periods = df[self.metric_eval_period.col_name].unique()
            if self.metric_eval_period.value not in periods:
                raise ValueError(
                    f"Column {self.metric_eval_period.value} not found in {self.donor_stats_file}."
                )
            else:
                # Filter the DataFrame based on the evaluation period
                df = df[
                    df[self.metric_eval_period.col_name]
                    == self.metric_eval_period.value
                ]
        else:
            logger.warning(
                "No evaluation period provided. Using all periods in {self.donor_stats_file}."
            )

        # filter based on metric thresholds
        for col, threshold in self.metric_threshold.items():
            if threshold.absolute:
                df[col] = df[col].abs()
            if threshold.min is not None:
                df = df[df[col] >= threshold.min]
            if threshold.max is not None:
                df = df[df[col] <= threshold.max]

        donors = df[self.id_name].unique().tolist()
        donor_cats = (
            df_cwt[df_cwt[self.id_name].isin(donors)][id_name].unique().tolist()
        )

        logger.info(
            f"Number of donors after filtering: {len(donors)} gages, {len(donor_cats)} catchments"
        )

        # check if any donors are left after filtering
        if not donors:
            logger.info(
                "No donors left after filtering. Check the metric thresholds and evaluation period."
            )

        return {"gage_id": donors, id_name: donor_cats}


class AttrDatasetConfig(BaseModel):
    """Configuration for attribute datasets used in the regionalization process."""

    attr_list: Optional[list] = None
    attr_select_file: Optional[Path | str] = None
    attr_data_file: Optional[Path | str] = None

    @model_validator(mode="after")
    def validate_either_field_exists(self):
        """Validate that at least one of 'attr_list' or 'attr_select_file' is provided."""
        if not self.attr_list and not self.attr_select_file:
            raise ValueError(
                "At least one of 'attr_list' or 'attr_select_file' must be provided."
                " If both are provided, 'attr_list' takes priority."
            )
        return self

    def _get_selected_attrs(self):
        """Private method to load the list of selected attributes."""
        # determine list of attributes to use from either attr_list or attr_select_file
        # if both are provided, attr_list takes priority
        if self.attr_list:
            # make sure attr_list is valid
            attrs1 = [
                x
                for x in self.attr_list
                if x not in pq.ParquetFile(self.attr_data_file).schema.names
            ]
            if attrs1:
                raise ValueError(
                    f"These attributes {attrs1} are not found in {self.attr_data_file}"
                )
        else:
            attr_select_path = Path(self.attr_select_file)
            if not attr_select_path.exists():
                raise FileNotFoundError(
                    f"Select file not found: {self.attr_select_file}"
                )

            df_attrs = pd.read_csv(attr_select_path)

            if "select" not in df_attrs.columns or "attr_name" not in df_attrs.columns:
                raise ValueError(
                    f"Missing required columns 'select' and/or 'attr_name' in file: {self.attr_select_file}"
                )

            self.attr_list = df_attrs[df_attrs["select"] == 1]["attr_name"].to_list()

    def get_attr_data(self, id_name: str = "divide_id") -> pd.DataFrame:
        """Load attribute data filtered by selected attributes."""
        self._get_selected_attrs()

        if not self.attr_data_file:
            raise FileNotFoundError("No attr_data_file provided.")

        attr_data_path = Path(self.attr_data_file)
        if not attr_data_path.exists():
            raise FileNotFoundError(
                f"Attribute data file not found: {self.attr_data_file}"
            )

        suffix = attr_data_path.suffix.lower()
        if suffix == ".csv":
            df_data = pd.read_csv(attr_data_path)
        elif suffix == ".parquet":
            df_data = pd.read_parquet(attr_data_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        missing_cols = set(self.attr_list) - set(df_data.columns)
        if missing_cols:
            raise ValueError(f"Missing attributes in data file: {missing_cols}")

        return df_data[[id_name] + self.attr_list]


class AttrDatasets(BaseModel):
    """Configuration for attribute datasets that can be used in the regionalization process."""

    hlr: Optional[AttrDatasetConfig] = None
    ngen: Optional[AttrDatasetConfig] = None
    hydroatlas: Optional[AttrDatasetConfig] = None
    streamcat: Optional[AttrDatasetConfig] = None
    nhdplus: Optional[AttrDatasetConfig] = None
    camels: Optional[AttrDatasetConfig] = None


class OutputSection(BaseModel):
    """Output Manager."""

    save: bool
    path: Path | str
    format: Optional[str] = None
    plots: Optional[dict] = None

    @model_validator(mode="after")
    def check_format_if_dir(cls, values):
        """Check if path is a diretory. If so require a 'format'."""
        if not Path(values.path).suffix and not values.format:
            raise ValueError(
                f"'format' must be specified if 'path' is a directory: {Path(values.path)}"
            )

        return values

    def get_file_path(self, file_name: Optional[str] = None) -> Path:
        """Get the file path for saving the output."""
        file_path = Path(self.path)
        if file_name:
            file_path = file_path / file_name
        if not file_path.suffix and self.format:
            file_path = file_path.with_suffix(f".{self.format}")

        return file_path

    def save_data(self, data: Any, file_name: Optional[str] = None):
        """Save the data to the specified path and format."""
        if not self.save:
            return

        if not self.format:
            raise ValueError(
                f"'format' must be specified if 'save' is True: {self.path}"
            )

        file_path = self.get_file_path(file_name)

        save_data(data, file_path)


class OutputConfig(BaseModel):
    """Output Configueer."""

    pairs: OutputSection
    attr_data_final: OutputSection
    config_final: OutputSection
    spatial_distance: OutputSection


class AlgoGeneral(BaseModel):
    """General algorithm class."""

    min_snow_frac: float
    max_spa_dist: float
    max_attr_diff: Dict[str, float]
    n_donor_max: int
    min_var_pca: float


class Gower(AlgoGeneral):
    """Gower algorithm class."""

    min_attr_dist: float
    max_attr_dist: float
    min_spa_dist: float
    n_donor_max: int
    zero_spa_dist: float


class URF(AlgoGeneral):
    """Unsupervised Rand Forest (URF) algorithm class."""

    pca: bool
    n_trees: int
    max_depth: int
    min_attr_dist: float
    max_attr_dist: float
    min_spa_dist: float
    n_donor_max: int
    zero_spa_dist: float


class KMeans(AlgoGeneral):
    """K-means algorithm class."""

    n_donor_max: int
    n_iter_max: int
    init: str
    n_init: int


class KMedoids(AlgoGeneral):
    """K-medoids algorithm class."""

    n_donor_max: int
    n_iter_max: int
    init: str


class HDBSCAN(AlgoGeneral):
    """Hierarchical Density Based Spatial Clustering of Applications with Noise (HDBSCAN) algorithm class."""

    n_donor_max: int
    min_cluster_size: int


class Birch(AlgoGeneral):
    """Balanced Iterative Reducing and Clustering using Hierarchies (BIRCH) algorithm class."""

    n_donor_max: int
    branching_factor: int
    min_thresh: float
    max_thresh: float
    max_resample: int


class AlgorithmConfig(BaseModel):
    """Algorithm configuration class."""

    general: AlgoGeneral
    gower: Optional[Gower] = None
    urf: Optional[URF] = None
    kmeans: Optional[KMeans] = None
    kmedoids: Optional[KMedoids] = None
    hdbscan: Optional[HDBSCAN] = None
    birch: Optional[Birch] = None


class Config(BaseModel):
    """Configuration class."""

    general: GeneralConfig
    donor: DonorConfig
    attr_datasets: AttrDatasets
    output: OutputConfig
    algorithms: AlgorithmConfig

    @model_validator(mode="after")
    def check_required_algorithms_present(self):
        """Check if required algorithms are present."""
        required = set(self.general.algorithm_list)
        defined = set(self.algorithms.model_dump(exclude_unset=True).keys())

        missing = required - defined
        if missing:
            raise ValueError(
                f"The following algorithms are listed in 'general.algorithm_list' "
                f"but missing from the 'algorithms' section: {missing}"
            )
        return self

    @model_validator(mode="after")
    def check_required_attr_datasets_present(self):
        """Check that the required attributes are present."""
        required = set(self.general.attr_dataset_list)
        defined = set(self.attr_datasets.model_dump(exclude_unset=True).keys())

        missing = required - defined
        if missing:
            raise ValueError(
                f"The following attribute datasets are listed in 'general.attr_dataset_list' "
                f"but missing from the 'attr_datasets' section: {missing}"
            )
        return self
