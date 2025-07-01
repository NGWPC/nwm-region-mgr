"""Configuration schema for the formulation regionalization application."""

import math
from enum import Enum
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class GeneralSettings(BaseModel):
    """General settings for the formulation regionalization application.

    Attributes:
        run_name: Name of the run, used to create output folders and files.
        domain: Define NWM domain. Options: conus, ak, hi, prvi.
        vpu: List of VPUs within the domain or 'all' to process all.
        catchments_to_exclude: List, 'all', or path to CSV with divide_id column.
        formulation_to_include: List of formulations to consider.
        formulation_to_exlcude: List of formulations to exclude.
        base_dir: Path to base directory for input/output files.
        dir_stats: Directory for calibration/validation stats parquet/csv files.
        consider_cost: Whether to consider computational cost in selection.
        approach_calib_basins: Strategy for assigning formulations to calibrated basins.

    """

    run_name: str
    domain: str
    vpu: Union[List[str], str]
    catchments_to_exclude: Optional[Union[str, List[str]]] = None
    formulation_to_include: Optional[List[str]] = None
    formulation_to_exlcude: Optional[List[str]] = None
    base_dir: str
    dir_stats: str
    consider_cost: Optional[bool] = False
    approach_calib_basins: Optional[str] = "regionalization"  # Options: 'regionalization', 'calval_stat'


class PlotsConfig(BaseModel):
    """Configuration for output plots.

    Attributes:
        spatial_map: Whether to generate spatial maps of formulations.
        histogram: Whether to generate histograms of formulation distributions.

    """

    spatial_map: Optional[bool] = True
    histogram: Optional[bool] = True


class OutputConfig(BaseModel):
    """Output file and plot configuration.

    Attributes:
        path: Path to output directory.
        plots: Configuration for output plots, including spatial maps and histograms.
        If not provided, defaults to generating spatial maps and histograms.

    """

    path: str
    plots: PlotsConfig


class SpatialUnitConfig(BaseModel):
    """Spatial discretization settings.

    For each spatial unit, a single formulation will be identified and applied to all catchments within the unit.
    Special consideration may be given to calibrated catchments.

    Attributes:
        huc_level: USGS HUC level used for discretization (e.g., huc-8). Default is 'huc-8'.
        min_no_calib_basin: Minimum calibration basins required per unit. Default is 5.
        crosswalk_file: Path to CSV or parquet file with crosswalk between HUC-12 basins and NextGen catchments,
            with columns 'divide_id' and 'huc_12', respectively.
        basin_fill_method: How to handle units with too few calibration basins.

    """

    huc_level: Optional[str] = "huc-8"
    crosswalk_file: str
    min_no_calib_basin: Optional[int] = 5
    basin_fill_method: Optional[str] = "upscaling"


class Orientation(str, Enum):
    """Orientation for metrics: 'positive' means higher is better, 'negative' means lower is better."""

    positive = "positive"
    negative = "negative"


class MetricConfig(BaseModel):
    """Configuration for an individual metric used in summary scoring."""

    upper: float = Field()
    """Upper bound for scaling and normalization, must be greater than lower bound."""

    lower: float = Field()
    """Lower bound for scaling and normalization, must be less than upper bound."""

    orientation: Orientation = Field()
    """Orientation of the metric, either 'positive' or 'negative'."""

    weight: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    """Weight of the metric in the summary score, must be between 0.0 and 1.0."""

    @model_validator(mode="after")
    def check_bounds(self) -> "MetricConfig":
        """Ensure that upper bound is greater than lower bound."""
        if self.upper <= self.lower:
            raise ValueError(f"'upper' must be greater than 'lower' (got upper={self.upper}, lower={self.lower})")
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


class SummaryScoreConfig(BaseModel):
    """Configuration for computing a summary score as a weighted average of normalized metrics."""

    eval_period: Literal["calib", "valid", "full"] = Field(default="valid")
    """Evaluation period for the summary score."""

    metrics: Dict[str, MetricConfig] = Field()
    """Dictionary of metrics used in the summary score, keyed by metric name."""

    @model_validator(mode="after")
    def check_weights_sum_to_one(self) -> "SummaryScoreConfig":
        """Ensure that the sum of all metric weights equals 1.0."""
        total_weight = sum(metric.weight for metric in self.metrics.values())
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"The sum of all metric weights must equal 1.0, but got {total_weight}")
        return self

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
    """Computational cost of each formulation.

    Attributes:
        file: Path to CSV file with formulation costs.
        costs: Dictionary of formulation costs, keyed by formulation name. If `file` is provided, this is ignored.
        If `file` is not provided, this should be populated with costs for each formulation.

    """

    file: Optional[str] = None
    costs: Optional[Dict[str, float]] = None


class Config(BaseModel):
    """Top-level configuration for formulation regionalization.

    Attributes:
        general: General settings for the application.
        output: Output file and plot configuration.
        spatial_unit: Spatial discretization settings.
        summary_score: Summary score computation configuration.
        formulation_cost: Computational cost of each formulation.

    """

    general: GeneralSettings
    output: OutputConfig
    spatial_unit: SpatialUnitConfig
    summary_score: SummaryScoreConfig
    formulation_cost: FormulationCostConfig
