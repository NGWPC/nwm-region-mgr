"""Process configuration for formreg.

This module provides functions to load, validate, and process the configuration for formulation regionalization.

Functions:
- process_config: Load and process the configuration file.
- get_formulations_from_stats: Extract formulation names from calibration and validation statistics file names.
- formulation_summary_score: Compute the summary score for each row in the DataFrame based on the configuration.
- compute_summary_score: Compute summary scores for each formulation from calibration and validation statistics.

"""

import glob
import logging
import re
from pathlib import Path
from typing import Dict

import geopandas as gpd
import numpy as np
import pandas as pd
from utils import check_columns_dataframe, read_table

from . import config_schema as cs

logger = logging.getLogger(__name__)


def get_formulations_from_stats(config: cs.Config, vpu: str) -> dict[str, Path]:
    """Extract formulation names from the calibration and validation statistics file names.

    Args:
        config: The configuration object.
        vpu: The VPU identifier.

    Returns:
        dict[str, Path]: A dictionary mapping formulation names to their statistics file paths.

    """
    # Find all statistics files (parquet or csv) for the given VPU
    dir_stats = Path(config.general.calval_stats_dir)

    # Pattern for VPU-specific files
    stats_files = glob.glob(f"{dir_stats}/stat_calval_*_{config.general.domain}_vpu{vpu}.parquet") + glob.glob(
        f"{dir_stats}/stat_calval_*_{config.general.domain}_vpu{vpu}.csv"
    )

    # Fallback: general domain-level files
    if not stats_files:
        stats_files = glob.glob(f"{dir_stats}/stat_calval_*_{config.general.domain}.parquet") + glob.glob(
            f"{dir_stats}/stat_calval_*_{config.general.domain}.csv"
        )

    if not stats_files:
        msg = f"No statistics files found for VPU {vpu} in {dir_stats}. Please check the configuration."
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Extract unique formulation names from the file names
    formulations = set()
    for file in stats_files:
        match = re.search(r"stat_calval_(.*?)_", file)
        if match:
            formulations.add(match.group(1))

    # narrow down to formulation_to_include (if provided in the config)
    forms1 = config.general.formulation_to_include
    if forms1:
        formulations = {form for form in formulations if form in forms1}
        forms_missing = forms1 - formulations
        if forms_missing:
            logger.warning(
                f"Formulations {', '.join(forms_missing)} not found in statistics files for "
                f"VPU {vpu} in {dir_stats}. Skipping them."
            )

    # exclude formulations_to_exclude (if provided in the config)
    if config.general.formulation_to_exclude:
        formulations = {form for form in formulations if form not in config.general.formulation_to_exclude}

    if not formulations:
        msg = (
            f"No valid formulations found in statistics files for VPU {vpu} in {dir_stats}. "
            "Please check the configuration and ensure that the statistics files contain the expected formulations."
        )
        logger.error(msg)
        raise ValueError(msg)

    # Convert formulations to a dictionary mapping to their statistics file paths
    dict_form = {
        form: Path([file for file in stats_files if form in file][0])  # Get the first matching file path
        for form in formulations
    }

    return dict_form


def formulation_summary_score(df: pd.DataFrame, dict_metrics: Dict[str, cs.MetricConfig]) -> None:
    """Compute the summary score for each row in the DataFrame based on the configuration.

    Args:
        df: DataFrame containing the metrics to compute the summary score.
        dict_metrics: Dictionary containing metric configurations.

    """
    # Check if the metrics dictionary is empty
    if not dict_metrics:
        msg = "No metrics defined in the configuration for summary score computation."
        logger.warning(msg)
        return

    # weights and orientations
    weights = {name: metric.weight for name, metric in dict_metrics.items()}
    orientations = {name: metric.orientation for name, metric in dict_metrics.items()}

    # Make sure weights sum to 1
    assert abs(sum(weights.values()) - 1.0) < 1e-6

    # Select the metric columns
    metrics = list(weights.keys())
    df_metrics = df[metrics].copy()

    # remove rows with NaN values in any of the metric columns
    df_metrics.dropna(subset=metrics, inplace=True)
    if df_metrics.empty:
        logger.warning("No valid data found after removing rows with NaN values in metric columns.")
        return

    # Normalize each column based on orientation
    for col in metrics:
        values = df_metrics[col]
        min_val, max_val = values.min(), values.max()

        # replace min and max with lower and upper bounds if provided
        if dict_metrics[col].lower is not None:
            min_val = dict_metrics[col].lower
        if dict_metrics[col].upper is not None:
            max_val = dict_metrics[col].upper

        # rescale the values to range [min_val, max_val]
        values = values.clip(lower=min_val, upper=max_val)

        if max_val == min_val:
            # Avoid division by zero
            df_metrics[col + "_norm"] = 0.0
            logger.warning(
                f"Column '{col}' has constant value {max_val}. Normalization will result in zero for all rows."
            )
        else:
            norm = (values - min_val) / (max_val - min_val)
            if orientations[col] == "negative":
                norm = 1 - norm
            df_metrics[col + "_norm"] = norm

    # Compute weighted average based on normalized metrics
    normalized_cols = [f"{m}_norm" for m in metrics]
    weight_array = np.array([weights[m] for m in metrics])
    df["summary_score"] = df_metrics[normalized_cols].dot(weight_array)

    return df


def compute_summary_score(config: cs.Config, vpu: str) -> None:
    """Compute summary scores for each formulation from calibration and validation statistics.

    Args:
        config: The configuration object.
        vpu: The VPU identifier.

    """
    # Get the VPU ID column name
    id_cols = config.general.id_col
    gage_id_col = id_cols["gage"].lower()
    divide_id_col = id_cols["divide"].lower()
    vpu_id_col = id_cols["vpu"].lower()

    # get the list of formulations from the statistics files
    dict_form = get_formulations_from_stats(config, vpu)

    # read statistics and compute summary scores for each formulation
    df_score = pd.DataFrame()
    for form, file in dict_form.items():
        # check if the required columns are present
        ss = config.summary_score
        vpu_id_col = config.general.id_col.get("vpu", "vpuid")
        required_columns = [gage_id_col, ss.metric_eval_period.col_name, vpu_id_col] + list(ss.metrics.keys())
        check_columns_dataframe(file, set(required_columns))

        # read the statistics file
        df_stats = read_table(file, {gage_id_col: str, vpu_id_col: str})
        if df_stats.empty:
            logger.warning(f"No data found in statistics file {file} for VPU {vpu} and formulation {form}")
            continue

        # narrow down to the VPU
        df_stats = df_stats[df_stats[vpu_id_col] == vpu]

        # narrow down to the evaluation period (case-insensitive)
        p1 = ss.metric_eval_period
        df_stats = df_stats[df_stats[p1.col_name].str.lower() == p1.value.lower()]

        # keep only the required columns
        df_stats = df_stats[required_columns]

        if not df_stats.empty:
            # compute the summary score for the formulation
            df = formulation_summary_score(df_stats, ss.metrics)
            df["formulation"] = form  # Add formulation name to the DataFrame
            df_score = pd.concat([df_score, df[[gage_id_col, "formulation", "summary_score"]]], ignore_index=True)

    logger.info(
        f"Computed summary scores for the following formulations for VPU {vpu}: {df_score['formulation'].unique()}"
    )

    # Save the summary score DataFrame
    cc = config.output["summary_score"]
    cc.save_to_file(df_score, vpu=vpu, data_str="Summary Score")

    # plot the summary score
    if any(cc.plots.values()):
        # create wide-format DataFrame for plotting
        df_score_wide = df_score.pivot(index=gage_id_col, columns="formulation", values="summary_score").reset_index()
        df_score_wide.columns.name = None

        if cc.plots.get("spatial_map", False):
            # read the crosswalk file
            cwt_file = Path(config.general.gage_divide_cwt_file).resolve(strict=True)
            if not cwt_file.exists():
                logger.warning(f"Crosswalk file {cwt_file} does not exist. Skipping spatial map plot.")
                return
            cwt_df = read_table(cwt_file, dtype={gage_id_col: str, divide_id_col: str})
            if cwt_df.empty:
                logger.warning(f"Crosswalk file {cwt_file} is empty. Skipping spatial map plot.")
                return
            # merge with summary score DataFrame
            df_score_wide = df_score_wide.merge(
                cwt_df[[gage_id_col, divide_id_col]],
                on=gage_id_col,
                how="left",
            )
            # read the geometry file
            geo_file = Path(config.general.ngen_hydrofabric_file[vpu])
            if not geo_file.exists():
                logger.warning(f"Geometry file {geo_file} does not exist. Skipping spatial map plot.")
                return
            gdf = gpd.read_file(geo_file)
            if gdf.empty:
                logger.warning(f"Geometry file {geo_file} is empty. Skipping spatial map plot.")
                return

            # merge geometry with summary score DataFrame
            df_score_wide = df_score_wide.merge(gdf[[divide_id_col, "geometry"]], on=divide_id_col, how="right")
            df_score_wide = gpd.GeoDataFrame(df_score_wide, geometry="geometry", crs=gdf.crs)

        # plot the summary score
        plot_dict = {
            "vpu": vpu,
            "var_str": "Summary Score",
            "columns": df_score["formulation"].unique().tolist(),
            "ncols": 3,
        }
        cc.plot_data(df_score_wide, plot_dict)

    return df_score
