"""Select formulations for regionalization.

This module provides functions to select formulations based on summary scores of calibrated basins,
as well as formulation costs if provided in the configuration.

Functions:
- _get_gages_with_shared_formulations: Identify the formulations shared by a number of gages.
- _find_gages_nearest_neighbor: Find gages for a given HUC ID using the nearest neighbor method.
- _find_gages_upscaling: Find gages for a given HUC ID using the upscaling method.
- _find_calibration_gages: Find gages for a given HUC ID in the summary scores DataFrame.
- _get_formulation_costs: Retrieve formulation costs from the configuration.
- _select_formulation_given_score: Select a formulation for each spatial unit based on the method specified.
- _identify_best_formulation_per_gage: Identify the best formulation for each gage based on summary scores and costs.
- select_formulation_donors_only: Select formulations for donor basins only.
- select_formulation_all: Select formulations for all basins.
- save_formulation_results: Save the formulation selection results to file.
- plot_formulation_results: Plot the formulation selection results.
- select_formulation: Head function to select formulations for each spatial unit in the VPU.

"""

import logging
from itertools import combinations
from pathlib import Path
from typing import List, Optional, Tuple

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
from utils import check_columns_dataframe, find_gages_within_buffer, read_table

from . import config_schema as cs

logger = logging.getLogger(__name__)


def _get_gages_with_shared_formulations(
    df: pd.DataFrame,
    min_gages: int = 3,
) -> Tuple[bool, List[str], List[str]]:
    """Identify the largest formulation set shared by at least `min_gages` gages.

    Args:
        df (pd.DataFrame): Must contain 'gage_id' and 'formulation' columns.
        min_gages (int): Minimum number of gages that must share the same formulations.

    Returns:
        (True, [gages], [shared_formulations]) if found, else (False, [], [])

    """
    # Build mapping from gage_id -> set of formulations
    gage_to_formulations = df.groupby("gage_id")["formulation"].apply(
        lambda x: frozenset(x)
    )

    # All unique gage_ids and their formulation sets
    gage_ids = list(gage_to_formulations.index)
    gage_form_sets = gage_to_formulations.tolist()

    # Step 1: Get all unique formulations across gages
    all_formulations = set().union(*gage_form_sets)

    # Step 2: Loop through combinations of formulations, largest sets first
    for r in range(len(all_formulations), 0, -1):  # Start from largest combos
        for combo in combinations(all_formulations, r):
            combo_set = set(combo)
            matching_gages = [
                gage_ids[i]
                for i, g_form in enumerate(gage_form_sets)
                if combo_set.issubset(g_form)
            ]
            if len(matching_gages) >= min_gages:
                logger.debug(
                    f"Found {len(matching_gages)} gages ({matching_gages}) sharing formulations: {combo_set}."
                )
                return True, matching_gages, list(combo_set)

    return False, [], []


def _find_gages_nearest_neighbor(
    huc_id: str,
    df: pd.DataFrame,
    gage_file: Path,
    gage_id_col: str,
    min_gages: int,
    gdf: gpd.GeoDataFrame,
) -> tuple[list, list, list]:
    """Find gages for the given HUC ID in the DataFrame.

    Args:
        huc_id (str): HUC ID to find gages for.
        df (pd.DataFrame): DataFrame of summary scores.
        gage_file (Path): Path to the donor gage file containing gage_id, longitude, and latitude.
        gage_id_col (str): Column name for gage ID in the gage file.
        min_gages (int): Minimum number of gages required for each spatial unit.
        gdf (gpd.GeoDataFrame): GeoDataFrame of hydrofabric (HUC12) polygons.

    Returns:
        tuple: A tuple containing a list of calibration gage IDs found for the HUC ID,  distances of the gages
            to the HUC centroid, and the shared formulations.

    """
    # get all calibration gages with valid formulation and summary scores
    gages_calib = (
        df[~df["formulation"].isna() & ~df["summary_score"].isna()][gage_id_col]
        .unique()
        .tolist()
    )

    # iteratively find the nearest neighbor gages for the given HUC ID, increasing the neighborhood size
    # by 100km each time until the minimum number of gages is met
    buffer = 100  # initial buffer size in kilometers
    gages = []
    while len(gages) < min_gages:
        # find gages within the buffer around huc_id
        gages, distances, _ = find_gages_within_buffer(
            gage_file, gage_id_col, buffer, gdf=gdf, id=huc_id
        )

        # filter gages to only those that are calibrated, and filter distances accordingly
        filtered = [(g, d) for g, d in zip(gages, distances) if g in gages_calib]
        if filtered:
            gages, distances = map(list, zip(*filtered))
        else:
            gages, distances = [], []

        # if there are enough gages, check if they share the same formulations
        found_gages = None
        if len(gages) > min_gages:
            found_gages, gages, formulations = _get_gages_with_shared_formulations(
                df[df[gage_id_col].isin(gages)], min_gages=min_gages
            )

        # if no gages are found, increase the buffer size and try again
        if not found_gages:
            logger.debug(
                f"{huc_id}: Not enough gages found within {buffer} km buffer. Increasing buffer size."
            )
            buffer += 100  # increase buffer size by 100 km
        else:
            logger.debug(
                f"{huc_id}: Found {len(gages)} gages ({gages}) within {buffer} km buffer."
            )
            break
    else:
        msg = (
            f"Not enough calibrated gages found for {huc_id} after increasing buffer size to {buffer} km. "
            f"Minimum required is {min_gages}."
        )
        logger.error(msg)
        raise ValueError(msg)

    return gages, distances, formulations


def _find_gages_upscaling(
    huc_id: str, df: pd.DataFrame, gage_id_col: str, min_gages: int
) -> tuple[list, str, list]:
    """Find gages for the given HUC ID in the DataFrame.

    Args:
        huc_id (str): HUC ID to find gages for.
        df (pd.DataFrame): DataFrame of summary scores.
        gage_id_col (str): Column name for gage ID in the gage file.
        min_gages (int): Minimum number of gages required for each spatial unit.

    Returns:
        tuple: A tuple containing a list of calibration gage IDs found for the HUC ID, the HUC level,
        and the shared formulations.

    """
    # define valid HUC levels
    valid_huc_levels = ["huc2", "huc4", "huc6", "huc8", "huc10", "huc12"]
    valid_huc_levels.reverse()

    # make sure current huc level is in the valid HUC levels
    current_huc_level = "huc" + str(len(huc_id))
    if current_huc_level not in valid_huc_levels:
        msg = f"Invalid current HUC level: {current_huc_level}. Valid levels are: {', '.join(valid_huc_levels)}."
        logger.error(msg)
        raise ValueError(msg)

    gages = []
    formulations = []
    huc_level = current_huc_level  # Default to current if nothing better is found

    # start from current huc level, loop through valid HUC levels to ensure sufficient calibrated gages
    for _, huc_level in enumerate(
        valid_huc_levels[valid_huc_levels.index(current_huc_level) :]
    ):
        # count the number of unique gages in the new HUC level
        huc_digit = int(huc_level.replace("huc", ""))
        gages = (
            df[df["huc_id"].str[:huc_digit] == huc_id[:huc_digit]][gage_id_col]
            .unique()
            .tolist()
        )

        # remove NaN values from gages
        gages = [gage for gage in gages if pd.notna(gage)]
        ngage = len(gages)

        # if there are enough gages, check if they share the same formulations
        if ngage >= min_gages:
            found_gages, gages, formulations = _get_gages_with_shared_formulations(
                df[df[gage_id_col].isin(gages)], min_gages=min_gages
            )

            if not found_gages:
                logger.debug(
                    f"{huc_id}: upscaling HUC level from {current_huc_level} to {huc_level} "
                )
                continue
            else:
                # logger.debug(f"{huc_id}: found {len(gages)} gages ({gages}) at {huc_level} level.")
                break

    return gages, huc_level, formulations


def _find_calibration_gages(
    huc_id: str, df: pd.DataFrame, config: cs.Config, gdf: gpd.GeoDataFrame
) -> tuple[str, list, list, list]:
    """Find gages for the given HUC ID in the DataFrame.

    Args:
        huc_id (str): HUC ID to find gages for.
        df (pd.DataFrame): DataFrame of summary scores.
        config (cs.Config): Configuration object containing settings.
        gdf (gpd.GeoDataFrame): GeoDataFrame of hydrofabric (HUC12) polygons.

    Returns:
        tuple: A tuple containing the HUC level, the list of calibration gage IDs found for the HUC ID,
            list of corresponding distances, and the list of shared formulations.

    """
    # get configuration settings
    gage_id_col = config.general.id_col[
        "gage"
    ]  # column name for gage ID in the DataFrame
    nmin_gages = (
        config.spatial_unit.nmin_calib_basin
    )  #  minimum number of calibration gages required
    method = (
        config.spatial_unit.basin_fill_method.lower()
    )  # method to find additional calibration gages if needed
    gage_file = config.general.donor_gage_file  # path to the donor gage file

    # check if the huc_id is valid
    if not isinstance(huc_id, str) or len(huc_id) < 2:
        msg = f"Invalid HUC ID: {huc_id}. It should be a string with at least 2 characters."
        logger.error(msg)
        raise ValueError(msg)

    # remove rows with invalid gage_id_col, formulation, and summary_score columns in the DataFrame
    df = df[
        ~df[gage_id_col].isna()
        & ~df["formulation"].isna()
        & ~df["summary_score"].isna()
    ]

    # check number of calibration gages within the current huc_id
    gages0 = df[df["huc_id"] == huc_id][gage_id_col].unique().tolist()
    gages0 = [gage for gage in gages0 if pd.notna(gage)]  # remove NaN values

    if len(gages0) >= nmin_gages:
        found_gages, gages0, formulations = _get_gages_with_shared_formulations(
            df[df[gage_id_col].isin(gages0)], min_gages=nmin_gages
        )

    # if there are enough gages at the current huc_id level, return them
    if len(gages0) >= nmin_gages:
        logger.debug(
            f"{huc_id}: found {len(gages0)} calibration gages ({gages0}) at the current level. No need to find additional gages."
        )
        huc_level = "huc" + str(len(huc_id))
        return huc_level, gages0, [np.nan] * len(gages0), formulations
    else:
        logger.debug(
            f"{huc_id}: found only {len(gages0)} calibration gages ({gages0}) at the current level. "
            f"Need to find additional gages using the {method} method."
        )

    def nearest_neighbor_fallback():
        logger.warning(
            f"Not enough calibration gages found for {huc_id} after upscaling. "
            f"Found {len(gages0)} gages ({gages0}), minimum required is {nmin_gages}. "
            f"Use nearest-neighbor method for {huc_id} instead."
        )
        gages_nn, dists_nn, formulations = _find_gages_nearest_neighbor(
            huc_id, df, gage_file, gage_id_col, nmin_gages, gdf
        )
        return gages_nn, dists_nn, "huc" + str(len(huc_id)), formulations

    if method == "upscaling":
        # find calibration gages using upscaling method
        gages, huc_level, formulations = _find_gages_upscaling(
            huc_id, df, gage_id_col, nmin_gages
        )
        dists = [np.nan] * len(gages)
        if len(gages) < nmin_gages:
            gages, dists, huc_level, formulations = nearest_neighbor_fallback()

    elif method == "nearest-neighbor":
        # find calibration gages using nearest neighbor
        gages, dists, formulations = _find_gages_nearest_neighbor(
            huc_id, df, gage_file, gage_id_col, nmin_gages, gdf
        )
        huc_level = "huc" + str(
            len(huc_id)
        )  # HUC level is determined by the length of huc_id
    else:
        # raise error if the basin fill method is not recognized
        msg = f"Unknown basin fill method: {method}. Supported methods are 'upscaling' and 'nearest-neighbor'."
        logger.error(msg)
        raise ValueError(msg)

    return huc_level, gages, dists, formulations


def _get_formulation_costs(
    config: cs.FormulationCostConfig,
) -> Optional[dict[str, float]]:
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
        check_columns_dataframe(
            config.file,
            columns=["formulation", "cost"],
        )
        # read the cost file
        cost_df = read_table(config.file)
        if not cost_df.empty:
            return dict(zip(cost_df["formulation"], cost_df["cost"]))
        else:
            logger.warning(
                f"No costs found in the file: {config.file}. Returning None."
            )
            return None
    elif config.costs:
        return config.costs
    else:
        logger.warning(
            "No formulation costs defined in the configuration. Returning None."
        )

    return None


def _select_formulation_given_score(
    df: pd.DataFrame,
    method: str = "basin",
    type: str = "total_score",
    id_col: dict[str, str] = {"gage": "gage_id", "divide": "divide_id"},
) -> pd.DataFrame:
    """Compute total score for each spatial unit based on the method specified.

    Args:
        df : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        method : str, optional
            Method to compute total score, either 'basin' or 'divide', by default 'basin'.
        type : str, optional
            Type of total score to compute, either 'total_score' or 'total_count', by default 'total_score'.
        id_col : dict[str, str], optional
            Dictionary mapping spatial unit type to its identifier column name,
            by default {"gage": "gage_id", "divide": "divide_id"}.

    Returns:
        pd.DataFrame
            DataFrame with total scores computed for each spatial unit.

    """
    col1 = (
        id_col.get("gage", "gage_id")
        if type == "basin" and "gage_id" in df.columns
        else id_col.get("divide", "divide_id")
    )

    df1 = df[[col1, "formulation", "summary_score", "cost"]].copy()

    # remove duplicate rows
    df1 = df1.drop_duplicates(subset=[col1, "formulation"])

    # drop rows with NaN values in the summary_score column
    df1 = df1.dropna(subset=["summary_score"])

    # identify best formulation(s)
    if method == "total_score":
        df1.loc[:, method] = (
            df1.groupby(["formulation"])["summary_score"].transform("sum").round(2)
        )
    elif method == "total_count":
        df1.loc[:, method] = df1.groupby(["formulation"])["summary_score"].transform(
            "count"
        )
    else:
        msg = f"Unknown method: {method}. Supported methods are 'total_score' and 'total_count'."
        logger.error(msg)
        raise ValueError(msg)

    # keep only the best formulation(s) with the highest total score
    df1 = df1[df1[method] == df1[method].max()]

    # if there are multiple formulations with the same total score, choose the one that has the lowest cost
    if df1.shape[0] > 1:
        df1 = df1[df1["cost"] == df1["cost"].min()]

    # drop col1
    df1 = df1.drop(columns=[col1])

    # remove duplicates
    df1 = df1.drop_duplicates(subset=["formulation", method])

    return df1


def _identify_best_formulation_per_gage(
    df_score: pd.DataFrame,
    gage_id_col: str,
    tolerance: float = 0.05,
    cost_dict: Optional[dict] = None,
) -> pd.DataFrame:
    """Identify the best formulation for each gage based on summary scores and costs.

    Args:
        df_score : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        gage_id_col : str
            Column name for gage ID in the gage file.
        tolerance : float, optional
            Tolerance for the summary score to consider formulations as equally good, by default 0.05.
        cost_dict : dict, optional
            Dictionary containing costs for each formulation, by default None.

    Returns:
        pd.DataFrame
            DataFrame with the best formulation for each gage and its score.

    """
    max_scores = df_score.groupby(gage_id_col)["summary_score"].transform("max")
    best_per_gage = df_score[
        df_score["summary_score"] >= (max_scores - max_scores * tolerance)
    ].copy()

    if cost_dict is not None:
        # check if all formulations are in the cost_dict
        if not best_per_gage["formulation"].isin(cost_dict.keys()).all():
            missed_formulations = best_per_gage[
                ~best_per_gage["formulation"].isin(cost_dict.keys())
            ]["formulation"].unique()

            msg = f"Some formulations are missing costs in the configuration: {', '.join(missed_formulations)}."
            logger.error(msg)
            raise ValueError(msg)

        # map costs to the formulations
        best_per_gage.loc[:, "cost"] = best_per_gage["formulation"].map(cost_dict)

        # for each gage, select the formulation with the minimum cost
        best_per_gage = best_per_gage.loc[
            best_per_gage.groupby(gage_id_col)["cost"].idxmin()
        ].copy()

        # if there are multiple formulations with the same minimum cost, keep the first one
        best_per_gage = best_per_gage.drop_duplicates(subset=[gage_id_col])
    else:
        # choose the first formulation with the highest score for each gage
        best_per_gage = best_per_gage.loc[
            best_per_gage.groupby(gage_id_col)["summary_score"].idxmax()
        ].copy()

        # initialize cost column to None
        best_per_gage["cost"] = None

    return best_per_gage


def select_formulation_donors_only(
    config: cs.Config,
    df_score: pd.DataFrame,
    cost_dict: Optional[dict] = None,
) -> pd.DataFrame:
    """Select formulations for donor basins only based on summary scores and costs.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        df_score : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        cost_dict : Optional[dict], optional
            Dictionary containing costs for each formulation, by default None.

    Returns:
        pd.DataFrame
            DataFrame with selected formulations and their scores.

    """
    # get the ID columns from the configuration
    id_cols = config.general.id_col
    gage_id_col = id_cols["gage"]
    divide_id_col = id_cols["divide"]

    # score computing method, type, and tolerance
    score_tolerance = config.spatial_unit.best_formulation.tolerance

    # identify the best formulation for each gage
    df_best_per_gage = _identify_best_formulation_per_gage(
        df_score,
        gage_id_col=gage_id_col,
        tolerance=score_tolerance,
        cost_dict=cost_dict,
    )

    # read the crosswalk file for gage/divide relationships
    col_dtype = {
        gage_id_col: "str",
        divide_id_col: "str",
    }
    cwt_divide_gage = read_table(config.general.gage_divide_cwt_file, dtype=col_dtype)

    # merge the crosswalk with the best formulations DataFrame
    df_selected = df_best_per_gage.merge(
        cwt_divide_gage[[gage_id_col]].drop_duplicates(),
        on=gage_id_col,
        how="left",
    )

    return df_selected


def select_formulation_all(
    config: cs.Config,
    vpu: str,
    df_score: pd.DataFrame,
    gdf_vpu: gpd.GeoDataFrame,
    cost_dict: Optional[dict] = None,
) -> pd.DataFrame:
    """Select formulation for all catchments in the VPU.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            Virtual Planning Unit (VPU) for which to select formulations.
        df_score : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        gdf_vpu : gpd.GeoDataFrame
            GeoDataFrame of the VPU polygons, used for spatial operations where needed.
        cost_dict : Optional[dict], optional
            Dictionary containing costs for each formulation, by default None.

    Returns:
        pd.DataFrame
            DataFrame with selected formulations and their scores.

    """
    # get the ID columns from the configuration
    id_cols = config.general.id_col
    gage_id_col = id_cols["gage"]
    divide_id_col = id_cols["divide"]
    huc12_id_col = id_cols["huc12"]

    # score computing method, type, and tolerance
    score_method = config.spatial_unit.best_formulation.method.lower()
    score_type = config.spatial_unit.best_formulation.type.lower()
    score_tolerance = config.spatial_unit.best_formulation.tolerance
    logger.info(
        f"Computing total score using method '{score_method}' and type '{score_type}'."
    )

    # crosswalk for gage/divide
    col_dtype = {
        gage_id_col: "str",
        divide_id_col: "str",
        huc12_id_col: "str",
    }
    cwt_divide_gage = read_table(config.general.gage_divide_cwt_file, dtype=col_dtype)

    # crosswalk for divide/huc12
    cwt_divide_huc12 = read_table(config.general.divide_huc12_cwt_file, dtype=col_dtype)

    # filter cwt_divide_huc12 with divides in gdf_vpu (i.e., only keep divides that are in the current VPU)
    cwt_divide_huc12 = cwt_divide_huc12[
        cwt_divide_huc12[divide_id_col].isin(gdf_vpu[divide_id_col])
    ].copy()

    # get spatial units for formulation selection
    huc_level = config.spatial_unit.huc_level.lower().replace("-", "").replace("_", "")
    huc_digit = int(huc_level.replace("huc", ""))

    # add huc_id column to cwt_divide_huc12 based on huc_digit
    cwt_divide_huc12["huc_id"] = cwt_divide_huc12[huc12_id_col].str[:huc_digit]

    # make sure type of huc_id column is string
    if not pd.api.types.is_string_dtype(cwt_divide_huc12["huc_id"]):
        logger.warning(
            f"Converting 'huc_id' column to string type. Current type: {cwt_divide_huc12['huc_id'].dtype}."
        )
        cwt_divide_huc12["huc_id"] = cwt_divide_huc12["huc_id"].astype(str)

    # merge the two crosswalks first
    df_cwt = cwt_divide_huc12[["huc_id", huc12_id_col, divide_id_col]].merge(
        cwt_divide_gage[[gage_id_col, divide_id_col]].drop_duplicates(),
        on=divide_id_col,
        how="left",
    )

    # then merge with the score DataFrame
    df_score = df_score.merge(df_cwt, on=gage_id_col, how="outer")

    logger.info(
        f"Selecting formulations for VPU {vpu} at {huc_level} level. "
        f"There are {len(df_score['huc_id'].unique())} unique {huc_level} IDs."
    )

    # all unique huc_ids in the score DataFrame
    huc_ids = df_score["huc_id"].unique()

    # remove NaN values from huc_ids
    huc_ids = [huc_id for huc_id in huc_ids if pd.notna(huc_id)]

    # get huc12 geometry for these huc_ids (to compute centroid distances between gages and huc_ids)
    huc12_hydro_file = Path(config.general.huc12_hydrofabric_file).resolve(strict=True)

    # Open with Fiona to read features in huc_ids
    features = []
    huc_digit = len(huc_ids[0])  # assuming all huc_ids have the same length
    with fiona.open(huc12_hydro_file, "r", open_options=["METHOD=ONLY_CCW"]) as src:
        for feat in src:
            huc_key = next(
                (k for k in feat["properties"] if k.lower() == huc12_id_col), None
            )
            if huc_key and feat["properties"][huc_key][:huc_digit] in huc_ids:
                features.append(feat)

        # Convert to GeoDataFrame
        huc12_gdf = gpd.GeoDataFrame.from_features(features, crs=src.crs)

    # loop through each unique huc_id and select formulation
    df_selected = pd.DataFrame()
    for huc_id in huc_ids:
        logger.debug(f"Processing HUC ID: {huc_id}")

        # Find actual column name in gdf that matches huc12_id_col (case-insensitive)
        col_match = next(
            (col for col in huc12_gdf.columns if col.lower() == huc12_id_col.lower()),
            None,
        )

        # Use the matched column to filter huc12_gdf
        huc12_gdf_huc = huc12_gdf[
            huc12_gdf[col_match].astype(str).str[:huc_digit] == huc_id
        ].copy()

        if huc12_gdf_huc.empty:
            msg = f"No geometry found for HUC ID: {huc_id}. Please check the HUC12 hydrofabric file."
            logger.error(msg)
            raise ValueError(msg)

        huc_level, gages, dists, formulations = _find_calibration_gages(
            huc_id, df_score, config, huc12_gdf_huc
        )
        if not gages:
            msg = (
                f"No calibration gages found for HUC ID: {huc_id}. "
                f"Minimum required is {config.spatial_unit.nmin_calib_basin}."
            )
            logger.error(msg)
            raise ValueError(msg)

        # filter the score DataFrame for identified gages and formulations
        df_huc = df_score[
            df_score[gage_id_col].isin(gages)
            & df_score["formulation"].isin(formulations)
        ].copy()

        # identify best formulation for each gage based on summary scores for formulation costs
        df_huc = _identify_best_formulation_per_gage(
            df_huc,
            gage_id_col=gage_id_col,
            tolerance=score_tolerance,
            cost_dict=cost_dict,
        )

        # select the best formulation for each huc_id based on the total score or count
        best_formulation = _select_formulation_given_score(
            df_huc, method=score_method, type=score_type
        )

        # append the selected formulation to the list
        if best_formulation.empty:
            logger.warning(
                f"No valid formulations found for HUC ID: {huc_id}. Skipping this HUC."
            )
            continue

        # add huc_id, huc_level, number of gages and vpu to the best formulation
        best_formulation["huc_id"] = huc_id
        best_formulation["upscale_huc"] = huc_level
        best_formulation["num_gages"] = len(gages)
        best_formulation["distances"] = ", ".join(
            [str(d) for d in dists]
        )  # join distances as a stringi

        df_selected = pd.concat([df_selected, best_formulation], ignore_index=True)

    # merge with cwt_divide_huc12 to get the divide_id
    df_selected = df_selected.merge(
        cwt_divide_huc12[["huc_id", divide_id_col]].drop_duplicates(),
        on="huc_id",
        how="left",
    )

    # handle formulation selection for calibration gages
    if config.general.approach_calib_basins == "regionalization":
        pass
    elif config.general.approach_calib_basins == "summary_score":
        # select formulations for donor gages based on the summary scores and costs
        df_selected_donors = select_formulation_donors_only(
            config, df_score, cost_dict=cost_dict
        )

        # replace the formulation for donors in df_selected with the one from df_selected_donors
        form_map = df_selected_donors.drop_duplicates(divide_id_col).set_index(
            divide_id_col
        )["formulation"]
        df_selected.loc[:, "formulation"] = (
            df_selected[divide_id_col].map(form_map).fillna(df_selected["formulation"])
        )
    else:
        msg = (
            f"Unknown approach for assigning formulations to calibrated basins: "
            f"{config.general.approach_calib_basins}. Supported methods are 'regionalization' and 'summary_score'."
        )
        logger.error(msg)
        raise ValueError(msg)

    return df_selected


def save_formulation_results(
    df_selected: pd.DataFrame,
    config: cs.Config,
    vpu: str,
) -> None:
    """Save the selected formulations to the output file.

    Args:
        df_selected : pd.DataFrame
            DataFrame with selected formulations and their scores.
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            Virtual Planning Unit (VPU) for which to save formulations.

    """
    cc = config.output["formulation"]
    cc.save_to_file(
        df_selected, vpu=vpu, data_str="Formulation Selection", use_stem_suffix=False
    )

    # create a slim version of the selected DataFrame by removing the divide_id column
    df_selected_slim = df_selected.copy()
    df_selected_slim = df_selected_slim.drop(columns=["divide_id"])

    # remove duplicates based on formulation and huc_id/gage_id
    columns = ["formulation", "huc_id", "gage_id"]
    df_selected_slim = df_selected_slim.drop_duplicates(
        subset=[c for c in columns if c in df_selected_slim.columns]
    )

    cc.save_to_file(
        df_selected_slim,
        vpu=vpu,
        data_str="Formulation Selection (slim version)",
        use_stem_suffix=True,
    )


def plot_formulation_results(
    df_selected: pd.DataFrame,
    config: cs.Config,
    vpu: str,
    gdf_vpu: Optional[gpd.GeoDataFrame],
) -> None:
    """Plot the selected formulations for each spatial unit in the VPU.

    Args:
        df_selected : pd.DataFrame
            DataFrame with selected formulations and their scores.
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            Virtual Planning Unit (VPU) for which to plot formulations.
        gdf_vpu : Optional[gpd.GeoDataFrame], optional
            GeoDataFrame of the VPU polygons, used for spatial operations where needed

    """
    # generate plots if enabled
    cc = config.output["formulation"]
    divide_id_col = config.general.id_col["divide"]
    score_method = config.spatial_unit.best_formulation.method.lower()
    if any(cc.plots.values()):
        # get geometry for divides if spatial map is enabled
        if cc.plots.get("spatial_map", False):
            # merge the geometry with the selected formulations
            df_selected = df_selected.merge(
                gdf_vpu[[divide_id_col, "geometry"]].drop_duplicates(),
                on=divide_id_col,
                how="left",
            )

            # convert df_selected to a real GeoDataFrame for plotting
            df_selected = gpd.GeoDataFrame(
                df_selected,
                geometry="geometry",
                crs=gdf_vpu.crs,
            )

        # plot the selected formulations
        columns_to_plot = cc.plots.get("columns_to_plot", None)
        if columns_to_plot is None:
            columns_to_plot = ["formulation", score_method, "summary_score", "cost"]
        plot_dict = {
            "vpu": vpu,
            "var_str": "Formulation Selection",
            "columns": columns_to_plot,
            "ncols": 3,
        }
        cc.plot_data(df_selected, plot_dict)


def select_formulation(
    config: cs.Config,
    vpu: str,
    df_score: pd.DataFrame,
    gdf_vpu: Optional[gpd.GeoDataFrame],
) -> pd.DataFrame:
    """Head function to select formulations for catchments in the VPU.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            Virtual Planning Unit (VPU) for which to select formulations.
        df_score : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        gdf_vpu : Optional[gpd.GeoDataFrame]
            GeoDataFrame of the VPU polygons, used for spatial operations where needed.

    Returns:
        pd.DataFrame
            DataFrame with selected formulations and their scores.

    """
    # get formulation costs from the configuration
    formulation_costs = _get_formulation_costs(config.formulation_cost)
    cost_dict = formulation_costs if config.general.consider_cost else None

    if config.general.calib_basins_only:
        # select formulations for donor basins only
        df_formulation = select_formulation_donors_only(config, df_score, cost_dict)
    else:
        # select formulations for all catchments in the VPU
        df_formulation = select_formulation_all(
            config, vpu, df_score, gdf_vpu, cost_dict
        )

    # add vpu column to the formulation DataFrame
    df_formulation["vpu"] = vpu

    # rearrange the columns in the formulation DataFrame
    divide_id_col = config.general.id_col["divide"]
    score_method = config.spatial_unit.best_formulation.method.lower()
    columns = [
        "vpu",
        divide_id_col,
        "formulation",
        "huc_id",
        score_method,
        "summary_score",
        "cost",
        "num_gages",
    ]
    method1 = config.spatial_unit.basin_fill_method.lower()
    output_columns = (
        columns + ["upscale_huc"] if method1 == "upscaling" else columns + ["distances"]
    )
    df_formulation = df_formulation.reindex(
        columns=[c for c in output_columns if c in df_formulation.columns]
    )

    # save the selected formulations to the output file
    save_formulation_results(df_formulation, config, vpu)

    # plot the selected formulations
    plot_formulation_results(df_formulation, config, vpu, gdf_vpu)

    return df_formulation
