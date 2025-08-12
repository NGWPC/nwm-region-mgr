"""Configuration schema for the formulation regionalization application."""

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator
from utils import (
    BaseConfig,
    BaseGeneralConfig,
    check_options,
)

logger = logging.getLogger(__name__)


class FormulationGeneralSettings(BaseGeneralConfig):
    """General settings for the formulation regionalization application."""

    huc12_hydrofabric_file: Optional[Union[str, Path]] = None
    """Path to HUC12 hydrofabric file containing HUC12 polygons for spatial discretization."""
    divide_huc12_cwt_file: Optional[str] = None
    """Path to crosswalk file between HUC12 basins and NextGen catchments, with columns 'divide_id' and 'huc_12'."""

    calib_basins_only: Optional[bool] = False
    """Whether to run formulation selection only for calibrated basins (based on summary score)."""
    formulation_to_include: Optional[List[str]] = None
    """List of formulations to consider. If None, all formulations are included."""
    """If 'all', all formulations are included."""
    formulation_to_exclude: Optional[List[str]] = None
    """List of formulations to exclude. If None, no formulations are excluded."""
    consider_cost: Optional[bool] = False
    """Whether to consider computational costs of formulations in the regionalization process."""

    @model_validator(mode="after")
    def check_approach_calib_basins(self) -> "FormulationGeneralSettings":
        """Ensure that the approach for assigning formulation to calibrated basins is valid."""
        valid_approaches = ["regionalization", "summary_score"]
        check_options(self.approach_calib_basins, valid_approaches, "approach_calib_basins")

        return self


class BestFormulation(BaseModel):
    """Configuration for determining the best formulation for each spatial unit."""

    method: str
    """Method to determine the best formulation, options: 'total_score', 'total_count'."""
    type: str
    """Type of spatial unit for best formulation, options: 'basin', 'divide'."""
    tolerance: float = Field(default=0.05, ge=0.0, le=1.0)
    """Score tolerance as a fraction of the best score, must be between 0.0 and 1.0."""

    @model_validator(mode="after")
    def check_method_and_type(self) -> "BestFormulation":
        """Ensure that the method and type for best formulation are valid."""
        valid_methods = ["total_score", "total_count"]
        valid_types = ["basin", "divide"]

        check_options(self.method, valid_methods, "best_formulation method")
        check_options(self.type, valid_types, "best_formulation type")

        return self


class FormulationSpatialUnitConfig(BaseModel):
    """Spatial discretization settings for formulation regionalization."""

    huc_level: Optional[str] = "huc-8"
    """USGS HUC level used for discretization, e.g., 'huc-8'."""
    nmin_calib_basin: Optional[int] = 5
    """Minimum number of calibration basins required per spatial unit to consider it valid."""
    basin_fill_method: Optional[str] = "upscaling"
    """Method to handle units with too few calibration basins. Options: 'upscaling', 'nearest-neighbor'."""
    best_formulation: BestFormulation
    """Strategy to determine the best formulation for each spatial unit."""

    @model_validator(mode="after")
    def check_huc_level(self) -> "FormulationSpatialUnitConfig":
        """Ensure that the HUC level is valid."""
        valid_huc_levels = ["huc-2", "huc-4", "huc-6", "huc-8", "huc-10", "huc-12"]
        valid_huc_levels = (
            valid_huc_levels
            + [level.replace("-", "_") for level in valid_huc_levels]
            + [level.replace("-", "") for level in valid_huc_levels]
        )
        check_options(self.huc_level.lower(), valid_huc_levels, "huc_level")

        return self

    @model_validator(mode="after")
    def check_basin_fill_method(self) -> "FormulationSpatialUnitConfig":
        """Ensure that the basin fill method is valid."""
        valid_methods = ["upscaling", "nearest-neighbor"]
        check_options(self.basin_fill_method.lower(), valid_methods, "basin_fill_method")

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

    weight: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    """Weight of the metric in the summary score, must be between 0.0 and 1.0."""

    absolute: Optional[bool] = Field(default=False)
    """Whether to use the absolute value of the metric for normalization, default is False."""


class MetricEvalPeriod(BaseModel):
    """Configuration for the evaluation period of metrics to be used for screening donors."""

    col_name: str
    """Name of the column in the donor stats file that contains the evaluation period."""

    value: str
    """Value of the evaluation period to filter the donor stats file."""


class FormulationSummaryScoreConfig(BaseModel):
    """Configuration for computing a summary score for formulation as a weighted average of normalized metrics."""

    metric_eval_period: Optional[MetricEvalPeriod] = None
    """Optional: evaluation period of metrics to be used for screening donors."""

    metrics: Dict[str, MetricConfig] = Field()
    """Dictionary of metrics used in the summary score, keyed by metric name."""

    @model_validator(mode="after")
    def remove_zero_weighted_metrics(self) -> "FormulationSummaryScoreConfig":
        """Remove metrics with a weight of 0.0 from the configuration.

        Returns:
            A new FormulationSummaryScoreConfig instance with zero-weighted metrics removed.

        """
        active_metrics = {name: metric for name, metric in self.metrics.items() if metric.weight > 0.0}
        missing_metrics = set(self.metrics) - set(active_metrics)
        if missing_metrics:
            logger.debug(
                f"Removed metrics with zero weight: {', '.join(missing_metrics)}. "
                "These metrics will not contribute to the summary score."
            )

        self.metrics = active_metrics

        return self

    @model_validator(mode="after")
    def validate_all_metrics(self) -> "FormulationSummaryScoreConfig":
        """Ensure that all metrics have valid bounds and weights."""
        for name, metric in self.metrics.items():
            if metric.upper is not None and metric.lower is not None and metric.upper <= metric.lower:
                msg = f"Invalid bounds for metric '{name}': upper={metric.upper}, lower={metric.lower}"
                logger.error(msg)
                raise ValueError(msg)

            if metric.weight is not None and (metric.weight < 0.0 or metric.weight > 1.0):
                msg = f"Invalid weight for metric '{name}': {metric.weight}. Must be between 0.0 and 1.0."
                logger.error(msg)
                raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def check_weights_sum_to_one(self) -> "FormulationSummaryScoreConfig":
        """Ensure that the sum of all metric weights equals 1.0."""
        total_weight = sum(metric.weight for metric in self.metrics.values())
        if abs(total_weight - 1.0) > 1e-6:
            msg = f"The sum of all metric weights must equal 1.0, but got {total_weight}"
            logger.error(msg)
            raise ValueError(msg)
        return self


class FormulationCostConfig(BaseModel):
    """Computational cost of each formulation."""

    file: Optional[str] = None
    """Path to CSV file with formulation costs. If provided, costs will be read from this file."""
    costs: Optional[Dict[str, float]] = None
    """Dictionary of formulation costs, keyed by formulation name. If `file` is provided, this is ignored."""


class Config(BaseConfig):
    """Top-level configuration for formulation regionalization."""

    general: FormulationGeneralSettings
    """General settings for the formulation regionalization application."""
    spatial_unit: FormulationSpatialUnitConfig
    """Spatial discretization settings for the application."""
    summary_score: FormulationSummaryScoreConfig
    """Summary score computation configuration for the application."""
    formulation_cost: FormulationCostConfig
    """Computational cost configuration for each formulation."""
