"""Configuration schema for the formulation regionalization application."""

import logging
import math
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Union

import geopandas as gpd
import pandas as pd
from pydantic import BaseModel, Field, model_validator
from utils import plot_histogram, plot_spatial_map, save_data

logger = logging.getLogger(__name__)


class GeneralSettings(BaseModel):
    """General settings for the formulation regionalization application."""

    run_name: str
    """Name of the run, used to create output folders and files."""
    domain: str
    """Define NWM domain. Options: conus, ak, hi, prvi."""
    vpu_list: Union[List[str], str]
    """List of VPUs within the domain or 'all' to process all."""
    catchments_to_exclude: Optional[Union[str, List[str]]] = None
    """List, 'all', or path to CSV with divide_id column to exclude from regionalization."""
    formulation_to_include: Optional[List[str]] = None
    """List of formulations to consider. If None, all formulations are included."""
    """If 'all', all formulations are included."""
    formulation_to_exclude: Optional[List[str]] = None
    """List of formulations to exclude. If None, no formulations are excluded."""
    base_dir: str
    """Path to base directory for input/output files."""
    id_name: str = "divide_id"
    """Name of the column containing the unique identifier for each catchment."""
    hydrofabric_file: Path | str | Dict[str, Path] | Dict[str, str] = Field()
    """Path to hydrofabric file, e.g., vpu_divides.gpkg."""
    gage_divide_cwt_file: Optional[str] = None
    """Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'."""
    consider_cost: Optional[bool] = False
    """Whether to consider computational costs of formulations in the regionalization process."""
    approach_calib_basins: Optional[str] = "regionalization"  # Options: 'regionalization', 'calval_stat'
    """Strategy for assigning formulations to calibrated basins."""
    donor_gage_file: Optional[str] = None
    """Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'."""
    gage_divide_cwt_file: Optional[str] = None
    """Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'."""
    consider_cost: Optional[bool] = False
    """Whether to consider computational costs of formulations in the regionalization process."""
    approach_calib_basins: Optional[str] = "regionalization"  # Options: 'regionalization', 'calval_stat'
    """Strategy for assigning formulations to calibrated basins."""
    donor_gage_file: Optional[str] = None
    """Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'."""
    huc12_shape_file: Optional[Union[str, Path]] = None
    """Path to HUC12 shape file or GeoPackage containing HUC12 polygons for spatial discretization."""


class PlotsConfig(BaseModel):
    """Configuration for output plots."""

    spatial_map: Optional[bool] = True
    """Whether to generate spatial maps of formulations."""
    histogram: Optional[bool] = True
    """Whether to generate histograms of formulation distributions."""


class SpatialUnitConfig(BaseModel):
    """Spatial discretization settings."""

    huc_level: Optional[str] = "huc-8"
    """USGS HUC level used for discretization, e.g., 'huc-8'."""
    crosswalk_file: str
    """Path to crosswalk file between HUC-12 basins and NextGen catchments, with columns 'divide_id' and 'huc_12'."""
    nmin_calib_basin: Optional[int] = 5
    """Minimum number of calibration basins required per spatial unit to consider it valid."""
    basin_fill_method: Optional[str] = "upscaling"
    """Method to handle units with too few calibration basins. Options: 'upscaling', 'nearest-neighbor'."""
    best_formulation: Optional[Dict[str, Union[str, float]]] = {
        "method": "total_score",
        "type": "divide",
        "tolerance": 0.05,
    }
    """Method, type, and score tolerance to determine the best formulation for each spatial unit."""

    @model_validator(mode="after")
    def check_huc_level(self) -> "SpatialUnitConfig":
        """Ensure that the HUC level is valid."""
        valid_huc_levels = ["huc-2", "huc-4", "huc-6", "huc-8", "huc-10", "huc-12"]
        valid_huc_levels = (
            valid_huc_levels
            + [level.replace("-", "_") for level in valid_huc_levels]
            + [level.replace("-", "") for level in valid_huc_levels]
        )
        if self.huc_level.lower() not in valid_huc_levels:
            raise ValueError(f"Invalid HUC level: {self.huc_level}. Valid options are: {valid_huc_levels}")

        return self

    @model_validator(mode="after")
    def check_basin_fill_method(self) -> "SpatialUnitConfig":
        """Ensure that the basin fill method is valid."""
        valid_methods = ["upscaling", "nearest-neighbor"]
        if self.basin_fill_method not in valid_methods:
            raise ValueError(f"Invalid basin fill method: {self.basin_fill_method}. Valid options are: {valid_methods}")

        return self

    @model_validator(mode="after")
    def check_best_formulation(self) -> "SpatialUnitConfig":
        """Ensure that the best formulation method and type are valid."""
        # make sure best_formulation is a dict with keys 'method', 'type', and 'tolerance'
        if (
            not isinstance(self.best_formulation, dict)
            or "method" not in self.best_formulation
            or "type" not in self.best_formulation
            or "tolerance" not in self.best_formulation
        ):
            raise ValueError(
                f"best_formulation must be a dictionary with keys 'method', 'type', and 'tolerance'. "
                f"Got: {self.best_formulation}"
            )

        valid_methods = ["total_score", "total_count"]
        valid_types = ["basin", "divide"]

        if self.best_formulation["method"] not in valid_methods:
            raise ValueError(
                f"Invalid best formulation method: {self.best_formulation['method']}. "
                f"Valid options are: {valid_methods}"
            )

        if self.best_formulation["type"] not in valid_types:
            raise ValueError(
                f"Invalid best formulation type: {self.best_formulation['type']}. Valid options are: {valid_types}"
            )

        """Ensure that score tolerance is a valid value."""
        if not (0.0 <= self.best_formulation["tolerance"] <= 1.0):
            raise ValueError(
                f"Score tolerance (i.e., fraction of best score) must be between 0.0 and 1.0, "
                f"got {self.best_formulation['tolerance']}"
            )

        return self


class Orientation(str, Enum):
    """Orientation for metrics: 'positive' means higher is better, 'negative' means lower is better."""

    positive = "positive"
    negative = "negative"


class MetricConfig(BaseModel):
    """Configuration for an individual metric used in summary scoring."""

    upper: Optional[float] = Field(default=None)
    """Upper bound for scaling and normalization, must be greater than lower bound."""

    lower: Optional[float] = Field(default=None)
    """Lower bound for scaling and normalization, must be less than upper bound."""

    orientation: Optional[Orientation] = Field(default=Orientation.positive)
    """Orientation of the metric, either 'positive' or 'negative'."""

    weight: Annotated[float, Field(ge=0.0, le=1.0)] = Field(default=0.0)
    """Weight of the metric in the summary score, must be between 0.0 and 1.0."""

    @model_validator(mode="after")
    def check_bounds(self) -> "MetricConfig":
        """Ensure that upper bound is greater than lower bound."""
        if self.upper is not None and self.lower is not None and self.upper <= self.lower:
            raise ValueError(f"'lower' must be smaller than 'upper' (got upper={self.upper}, lower={self.lower})")

        return self

    def _scale_value(self, value: float) -> float:
        """Scale a value based on the metric's bounds.

        Args:
            value: The value to scale.

        Returns:
            Scaled value between 0.0 and 1.0.

        """
        return max(self.lower, min(value, self.upper))

    def normalize_value(self, value: float) -> float:
        """Normalize a value based on the metric's bounds and orientation.

        Args:
            value: The value to normalize.

        Returns:
            Normalized value between 0.0 and 1.0.

        """
        # make sure value is not nan or inf
        if value is None or not math.isfinite(value):
            raise ValueError(f"Invalid value for normalization: {value}")

        # scale value to be within bounds
        value = self._scale_value(value)

        # normalize based on orientation
        if self.orientation == Orientation.positive:
            normalized = (value - self.lower) / (self.upper - self.lower)
        else:
            normalized = (self.upper - value) / (self.upper - self.lower)

        return max(0.0, min(1.0, normalized))


class MetricEvalPeriod(BaseModel):
    """Configuration for the evaluation period of metrics to be used for screening donors."""

    col_name: str
    """Name of the column in the donor stats file that contains the evaluation period."""

    value: str
    """Value of the evaluation period to filter the donor stats file."""


class SummaryScoreConfig(BaseModel):
    """Configuration for computing a summary score as a weighted average of normalized metrics."""

    dir_stats: Union[str, Path]
    """Directory for calibration/validation stats parquet/csv files

    These files should have a specific naming convention: stat_calval_[formulation]_[domain]_vpu[vpu].parquet,
    e.g., stat_calval_nom-cfes_conus_vpu01.parquet, or stat_calval_nom-cfes_conus.parquet, 
    or stat_calval_nom-cfes_conus.csv
    """
    id_name: str = Field(default="gage_id")
    """Name of the column containing the unique identifier for each calibration basin."""

    metric_eval_period: Optional[MetricEvalPeriod] = None
    """Optional: evaluation period of metrics to be used for screening donors."""

    metrics: Dict[str, MetricConfig] = Field()
    """Dictionary of metrics used in the summary score, keyed by metric name."""

    @model_validator(mode="after")
    def check_weights_sum_to_one(self) -> "SummaryScoreConfig":
        """Ensure that the sum of all metric weights equals 1.0."""
        total_weight = sum(metric.weight for metric in self.metrics.values())
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"The sum of all metric weights must equal 1.0, but got {total_weight}")
        return self

    def get_active_metrics(self) -> Dict[str, MetricConfig]:
        """Get metrics that have a weight greater than 0.0.

        Returns:
            Dictionary of active metrics, keyed by metric name.

        """
        return {name: metric for name, metric in self.metrics.items() if metric.weight > 0.0}

    def _read_calval_stats(self, formulation: str, vpu: str) -> Dict[str, float]:
        """Read calibration/validation statistics for a specific formulation and VPU.

        Args:
            formulation: Name of the formulation.
            vpu: VPU identifier.

        Returns:
            Dictionary of metric values for the specified formulation and VPU.

        """
        # Construct the file path based on the naming convention
        file_path = Path(self.dir_stats) / f"stat_calval_{formulation}_{domain}_vpu{vpu}.parquet"
        if not file_path.exists():
            raise FileNotFoundError(f"Calibration/validation stats file not found: {file_path}")

        # Read the stats file (assuming it's in parquet format)
        import pandas as pd

        df = pd.read_parquet(file_path)

        # Convert to dictionary of metric values
        return df.set_index("metric_name")["value"].to_dict()

    def compute_summary_score(self, metric_values: Dict[str, float]) -> float:
        """Compute the summary score based on metric values.

        Args:
            metric_values: Dictionary of metric values, keyed by metric name.

        Returns:
            Summary score as a weighted average of normalized metrics.

        """
        score = 0.0
        for metric_name, metric in self.metrics.items():
            normalized_value = metric.normalize_value(metric_values.get(metric_name, math.nan))
            score += normalized_value * metric.weight
        return score


class FormulationCostConfig(BaseModel):
    """Computational cost of each formulation."""

    file: Optional[str] = None
    """Path to CSV file with formulation costs. If provided, costs will be read from this file."""
    costs: Optional[Dict[str, float]] = None
    """Dictionary of formulation costs, keyed by formulation name. If `file` is provided, this is ignored."""


class OutputSection(BaseModel):
    """Output Manager."""

    save: bool
    """Whether to save output files"""
    path: Path | str
    """Path to save output files. If a directory, the 'stem' and 'format' must be specified."""
    stem: Optional[str | Dict[str, str]] = None
    """File stem for output files, used to create unique file names based on the path."""
    format: Optional[str] = None
    """File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file."""
    plot: Optional[dict] = None
    """Configuration for output plots, if applicable."""
    plot_path: Optional[str] = None
    """Path to save output plots, if applicable."""

    @model_validator(mode="after")
    def check_format_if_dir(cls, values):
        """Check if path is a directory. If so require a 'format'."""
        if not Path(values.path).suffix and not values.format:
            raise ValueError(f"'format' must be specified if 'path' is a directory: {Path(values.path)}")

        return values

    def _get_file_path(self, vpu: str = None, plot_type: str = None) -> Path:
        """Get the file path for saving the output."""
        file_path = Path(self.path) if plot_type is None else Path(self.plot_path)

        # If the path is a directory, construct the file name using 'stem' and 'format'
        if not file_path.suffix:
            if not self.stem or not self.format:
                raise ValueError(f" File 'stem' and 'format' must be specified if 'path' is a directory: {file_path}")
            if isinstance(self.stem, dict):
                # If stem is a dict (for different VPUs), find the stem for current VPU
                file_stem = self.stem.get(f"{vpu}")
            else:
                # If stem is a string, use it directly
                file_stem = self.stem

            if not file_stem:
                raise ValueError(f"File stem not found for VPU {vpu}: {self.stem}")

            # make sure plot_type is supported
            if plot_type not in [None, "map", "hist"]:
                raise ValueError(f"Unsupported plot type: {plot_type}. Supported types are None, 'map', 'hist'.")

            file_format = self.format if plot_type is None else "png"
            file_prefix = "" if plot_type is None else f"{plot_type}_"

            # Construct the full file path
            file_path = file_path / f"{file_prefix}{file_stem}.{file_format}"

        # create the directory if it does not exist
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path

    def save_to_file(self, data: Any, vpu: str = None, data_str: str = None) -> None:
        """Save output data to the specified path and format.

        Args:
            data: Data to save, can be a DataFrame or Pydantic model.
            vpu: VPU identifier for the output file name.
            data_str: String representation of the data being saved.

        Raises:
            ValueError: If the output path is a directory and no file name is provided.

        """
        if not self.save:
            return

        # get the file path to save the output
        filepath = self._get_file_path(vpu)

        # save the output data
        save_data(data, filepath)
        if data_str is None:
            logger.info(f"Saved output to {filepath}")
        else:
            logger.info(f"Saved {data_str} output to {filepath}")

    def plot_data(
        self,
        data: pd.DataFrame | gpd.GeoDataFrame,
        plot_dict: Dict[str, Any],
    ) -> None:
        """Plot the data and save png to the specified path.

        Args:
            data: DataFrame or GeoDataFrame containing the data to plot.
            plot_dict: Dictionary containing plot configuration, including:
                var_str: String representation of the variable being plotted.
                columns: list of columns in the data to plot.
                vpu: VPU identifier for the output file name.
                plot_type: Type of plot being saved (e.g., 'map', 'hist').

        """
        if self.plot["histogram"]:
            path1 = self._get_file_path(plot_dict.get("vpu"), plot_type="hist")
            plot_dict1 = plot_dict.copy()
            plot_dict1["outfile"] = path1
            plot_dict1["ncols"] = 2

            # remove non-numeric columns from data from histogram plotting
            numeric_columns = data.select_dtypes(include=["number"]).columns.tolist()
            plot_dict1["columns"] = [col for col in plot_dict1.get("columns", []) if col in numeric_columns]

            plot_histogram(data, plot_dict1)

        if self.plot["spatial_map"]:
            path2 = self._get_file_path(plot_dict.get("vpu"), plot_type="map")
            plot_dict2 = plot_dict.copy()
            plot_dict2["outfile"] = path2
            plot_dict2["ncols"] = 3
            plot_spatial_map(data, plot_dict2)


class OutputConfig(BaseModel):
    """Output Configurer."""

    formulation: OutputSection
    """Output configuration for formulation regionalization results."""
    config_final: OutputSection
    """Output configuration for the final processed configuration file."""
    summary_score: OutputSection
    """Output configuration for summary score results."""


class Config(BaseModel):
    """Top-level configuration for formulation regionalization."""

    general: GeneralSettings
    """General settings for the formulation regionalization application."""
    output: OutputConfig
    """Output configuration for the application, including paths and formats for results."""
    spatial_unit: SpatialUnitConfig
    """Spatial discretization settings for the application."""
    summary_score: SummaryScoreConfig
    """Summary score computation configuration for the application."""
    formulation_cost: FormulationCostConfig
    """Computational cost configuration for each formulation."""
