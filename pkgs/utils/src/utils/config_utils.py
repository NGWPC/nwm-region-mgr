"""Utility functions for loading and validating configuration files using Pydantic and YAML.

config_utils.py

Functions:
- _deep_merge_configs: Recursively merge two dictionaries, with values from dict #2 overwriting those in dict #1.
- _load_and_validate_config: Load a YAML file, validate its structure using Pydantic
- _substitute_placeholders: Substitute placeholders in the config with actual values.
- load_and_process_config: Load, validate, process, and save the configuration files.
- LoggingConfig: Pydantic model for logging configuration.
- BaseGeneralConfig: Pydantic model for general settings of the application.
- BaseOutputConfig: Pydantic model for output settings of the application.
- BaseConfig: Pydantic model for the base configuration of the application.

"""

import logging
import re
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import geopandas as gpd
import pandas as pd
import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from .io_utils import read_table, save_data
from .logging_utils import setup_logging
from .plot_utils import plot_histogram, plot_spatial_map
from .string_utils import recursive_substitute
from .validation_utils import check_columns_dataframe, check_columns_hydrofabric, check_options

logger = logging.getLogger(__name__)


class LoggingConfig(BaseModel):
    """Logging configuration for the application."""

    level: Optional[str] = "INFO"
    """Logging level, e.g., 'DEBUG', 'INFO', 'WARNING', 'SEVERE', 'FATAL'."""
    log_to_file: Optional[bool] = True
    """Whether to log to a file."""
    file: Optional[str] = None
    """Path to the log file. If not provided, logging will be to console only."""

    @model_validator(mode="after")
    def check_log_level(self) -> "LoggingConfig":
        """Ensure that the log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "SEVERE", "FATAL"]  # use standard Python log levels
        check_options(self.level.upper(), valid_levels, "log level")
        return self

    @model_validator(mode="after")
    def check_log_file(self) -> "LoggingConfig":
        """Ensure that the log file path is valid if logging to a file."""
        if self.log_to_file and not self.file:
            logger.error("If 'log_to_file' is True, 'file' must be specified.")

        return self


class BaseGeneralConfig(BaseModel):
    """Base general settings for the formulation regionalization application."""

    run_name: str
    """Name of the run, used to create output folders and files."""
    domain: str
    """Define NWM domain. Options: conus, ak, hi, prvi."""
    vpu_list: Union[List[str], str]
    """List of VPUs within the domain or 'all' to process all."""
    base_dir: str
    """Path to base directory for input/output files."""

    ngen_hydrofabric_file: Path | str | Dict[str, Path] | Dict[str, str] = Field()
    """Path to NextGen hydrofabric file, e.g., vpu_01.gpkg."""
    gage_divide_cwt_file: Path | str = Field()
    """Path to CSV or parquet file with gage divide CWTs, with columns 'divide_id' and 'gage_id'."""
    donor_gage_file: Path | str = Field()
    """Path to CSV file with donor gage information, including 'gage_id', 'longitude', and 'latitude'."""
    calval_stats_dir: Path | str = Field()
    """Path to directory with calibration/validation statistics files"""

    id_col: Optional[dict[str, str]] = Field(
        default_factory=lambda: {"divide": "divide_id", "gage": "gage_id", "huc12": "huc_12", "vpu": "vpuid"}
    )
    """Dictionary mapping column names for unique identifiers in all applicable files."""

    layer_name: Optional[dict[str, str]] = Field(
        default_factory=lambda: {
            "huc12": "WBDSnapshot_National",
            "ngen": "divides",
        }
    )
    """Dictionary mapping layer names for hydrofabric files."""

    logging: Optional[LoggingConfig] = None
    """Logging configuration for the application."""

    @model_validator(mode="after")
    def lower_case_ids(self) -> "BaseGeneralConfig":
        """Ensure that all ID columns are in lower case."""
        if self.id_col:
            self.id_col = {k.lower(): v.lower() for k, v in self.id_col.items()}

        if self.layer_name:
            self.layer_name = {k.lower(): v.lower() for k, v in self.layer_name.items()}

        return self


class BaseOutputConfig(BaseModel):
    """Base Output Manager."""

    save: bool
    """Whether to save output files"""
    path: Path | str
    """Path to save output files. If a directory, the 'stem' and 'format' must be specified."""
    stem: Optional[str | Dict[str, str]] = None
    """File stem for output files, used to create unique file names based on the path."""
    stem_suffix: Optional[str] = None
    """Suffix for the file stem, used to create unique file names based on the path for specific needs."""
    format: Optional[str] = None
    """File format for output files, e.g., 'parquet', 'csv', 'yaml'. If not specified, the path must be a file."""
    plots: Optional[Dict[str, bool]] = None
    """Configuration for output plots, if applicable."""
    plot_path: Optional[str] = None
    """Path to save output plots, if applicable. If not specified, plots will be saved in the same directory 
    as the output files."""

    @model_validator(mode="after")
    def check_plot_path(cls, values):
        """Check if plot path is valid."""
        if not values.plot_path:
            values.plot_path = f"{values.path}/plots"
            logger.debug(f"Plot path not specified, using default: {values.plot_path}")

        return values

    @model_validator(mode="after")
    def check_format_if_dir(cls, values):
        """Check if path is a directory. If so require a 'format'."""
        if not Path(values.path).suffix and not values.format:
            msg = f"If 'path' is a directory, 'format' must be specified: {values.path}"
            logger.error(msg)
            raise ValueError(msg)

        return values

    @model_validator(mode="after")
    def check_plot_config(cls, values):
        """Check if plot configuration is valid."""
        if values.plots is not None:
            if not isinstance(values.plots, dict):
                msg = f"'plots' must be a dictionary, got {type(values.plots)}"
                logger.error(msg)
                raise ValueError(msg)
            # only "histogram" and "spatial_map" are supported, currently
            check_options(
                list(values.plots.keys()),
                ["histogram", "spatial_map"],
                "plot keys",
            )

        return values

    def _get_file_path(self, vpu: str = None, plot_type: str = None, use_stem_suffix: bool = False) -> Path:
        """Get the file path for saving the output."""
        file_path = Path(self.path) if plot_type is None else Path(self.plot_path)

        # If the path is a directory, construct the file name using 'stem' and 'format'
        if not file_path.suffix:
            if not self.stem or not self.format:
                msg = f"File 'stem' and 'format' must be specified if 'path' is a directory: {file_path}"
                logger.error(msg)
                raise ValueError(msg)
            if isinstance(self.stem, dict):
                # If stem is a dict (for different VPUs), find the stem for current VPU
                if vpu:
                    file_stem = self.stem.get(f"{vpu}")
                else:
                    file_stem = re.sub(r"_vpu.*$", "", next(iter(self.stem.values())))  # remove VPU part from stem
            elif isinstance(self.stem, str):
                file_stem = self.stem
            else:
                msg = f"Invalid 'stem' type: {type(self.stem)}. Must be str or dict."
                logger.error(msg)
                raise ValueError(msg)

            if not file_stem:
                msg = f"File stem not found for VPU {vpu}: {self.stem}"
                logger.error(msg)
                raise ValueError(msg)

            if use_stem_suffix:
                if not self.stem_suffix:
                    msg = f"File stem suffix not specified: {self.stem_suffix}"
                    logger.error(msg)
                    raise ValueError(msg)
                else:
                    file_stem += self.stem_suffix

            # make sure plot_type is supported
            if plot_type not in [None, "map", "hist"]:
                msg = f"Unsupported plot type: {plot_type}. Supported types are None, 'map', 'hist'."
                logger.error(msg)
                raise ValueError(msg)

            file_format = self.format if plot_type is None else "png"
            file_prefix = "" if plot_type is None else f"{plot_type}_"

            # Construct the full file path
            file_path = file_path / f"{file_prefix}{file_stem}.{file_format}"

        # create the directory if it does not exist
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path

    def save_to_file(self, data: Any, vpu: str = None, data_str: str = None, use_stem_suffix: bool = False) -> None:
        """Save output data to the specified path and format.

        Args:
            data: Data to save, can be a DataFrame or Pydantic model.
            vpu: VPU identifier for the output file name.
            data_str: String representation of the data being saved.
            use_stem_suffix: Whether to use the stem suffix for the file name.

        Raises:
            ValueError: If the output path is a directory and no file name is provided.

        """
        if not self.save:
            return

        # get the file path to save the output
        filepath = self._get_file_path(vpu, use_stem_suffix=use_stem_suffix)

        # save the output data
        save_data(data, filepath)
        if data_str is None:
            logger.info(f"Saved output to {filepath}")
        else:
            logger.info(f"Saved {data_str} output to {filepath}")

    def read_from_file(
        self, vpu: str = None, use_stem_suffix: bool = False, data_str: str = None, data_type: dict[str, Any] = None
    ) -> pd.DataFrame | gpd.GeoDataFrame:
        """Read output data from the specified path and format.

        Args:
            vpu: VPU identifier for the output file name.
            use_stem_suffix: Whether to use the stem suffix for the file name.
            data_str: String representation of the data being read.
            data_type: Optional dictionary specifying the data types for specific columns.

        Returns:
            DataFrame or GeoDataFrame containing the loaded data.

        Raises:
            FileNotFoundError: If the file does not exist.

        """
        # get the file path to read the output
        filepath = self._get_file_path(vpu, use_stem_suffix=use_stem_suffix)

        # read the output data
        data = read_table(filepath, dtype=data_type)

        if data_str is None:
            logger.info(f"Read output from {filepath}")
        else:
            logger.info(f"Read {data_str} output from {filepath}")

        return data

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
        if self.plots["histogram"]:
            path1 = self._get_file_path(plot_dict.get("vpu"), plot_type="hist")
            plot_dict1 = plot_dict.copy()
            plot_dict1["outfile"] = path1
            plot_dict1["ncols"] = 2

            # remove non-numeric columns from data from histogram plotting
            numeric_columns = data.select_dtypes(include=["number"]).columns.tolist()
            plot_dict1["columns"] = [col for col in plot_dict1.get("columns", []) if col in numeric_columns]

            plot_histogram(data, plot_dict1)

        if self.plots["spatial_map"]:
            path2 = self._get_file_path(plot_dict.get("vpu"), plot_type="map")
            plot_dict2 = plot_dict.copy()
            plot_dict2["outfile"] = path2
            plot_dict2["ncols"] = 3
            plot_spatial_map(data, plot_dict2)


class BaseConfig(BaseModel):
    """Base configuration for the application."""

    general: BaseGeneralConfig
    """Base general settings for the regionalization application."""

    output: dict[str, BaseOutputConfig]
    """Base output settings for the regionalization application."""


def _deep_merge_configs(a: dict, b: dict) -> dict:
    """Recursively merge two configuration dictionaries, with values from `b` overwriting those in `a`.

    Args:
        a: The base dictionary.
        b: The dictionary whose values will overwrite those in `a`.

    Returns:
        A new dictionary that is the result of merging `a` and `b`.

    """
    result = a.copy()
    for key, value in b.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def _load_and_validate_config(config_paths: list[str], config_schema: BaseModel = Field(...)) -> BaseModel:
    """Load a YAML file, validate its structure using Pydantic, and substitute placeholders in the config.

    Args:
        config_paths: list of paths to the config files
        config_schema: Pydantic model to validate the config structure

    Returns:
        Config object with validated structure

    """
    try:
        configs = []
        for p in config_paths:
            with open(p, "r") as f:
                configs.append(yaml.safe_load(f))
        merged_config = reduce(_deep_merge_configs, configs)
        config = config_schema(**merged_config)

        return config

    except ValidationError as e:
        logger.exception(f"Validation Error: {e}")
        raise
    except Exception as e:
        logger.exception(f"Error loading YAML file: {e}")
        raise


def _substitute_placeholders(config: BaseModel) -> BaseModel:
    """Substitute placeholders in the config with actual values.

    Args:
        config: Config object with placeholders

    Returns:
        Config object with placeholders substituted

    """
    # resolve placeholders in the config
    context = {
        "domain": config.general.domain,
        "run_name": config.general.run_name,
        "base_dir": config.general.base_dir,
        "vpu_list": config.general.vpu_list,
    }
    config = recursive_substitute(config, context)

    return config


def _validate_paths(paths: str | Path | list[str | Path]):
    """Validate that all file and directory paths exist.

    Args:
        paths: A string, Path, or list of strings/Paths to validate.

    Raises:
        FileNotFoundError: If any path does not exist.

    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    missing_paths = []
    for path in paths:
        if not Path(path).exists():
            missing_paths.append(Path(path))

    if missing_paths:
        msg = f"Missing paths: {missing_paths}"
        logger.error(msg)
        raise FileNotFoundError(msg)


def _check_file_columns(config: BaseModel):
    """Check if the required columns are present in the files in the configuration.

    Args:
        config: The configuration object to check.

    Raises:
        ValueError: If any required columns are missing in the files.

    """
    # get the ID columns and hydrofabric layer names from the configuration
    id_cols = config.general.id_col

    gage_id_col = id_cols["gage"] if "gage" in id_cols else None
    if not gage_id_col:
        msg = "Gage ID column is not defined in the configuration."
        logger.error(msg)
        raise ValueError(msg)

    divide_id_col = id_cols["divide"] if "divide" in id_cols else None
    if not divide_id_col:
        msg = "Divide ID column is not defined in the configuration."
        logger.error(msg)
        raise ValueError(msg)

    huc12_id_col = id_cols["huc12"] if "huc12" in id_cols else None
    if not huc12_id_col:
        msg = "HUC12 ID column is not defined in the configuration."
        logger.error(msg)
        raise ValueError(msg)

    vpu_id_col = id_cols["vpu"] if "vpu" in id_cols else None
    if not vpu_id_col:
        msg = "VPU ID column is not defined in the configuration."
        logger.error(msg)
        raise ValueError(msg)

    ngen_layer = config.general.layer_name["ngen"] if "ngen" in config.general.layer_name else None
    huc12_layer = config.general.layer_name["huc12"] if "huc12" in config.general.layer_name else None

    # NextGen hydrofabric file
    file = config.general.ngen_hydrofabric_file
    required_fields = {divide_id_col, vpu_id_col, "geometry"}
    if file is not None:
        if isinstance(file, dict):
            for vpu, f in file.items():
                config.general.layer_name["ngen"] = check_columns_hydrofabric(f, required_fields, layer_name=ngen_layer)

    # huc12 hydrofabric file
    file = config.general.huc12_hydrofabric_file
    required_fields = {huc12_id_col, "geometry"}
    if file is not None:
        config.general.layer_name["huc12"] = check_columns_hydrofabric(file, required_fields, layer_name=huc12_layer)

    # Gage divide CWT file
    file = config.general.gage_divide_cwt_file
    if file is not None:
        check_columns_dataframe(file, {divide_id_col, gage_id_col})

    # huc12 divide crosswalk file
    file = config.general.divide_huc12_cwt_file
    if file is not None:
        check_columns_dataframe(file, {divide_id_col, huc12_id_col})

    # Donor gage file
    file = config.general.donor_gage_file
    if file is not None:
        check_columns_dataframe(file, {gage_id_col, "longitude", "latitude"})


def load_and_process_config(
    config_paths: list[str],
    config_schema: BaseModel = Field(...),
) -> BaseModel:
    """Load, validate, and process the configuration files.

    Args:
        config_paths: List of paths to the config files.
        config_schema: Pydantic model to validate the config structure.

    Returns:
        Config object with validated structure and substituted placeholders.

    """
    # Load and validate the configuration
    config = _load_and_validate_config(config_paths, config_schema)

    # Substitute placeholders in the configuration
    config = _substitute_placeholders(config)

    # Set up logging based on the configuration
    log_level = config.general.logging.level.upper()
    log_file = Path(config.general.logging.file)
    setup_logging(
        level=log_level,
        target_packages=("__main__", "formreg", "utils"),
        log_file=log_file,
        file_level=log_level,
    )

    logger.info("Used config files: %s", config_paths)
    logger.info("Set up logging with level: %s, based on config file", log_level)
    logger.info("Log file: %s", log_file)

    # Validate that all paths in the configuration exist
    paths = [
        config.general.huc12_hydrofabric_file,
        config.general.gage_divide_cwt_file,
        config.general.divide_huc12_cwt_file,
        config.general.donor_gage_file,
        config.general.calval_stats_dir,
    ]
    paths.extend(config.general.ngen_hydrofabric_file.values())

    # remove None values from paths
    paths = [p for p in paths if p is not None]

    _validate_paths(paths)

    # Check if the required columns are present in the files
    _check_file_columns(config)

    logger.info("Successfully validated and processed the configuration.")

    # Save the final configuration
    cc = config.output["config_final"]
    cc.save_to_file(config, data_str="Final Configuration")

    return config
