"""Select formulations for regionalization.

This module provides functions to select formulations based on summary scores of calibrated basins,
as well as formulation costs if provided in the configuration.

Functions:
- find_calibration_gages: Find gages for a given HUC ID in the summary scores DataFrame.
- get_formulation_costs: Retrieve formulation costs from the configuration.
- compute_total_score: Compute total score for each spatial unit based on the method specified.
- select_formulation_given_score_cost: Select formulations based on summary scores and costs.
- select_formulation: head function to select formulations for each spatial unit in the VPU.

"""

import logging
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from utils import check_columns, read_table

from . import config_schema as cs

logger = logging.getLogger(__name__)


def _find_calibration_gages(huc_id: str, df: pd.DataFrame, min_gages: int) -> tuple[list, str]:
    """Find gages for the given HUC ID in the DataFrame.

    Args:
        huc_id (str): HUC ID to find gages for.
        df (pd.DataFrame): DataFrame of summary scores.
        min_gages (int): Minimum number of gages required for each spatial unit.

    Returns:
        tuple: A tuple containing a list of calibration gage IDs found for the HUC ID and the HUC level.

    """
    # define valid HUC levels
    valid_huc_levels = ["huc2", "huc4", "huc6", "huc8", "huc10", "huc12"]
    valid_huc_levels.reverse()

    # make sure current huc level is in the valid HUC levels
    current_huc_level = "huc" + str(len(huc_id))
    if current_huc_level not in valid_huc_levels:
        raise ValueError(f"Invalid current HUC level: {current_huc_level}. Valid levels are: {valid_huc_levels}")

    # start from current huc level, loop through valid HUC levels to ensure sufficient calibrated gages
    for i, huc_level in enumerate(valid_huc_levels[valid_huc_levels.index(current_huc_level) :]):
        # count the number of unique gages in the new HUC level
        huc_digit = int(huc_level.replace("huc", ""))
        ngage = df[df["huc_id"].str[:huc_digit] == huc_id[:huc_digit]]["gage_id"].nunique()

        # if the number of gages is sufficient, select the new HUC level
        if ngage >= min_gages:
            df_huc = df[df["huc_id"].str[:huc_digit] == huc_id[:huc_digit]].copy()
            gages = df_huc["gage_id"].unique().tolist()

            # remove NaN values from gages
            gages = [gage for gage in gages if pd.notna(gage)]

            if huc_level != current_huc_level:
                logger.debug(
                    f"{huc_id}: upscaled HUC level from {current_huc_level} to {huc_level} "
                    f"and found {len(gages)} gages."
                )
            else:
                logger.debug(f"{huc_id}: found {len(gages)} gages at {huc_level} level.")

            break
    else:
        raise ValueError(
            f"Not enough calibrated gages at {huc_level} level for {len(df_huc)} catchments. Found {ngage} gages, "
            f"minimum required is {min_gages}."
        )

    return gages, huc_level


def _get_formulation_costs(config: cs.FormulationCostConfig) -> Optional[dict[str, float]]:
    """Get formulation costs from the configuration.

    Args:
        config : cs.FormulationCostConfig
            Configuration object containing formulation cost settings.

    Returns:
        Optional[dict[str, float]]
            Dictionary of formulation costs, keyed by formulation name. If no costs are defined, returns None.

    """
    if config.file:
        # check "formulation" and "cost" columns in the cost file
        check_columns(
            config.file,
            columns=["formulation", "cost"],
        )
        # read the cost file
        cost_df = read_table(config.file)
        if not cost_df.empty:
            return dict(zip(cost_df["formulation"], cost_df["cost"]))
        else:
            logger.warning(f"No costs found in the file: {config.file}. Returning None.")
            return None
    elif config.costs:
        return config.costs
    else:
        logger.warning("No formulation costs defined in the configuration. Returning None.")

    return None


def _compute_total_score(
    df: pd.DataFrame,
    method: str = "basin",
) -> pd.DataFrame:
    """Compute total score for each spatial unit based on the method specified.

    Args:
        df : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        method : str, optional
            Method to compute total score, either 'basin' or 'divide', by default 'basin'.

    Returns:
        pd.DataFrame
            DataFrame with total scores computed for each spatial unit.

    """
    col1 = "gage_id" if method == "basin" and "gage_id" in df.columns else "divide_id"

    df1 = df[[col1, "formulation", "summary_score"]].copy()

    # remove duplicate rows
    df1 = df1.drop_duplicates(subset=[col1, "formulation"])

    # drop rows with NaN values in the summary_score column
    df1 = df1.dropna(subset=["summary_score"])

    # drop col1
    df1 = df1.drop(columns=[col1])

    # count the values in the formulation column
    if df1["formulation"].value_counts().nunique() > 1:
        raise ValueError("Not all formulations have the same number of entries.")

    # compute total score for each formulation
    df1["total_score"] = df1.groupby(["formulation"])["summary_score"].transform("sum")

    # drop the summary_score column
    df1 = df1.drop(columns=["summary_score"])

    # remove duplicate rows
    df1 = df1.drop_duplicates(subset=["formulation", "total_score"])

    return df1


def _select_formulation_given_score_cost(
    df_score: pd.DataFrame,
    score_tolerance: float,
    cost_dict: Optional[dict] = None,
    method: str = "basin",
) -> pd.DataFrame:
    """Select formulations based on summary scores and costs.

    Args:
        df_score : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        score_tolerance : float
            Tolerance for the summary score to consider formulations as equally good.
        cost_dict : dict, optional
            Dictionary containing costs for each formulation, by default None.
        method : str, optional
            Method to compute total score, either 'basin' or 'divide', by default 'basin'.

    Returns:
        pd.DataFrame
            DataFrame with selected formulations and their scores.

    """
    # compute total score for each formulation
    df_total = _compute_total_score(df_score, method=method)

    # get the best formulation based on total scores
    max_score = df_total["total_score"].max()
    df_best = df_total[df_total["total_score"] == max_score].copy()
    df_best["cost"] = None  # Initialize cost column

    # if cost_dict is provided, filter the formulations based on the cost threshold
    if cost_dict is not None:
        df_score1 = df_total[df_total["total_score"] >= max_score - max_score * score_tolerance].copy()

        # check if all formulations are in the cost_dict
        if not df_score1["formulation"].isin(cost_dict.keys()).all():
            logger.warning("Not all formulations have associated costs. Filtering out those without costs.")
            df_score1 = df_score1[df_score1["formulation"].isin(cost_dict.keys())]

        # map costs to the formulations
        df_score1["cost"] = df_score1["formulation"].map(cost_dict)

        # select the best formulation based on the cost
        min_cost = df_score1["cost"].min()
        df_best = df_score1[df_score1["cost"] == min_cost]

    return df_best


def select_formulation(
    config: cs.Config,
    vpu: str,
    df_score: pd.DataFrame,
) -> pd.DataFrame:
    """Head function to select formulations for each spatial unit in the VPU.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            Virtual Planning Unit (VPU) for which to select formulations.
        df_score : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.

    Returns:
        pd.DataFrame
            DataFrame with selected formulations and their scores.

    """
    # crosswalk for gage/divide
    cwt_divide_gage = read_table(config.general.gage_divide_cwt_file, dtype={"gage_id": str, "divide_id": str})

    # crosswalk for divide/huc12
    cwt_divide_huc12 = read_table(config.spatial_unit.crosswalk_file, dtype={"divide_id": str, "huc12": str})

    # filter cwt_divide_gage for the current vpu
    cwt_divide_huc12["vpuid"] = cwt_divide_huc12["huc12"].str[:2]
    cwt_divide_huc12 = cwt_divide_huc12[cwt_divide_huc12["vpuid"] == vpu].copy()

    # get spatial units for formulation selection
    huc_level = config.spatial_unit.huc_level.lower().replace("-", "").replace("_", "")
    huc_digit = int(huc_level.replace("huc", ""))

    # add huc_id column to cwt_divide_huc12 based on huc_digit
    cwt_divide_huc12["huc_id"] = cwt_divide_huc12["huc12"].str[:huc_digit]

    # merge the two crosswalks first
    df = cwt_divide_huc12[["huc_id", "huc12", "divide_id"]].merge(
        cwt_divide_gage[["gage_id", "divide_id"]].drop_duplicates(),
        on="divide_id",
        how="left",
    )

    # then merge with the score DataFrame
    df_score = df_score.merge(df, on="gage_id", how="right")

    logger.info(
        f"Selecting formulations for VPU {vpu} at {huc_level} level. "
        f"There are {len(df_score['huc_id'].unique())} unique {huc_level} IDs."
    )

    # get formulation costs from the configuration
    formulation_costs = _get_formulation_costs(config.formulation_cost)

    # loop through each unique huc_id and select formulations
    df_selected = pd.DataFrame()
    for huc_id in df_score["huc_id"].unique():
        # find calibration gages for the current huc_id
        df_score_huc = df_score[~df_score["formulation"].isna() & ~df_score["summary_score"].isna()].copy()
        if df_score_huc.empty:
            logger.warning(f"No valid formulation scores found for HUC ID: {huc_id}. Skipping this HUC.")
            continue

        gages, huc_level = _find_calibration_gages(huc_id, df_score_huc, config.spatial_unit.nmin_calib_basin)
        if not gages:
            logger.warning(f"No gages found for HUC ID: {huc_id}. Skipping this HUC.")
            continue

        df_huc = df_score[df_score["gage_id"].isin(gages)].copy()

        # select the best formulation based on the score & optionally costs
        method = config.spatial_unit.total_score_method.lower()
        logger.info(f"Computing total score using method: {method}")
        best_formulation = _select_formulation_given_score_cost(
            df_huc,
            score_tolerance=config.formulation_cost.score_tolerance,
            cost_dict=formulation_costs,
            method=method,
        )

        # append the selected formulation to the list
        if best_formulation.empty:
            logger.warning(f"No valid formulations found for HUC ID: {huc_id}. Skipping this HUC.")
            continue

        # add huc_id, huc_level, number of gages and vpu to the best formulation
        best_formulation["huc_id"] = huc_id
        best_formulation["upscale_huc"] = huc_level
        best_formulation["num_gages"] = len(gages)
        best_formulation["vpu"] = vpu

        df_selected = pd.concat([df_selected, best_formulation], ignore_index=True)

    # rearrange the columns in the selected DataFrame
    df_selected = df_selected[
        [
            "vpu",
            "huc_id",
            "formulation",
            "total_score",
            "cost",
            "upscale_huc",
            "num_gages",
        ]
    ]

    # save the selected formulations to the output file
    cc = config.output.formulation
    cc.save_to_file(df_selected, vpu=vpu, data_str="Formulation Selection")

    # generate spatial map plots if enabled
    if any(cc.plot.values()):
        # merge with cwt_divide_huc12 to get the divide_id
        df_selected = df_selected.merge(
            cwt_divide_huc12[["huc_id", "divide_id"]].drop_duplicates(),
            on="huc_id",
            how="left",
        )

        # get geometry for divides if spatial map is enabled
        if cc.plot.get("spatial_map", False):
            # read the geometry file
            geo_file = Path(config.general.hydrofabric_file[vpu]).resolve(strict=True)
            if not geo_file.exists():
                logger.warning(f"Geometry file {geo_file} does not exist. Skipping spatial map plot.")
                return
            gdf = gpd.read_file(geo_file)
            if gdf.empty:
                logger.warning(f"Geometry file {geo_file} is empty. Skipping spatial map plot.")
                return

            # merge the geometry with the selected formulations
            df_selected = df_selected.merge(
                gdf[["divide_id", "geometry"]].drop_duplicates(),
                on="divide_id",
                how="left",
            )

            # convert df_selected to a real GeoDataFrame for plotting
            df_selected = gpd.GeoDataFrame(
                df_selected,
                geometry="geometry",
                crs=gdf.crs,
            )

        # plot the selected formulations
        plot_dict = {
            "vpu": vpu,
            "var_str": "Formulation Selection",
            "columns": ["formulation", "total_score", "cost"],
            "ncols": 3,
        }
        cc.plot_data(df_selected, plot_dict)

    return df_selected
