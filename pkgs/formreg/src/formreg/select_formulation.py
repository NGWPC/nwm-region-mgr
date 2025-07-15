"""Select formulations for regionalization.

This module provides functions to select formulations based on summary scores of calibrated basins,
as well as formulation costs if provided in the configuration.

Functions:
- _find_calibration_gages_nearest_neighbor: Find gages for a given HUC ID using the nearest neighbor method.
- _find_calibration_gages_upscaling: Find gages for a given HUC ID using the upscaling method.
- _find_calibration_gages: Find gages for a given HUC ID in the summary scores DataFrame.
- _get_formulation_costs: Retrieve formulation costs from the configuration.
- _select_formulation_given_score: Select a formulation for each spatial unit based on the method specified.
- _identify_best_formulation_per_gage: Identify the best formulation for each gage based on summary scores and costs.
- select_formulation: head function to select formulations for each spatial unit in the VPU.

"""

import logging
from pathlib import Path
from typing import Optional

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd

from utils import check_columns, find_gages_within_buffer, read_table
from . import config_schema as cs

logger = logging.getLogger(__name__)


def _find_calibration_gages_nearest_neighbor(
    huc_id: str,
    df: pd.DataFrame,
    gage_file: Path,
    min_gages: int,
    gdf: gpd.GeoDataFrame,
) -> tuple[list, str]:
    """Find gages for the given HUC ID in the DataFrame.

    Args:
        huc_id (str): HUC ID to find gages for.
        df (pd.DataFrame): DataFrame of summary scores.
        gage_file (Path): Path to the donor gage file containing gage_id, longitude, and latitude.
        min_gages (int): Minimum number of gages required for each spatial unit.
        gdf (gpd.GeoDataFrame): GeoDataFrame of hydrofabric (HUC12) polygons.

    Returns:
        tuple: A tuple containing a list of calibration gage IDs found for the HUC ID and distances of the gages
            to the HUC centroid.

    """
    # get all calibration gages with valid formulation and summary scores
    gages_calib = df[~df["formulation"].isna() & ~df["summary_score"].isna()]["gage_id"].unique().tolist()

    # iteratively find the nearest neighbor gages for the given HUC ID, increasing the neighborhood size
    # by 100km each time until the minimum number of gages is met
    buffer = 100  # initial buffer size in kilometers
    gages = []
    while len(gages) < min_gages:
        # find gages within the buffer around huc_id
        gages, distances, _ = find_gages_within_buffer(gage_file, buffer, gdf=gdf)

        # filter gages to only those that are calibrated, and filter distances accordingly
        gages, distances = (
            map(list, zip(*[(g, d) for g, d in zip(gages, distances) if g in gages_calib])) if gages else ([], [])
        )
        distances = pd.Series(distances)

        # if no gages are found, increase the buffer size and try again
        if not gages or len(gages) < min_gages:
            logger.debug(f"{huc_id}: Not enough gages found within {buffer} km buffer. Increasing buffer size.")
            buffer += 100  # increase buffer size by 100 km
        else:
            logger.debug(f"{huc_id}: Found {len(gages)} gages within {buffer} km buffer.")
            break
    else:
        raise ValueError(
            f"Not enough calibrated gages found for {huc_id} after increasing buffer size to {buffer} km. "
            f"Minimum required is {min_gages}."
        )

    # only keep the minimum number of gages required
    if len(gages) > min_gages:
        # sort gages by distance and keep the closest ones
        sorted_indices = distances.argsort()[:min_gages]
        gages = [gages[i] for i in sorted_indices]
        distances = distances.iloc[sorted_indices].tolist()

    return gages, distances


def _find_calibration_gages_upscaling(huc_id: str, df: pd.DataFrame, min_gages: int) -> tuple[list, str]:
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


def _find_calibration_gages(
    huc_id: str, df: pd.DataFrame, config: cs.Config, gdf: gpd.GeoDataFrame
) -> tuple[list, str]:
    """Find gages for the given HUC ID in the DataFrame.

    Args:
        huc_id (str): HUC ID to find gages for.
        df (pd.DataFrame): DataFrame of summary scores.
        config (cs.Config): Configuration object containing settings.
        gdf (gpd.GeoDataFrame): GeoDataFrame of hydrofabric (HUC12) polygons.

    Returns:
        tuple: A tuple containing a list of calibration gage IDs found for the HUC ID and the HUC level.

    """
    # check if the huc_id is valid
    if not isinstance(huc_id, str) or len(huc_id) < 2:
        raise ValueError(f"Invalid HUC ID: {huc_id}. It should be a string with at least 2 characters.")

    # check number of calibration gages within the current huc_id
    gages0 = (
        df[(df["huc_id"] == huc_id) & (~df["formulation"].isna()) & (~df["summary_score"].isna())]["gage_id"]
        .unique()
        .tolist()
    )

    # method to find additional calibration gages if not enough gages are found in the current huc_id
    method = config.spatial_unit.basin_fill_method.lower()

    # if there are enough gages at the current huc_id level, return them
    if len(gages0) >= config.spatial_unit.nmin_calib_basin:
        logger.debug(
            f"Found {len(gages0)} calibration gages for HUC ID {huc_id} at the current level. "
            f"No need to find additional gages."
        )
        huc_level = "huc" + str(len(huc_id))
        return huc_level, gages0, [np.nan] * len(gages0)
    else:
        logger.debug(
            f"Found only {len(gages0)} calibration gages for HUC ID {huc_id} at the current level. "
            f"Need to find additional gages using the {method} method."
        )

    if method == "upscaling":
        # find calibration gages using upscaling method
        gages, huc_level = _find_calibration_gages_upscaling(huc_id, df, config.spatial_unit.nmin_calib_basin)
        dists = [np.nan] * len(gages)
    elif method == "nearest-neighbor":
        # find calibration gages using nearest neighbor
        gages, dists = _find_calibration_gages_nearest_neighbor(
            huc_id,
            df,
            config.general.donor_gage_file,
            config.spatial_unit.nmin_calib_basin,
            gdf,
        )
        huc_level = "huc" + str(len(huc_id))  # HUC level is determined by the length of huc_id
    else:
        # raise error if the basin fill method is not recognized
        raise ValueError(
            f"Unknown basin fill method: {method}. Supported methods are 'upscaling' and 'nearest-neighbor'."
        )

    return huc_level, gages, dists


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


def _select_formulation_given_score(
    df: pd.DataFrame,
    method: str = "basin",
    type: str = "total_score",
) -> pd.DataFrame:
    """Compute total score for each spatial unit based on the method specified.

    Args:
        df : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        method : str, optional
            Method to compute total score, either 'basin' or 'divide', by default 'basin'.
        type : str, optional
            Type of total score to compute, either 'total_score' or 'total_count', by default 'total_score'.

    Returns:
        pd.DataFrame
            DataFrame with total scores computed for each spatial unit.

    """
    col1 = "gage_id" if type == "basin" and "gage_id" in df.columns else "divide_id"

    df1 = df[[col1, "formulation", "summary_score", "cost"]].copy()

    # remove duplicate rows
    df1 = df1.drop_duplicates(subset=[col1, "formulation"])

    # drop rows with NaN values in the summary_score column
    df1 = df1.dropna(subset=["summary_score"])

    # identify best formulation(s)
    if method == "total_score":
        df1.loc[:, method] = df1.groupby(["formulation"])["summary_score"].transform("sum")
    elif method == "total_count":
        df1.loc[:, method] = df1.groupby(["formulation"])["summary_score"].transform("count")
    else:
        raise ValueError(f"Unknown method: {method}. Supported methods are 'total_score' and 'total_count'.")

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
    tolerance: float = 0.05,
    cost_dict: Optional[dict] = None,
) -> pd.DataFrame:
    """Identify the best formulation for each gage based on summary scores and costs.

    Args:
        df_score : pd.DataFrame
            DataFrame containing summary scores for each formulation and calibrated basin.
        tolerance : float, optional
            Tolerance for the summary score to consider formulations as equally good, by default 0.05.
        cost_dict : dict, optional
            Dictionary containing costs for each formulation, by default None.

    Returns:
        pd.DataFrame
            DataFrame with the best formulation for each gage and its score.

    """
    max_scores = df_score.groupby("gage_id")["summary_score"].transform("max")
    best_per_gage = df_score[df_score["summary_score"] >= (max_scores - max_scores * tolerance)].copy()

    if cost_dict is not None:
        # check if all formulations are in the cost_dict
        if not best_per_gage["formulation"].isin(cost_dict.keys()).all():
            missed_formulations = best_per_gage[~best_per_gage["formulation"].isin(cost_dict.keys())][
                "formulation"
            ].unique()
            raise ValueError(f"The following formulations have no associated costs: {', '.join(missed_formulations)}.")

        # map costs to the formulations
        best_per_gage.loc[:, "cost"] = best_per_gage["formulation"].map(cost_dict)

        # for each gage, select the formulation with the minimum cost
        best_per_gage = best_per_gage.loc[best_per_gage.groupby("gage_id")["cost"].idxmin()].copy()

        # if there are multiple formulations with the same minimum cost, keep the first one
        best_per_gage = best_per_gage.drop_duplicates(subset=["gage_id"])
    else:
        # choose the first formulation with the highest score for each gage
        best_per_gage = best_per_gage.loc[best_per_gage.groupby("gage_id")["summary_score"].idxmax()].copy()

        # initialize cost column to None
        best_per_gage["cost"] = None

    return best_per_gage


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
    # score computing method, type, and tolerance
    score_method = config.spatial_unit.best_formulation["method"].lower()
    score_type = config.spatial_unit.best_formulation["type"].lower()
    score_tolerance = config.spatial_unit.best_formulation["tolerance"]
    logger.info(f"Computing total score using method '{score_method}' and type '{score_type}'.")

    # get formulation costs from the configuration
    formulation_costs = _get_formulation_costs(config.formulation_cost)

    # identify best formulation for each gage based on summary scores for formulation costs
    df_best = _identify_best_formulation_per_gage(df_score, tolerance=score_tolerance, cost_dict=formulation_costs)

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
    df_score = df_best.merge(df, on="gage_id", how="right")

    # check number of unique gages with valid formulation and summary scores
    gages_all = (
        df_score[~df_score["formulation"].isna() & ~df_score["summary_score"].isna()]["gage_id"].unique().tolist()
    )

    logger.info(
        f"Selecting formulations for VPU {vpu} at {huc_level} level. "
        f"There are {len(df_score['huc_id'].unique())} unique {huc_level} IDs, and "
        f"{len(gages_all)} unique gages."
    )

    # all unique huc_ids in the score DataFrame
    huc_ids = df_score["huc_id"].unique()

    # read huc12 shape file to get the geometry for these huc_ids
    huc12_shape_file = Path(config.general.huc12_shape_file).resolve(strict=True)
    if not huc12_shape_file.exists():
        logger.warning(f"HUC12 shape file {huc12_shape_file} does not exist. Skipping formulation selection.")
        return pd.DataFrame()

    # # Open with Fiona to read features in huc_ids
    features = []
    huc_digit = len(huc_ids[0])  # assuming all huc_ids have the same length
    with fiona.open(huc12_shape_file, "r", open_options=["METHOD=ONLY_CCW"]) as src:
        for feat in src:
            if feat["properties"]["HUC_12"][:huc_digit] in huc_ids:
                features.append(feat)

        # Convert to GeoDataFrame
        huc12_gdf = gpd.GeoDataFrame.from_features(features, crs=src.crs)

    # loop through each unique huc_id and select formulations
    df_selected = pd.DataFrame()
    for huc_id in huc_ids:
        # find calibration gages for the current huc_id
        df_score_huc = df_score[~df_score["formulation"].isna() & ~df_score["summary_score"].isna()].copy()
        if df_score_huc.empty:
            logger.warning(f"No valid formulation scores found for HUC ID: {huc_id}e Skipping this HUC.")
            continue

        # filter huc12_gdf for the current huc_id
        huc12_gdf_huc = huc12_gdf[huc12_gdf["HUC_12"].str[:huc_digit] == huc_id].copy()
        if huc12_gdf_huc.empty:
            logger.warning(f"No geometry found for HUC ID: {huc_id}. Skipping this HUC.")
            continue
        huc_level, gages, dists = _find_calibration_gages(huc_id, df_score_huc, config, huc12_gdf_huc)
        if not gages:
            logger.warning(f"No gages found for HUC ID: {huc_id}. Skipping this HUC.")
            continue

        df_huc = df_score[df_score["gage_id"].isin(gages)].copy()

        # select the best formulation based on the score & optionally costs
        best_formulation = _select_formulation_given_score(df_huc, method=score_method, type=score_type)

        # append the selected formulation to the list
        if best_formulation.empty:
            logger.warning(f"No valid formulations found for HUC ID: {huc_id}. Skipping this HUC.")
            continue

        # add huc_id, huc_level, number of gages and vpu to the best formulation
        best_formulation["huc_id"] = huc_id
        best_formulation["upscale_huc"] = huc_level
        best_formulation["num_gages"] = len(gages)
        best_formulation["distances"] = ", ".join([str(d) for d in dists])  # join distances as a string
        best_formulation["vpu"] = vpu

        df_selected = pd.concat([df_selected, best_formulation], ignore_index=True)
    
    # rearrange the columns in the selected DataFrame
    columns = ["vpu", "huc_id", "formulation", score_method, "cost", "num_gages"]
    method1 = config.spatial_unit.basin_fill_method.lower()
    output_columns = columns + ["upscale_huc"] if method1 == "upscaling" else columns + ["distances"]
    df_selected = df_selected.reindex(columns=output_columns)

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
            "columns": ["formulation", score_method, "cost"],
            "ncols": 3,
        }
        cc.plot_data(df_selected, plot_dict)

    return df_selected
