import logging
import time
from functools import reduce
from pathlib import Path
from typing import Any, Tuple

import geopandas as gpd
import pandas as pd
import yaml
from pydantic import BaseModel, ValidationError
from shapely.geometry import Point
from shapely.ops import unary_union

from . import config_schema as cs
from . import funcs_clust, funcs_dist, utils, utils_algo
from . import plot_outputs as po

logger = logging.getLogger(__name__)


def expand_with_vpu(string_with_vpu: str, context: dict) -> dict:
    """Expand a string with {vpu_list} placeholders.

    Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
    Returns a dictionary where keys are vpu codes and values are the formatted strings.
    """
    if "{vpu_list}" not in string_with_vpu or "vpu_list" not in context:
        return {"default": string_with_vpu.format(**context)}

    return {vpu: string_with_vpu.format(**{**context, "vpu_list": vpu}) for vpu in context["vpu_list"]}


def recursive_substitute(obj: Any, context: dict) -> Any:
    """Recursively substitute placeholders.

    Recursively substitute placeholders in config, be it a Pydantic model, dictionary, or string.

    Args:
        obj: A Pydantic model instance, a dictionary, or a string.
        context: A dictionary of substitution variables.

    Returns:
        The Pydantic model instance, dictionary or string after substitution

    """
    if isinstance(obj, BaseModel):
        # Convert Pydantic model to dict, substitute, then reconstruct the model
        data = obj.model_dump()
        substituted = recursive_substitute(data, context)
        return obj.__class__(**substituted)

    elif isinstance(obj, dict):
        return {k: recursive_substitute(v, context) for k, v in obj.items()}

    elif isinstance(obj, str):
        try:
            if "{vpu_list}" in obj and "vpu_list" in context:
                # If the string contains {vpu} and vpu_list is in context, expand it and substitute the placeholders
                return expand_with_vpu(obj, context)
            else:  # Otherwise, just substitute the placeholders
                return obj.format(**context)
        except KeyError:
            return obj  # leave unchanged if context is incomplete

    else:
        return obj  # return as-is if not str, dict, or BaseModel


def validate_by_section(config: dict) -> dict:
    """Perform pydantic validation separately for different sections.

    Validate different sections of the config file to allow specific validation for certain sections.

    Args:
        config: dictionary of config prior to validation

    Returns:
        Dictionary of config after validation

    """
    # Define the mapping of section names to Pydantic models
    section_map = {
        "general": cs.GeneralConfig,
        "donor": cs.DonorConfig,
        "attr_datasets": cs.AttrDatasets,
        "output": cs.OutputConfig,
        "algorithms": cs.AlgorithmConfig,
    }

    # Define the mapping of algorithm names to Pydantic models
    algorithm_map = {
        "general": cs.AlgoGeneral,
        "gower": cs.Gower,
        "urf": cs.URF,
        "kmeans": cs.KMeans,
        "kmedoids": cs.KMedoids,
        "hdbscan": cs.HDBSCAN,
        "birch": cs.Birch,
    }

    valid_config = dict()
    for section_name, section_content in config.items():
        if section_name != "algorithms":
            section = section_map[section_name]
            valid_config[section_name] = section(**section_content)
        else:
            # Loop through each algorithm
            general = section_content["general"]
            validated_algorithms = {}
            for alg_name, alg_specific in section_content.items():
                alg1 = algorithm_map[alg_name]

                if alg_name == "general":
                    validated_algorithms[alg_name] = alg1(**alg_specific)
                if alg_name not in algorithm_map:
                    raise ValueError(f"No model defined for algorithm: {alg_name}")

                # Merge general algorithm into specific algorithm
                merged = {**general, **alg_specific}

                # Validate
                validated_algorithms[alg_name] = alg1(**merged)

            valid_config[section_name] = validated_algorithms

    return valid_config


def find_occurrences(obj: Any, target: str, path: str = "") -> list:
    """Recursively find occurrences of a target string in a Pydantic model, dictionary, or list.

    Args:
        obj: The object to search (can be a Pydantic model, dictionary, or list).
        target: The target string to find.
        path: The current path in the object structure (used for recursion).

    Returns:
        A list of paths where the target string occurs.

    """
    occurrences = []

    if isinstance(obj, BaseModel):
        obj = obj.model_dump(exclude_unset=True)

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            occurrences.extend(find_occurrences(v, target, new_path))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            occurrences.extend(find_occurrences(item, target, new_path))

    elif isinstance(obj, str):
        if target in obj:
            occurrences.append(path)

    return occurrences


def load_and_validate_config(file_path: str):
    """Load a YAML file, validate its structure using Pydantic, and substitute placeholders in the config.

    Args:
        file_path: path to the config file

    """
    try:
        with open(Path(file_path), "r") as file:
            data = yaml.safe_load(file)

        # validate the config
        validated_config = validate_by_section(data)
        config = cs.Config(**validated_config)

        # resolve placeholders in the config
        context = {
            "domain": config.general.domain,
            "run_name": config.general.run_name,
            "base_dir": config.general.base_dir,
            "vpu_list": config.general.vpu_list,
        }
        config = recursive_substitute(config, context)

        # additional validation after substitution
        # config.donor.check_files()
        out = config.output.config_final
        if out.save:
            logger.info(f"Saving final config to {out.path}")
            if Path(out.path).is_file():
                utils.save_data(config, Path(out.path))
            elif Path(out.path).is_dir():
                utils.save_data(config, Path(out.path, "config_final." + out.format))

        return config

    except ValidationError as e:
        raise Exception(f"Validation Error: {e}")
    except Exception as e:
        raise Exception(f"Error loading YAML file: {e}")


def get_donor_basins(config: cs.Config, vpu: str) -> list:
    """Get the donor basins for a given VPU from the config.

    Args:
        config: the config object
        vpu: the VPU code

    Returns:
        donor_basins: list of donor basins (gage_ids) within the buffered VPU polygon

    """
    # get configs
    gage_file = config.donor.donor_gage_file
    hydrofabric_file = config.general.hydrofabric_file[vpu]
    buffer = config.donor.buffer_km

    # read in lat/lon of all donors
    donors = utils.read_table(gage_file)
    if donors.empty:
        raise ValueError(f"No donors found in the donor gage file: {gage_file}")
    if "longitude" not in donors.columns or "latitude" not in donors.columns:
        raise ValueError(f"Donor gage file must contain 'longitude' and 'latitude' columns: {gage_file}")
    if "gage_id" not in donors.columns:
        raise ValueError(f"Donor gage file must contain 'gage_id' column: {gage_file}")

    # create a GeoDataFrame of donors with geometry as points
    donor_gdf = gpd.GeoDataFrame(
        donors, geometry=[Point(xy) for xy in zip(donors["longitude"], donors["latitude"])], crs="EPSG:4326"
    )

    # read the hydrofabric file
    gdf = gpd.read_file(hydrofabric_file, layer="divides")

    # Project to meters for accurate distance calculations
    donor_gdf = donor_gdf.to_crs(epsg=3857)
    gdf = gdf.to_crs(epsg=3857)

    # remove invalid geometries
    gdf = gdf[gdf.is_valid]

    # dissolve all polygons into one before bufferring
    combined_geom = unary_union(gdf.geometry)

    # Create a buffer around the VPU polygon
    gdf_buffered = combined_geom.buffer(buffer * 1000)

    # Find donors in the buffered VPU
    donor_basins = donor_gdf[donor_gdf.geometry.within(gdf_buffered)]["gage_id"].tolist()

    if not donor_basins:
        logger.warning("No donor basins found. Please check the donor gage file and hydrofabric file.")

    # plot donor basin spatial map
    po.plot_donor_spatial_map(config, vpu, donor_basins, gdf_buffered, combined_geom)

    return donor_basins, gdf_buffered


def update_spatial_distance_donors(
    id_name: str,
    donors_gdf: gpd.GeoDataFrame,
    receivers_gdf: gpd.GeoDataFrame,
    dist_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, bool]:
    """Update existing dataframe for pairwise spatial distance to include new donors (if any).

    Args:
        id_name: the name of the identifier column in the GeoDataFrames
        donors_gdf: GeoDataFrame of new donors
        receivers_gdf: GeoDataFrame of receivers
        dist_df: existing pairwise spatial distance dataframe between donors and receivers

    Returns:
        df_spatial_dist: new dataframe of pairwise spatial distances with new donors (if any) included
        file_changed: boolean indicating whether the file has been changed

    """
    # get new donor list
    new_donor_ids = set(donors_gdf[id_name].values)

    # filter existing distance dataframe columns to keep only new donors
    filtered_df = dist_df.loc[:, dist_df.columns.intersection(new_donor_ids)]

    # find donor IDs missing in the existing dataframe
    missing_donors = new_donor_ids - set(filtered_df.columns)

    if missing_donors:
        # Subset new donors GeoDataFrame to only missing donors
        missing_donors_gdf = donors_gdf[donors_gdf["divide_id"].isin(missing_donors)]

        # Compute distances for missing donors
        missing_distances_df = utils_algo.compute_pairwise_centroid_distances(
            missing_donors_gdf, receivers_gdf, id_name, id_name
        )

        # Horizontally concatenate missing donor columns to filtered dataframe
        updated_df = pd.concat([filtered_df, missing_distances_df], axis=1)
    else:
        updated_df = filtered_df

    # Check if the updated dataframe has changed
    file_changed = not updated_df.equals(dist_df)

    return updated_df, file_changed


def update_spatial_distance_receivers(
    id_name: str,
    donors_gdf: gpd.GeoDataFrame,
    receivers_gdf: gpd.GeoDataFrame,
    dist_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, bool]:
    """Update existing dataframe for pairwise spatial distance to include new receivers (if any).

    Args:
        id_name: the name of the identifier column in the GeoDataFrames
        donors_gdf: GeoDataFrame of donors
        receivers_gdf: GeoDataFrame of receivers
        dist_df: existing pairwise spatial distance dataframe between donors and receivers

    Returns:
        df_spatial_dist: new dataframe of pairwise spatial distances with new donors (if any) included
        file_changed: boolean indicating whether the file has been changed.

    """
    # get new receiver list
    new_receiver_ids = set(receivers_gdf[id_name].values)

    # filter existing distance dataframe columns to keep only new receivers
    filtered_df = dist_df.loc[dist_df.index.intersection(new_receiver_ids), :]

    # find receiver IDs missing in the existing dataframe
    missing_receivers = new_receiver_ids - set(filtered_df.index)

    if missing_receivers:
        # Subset new receivers GeoDataFrame to only missing receivers
        missing_receivers_gdf = receivers_gdf[receivers_gdf["divide_id"].isin(missing_receivers)]

        # Compute distances for missing receivers
        missing_distances_df = utils_algo.compute_pairwise_centroid_distances(
            donors_gdf, missing_receivers_gdf, id_name, id_name
        )

        # Vertically concatenate missing receiver rows to filtered dataframe
        updated_df = pd.concat([filtered_df, missing_distances_df], axis=0)
    else:
        updated_df = filtered_df

    # Check if the updated dataframe has changed
    file_changed = not updated_df.equals(dist_df)

    return updated_df, file_changed


def get_donors_receivers(config: cs.Config, vpu: str) -> Tuple[list, list, pd.DataFrame]:
    """Get the donors and receivers for a given VPU from the config.

    Args:
        config: the config object
        vpu: the VPU code

    Returns:
        donors: list of donors
        receivers: list of receivers
        df_spatial_dist: dataframe of pairwise spatial distances between donors and receivers

    """
    # get id_name from the config
    id_name = config.general.id_name

    # get donor basins for the VPU
    donor_basins, gdf_buffered = get_donor_basins(config, vpu)

    # determine the VPUs of the donor basins
    df_cwt = utils.read_table(config.donor.donor_ngen_cwt_file)
    donor_vpus = df_cwt[df_cwt["gage_id"].isin(donor_basins)]["vpuid"].unique().tolist()

    # loop through the VPUs of the donor basins to get donor & receiver catchments
    # note that the donor basins may be from multiple VPUs, but receivers are only from the current VPU
    gdf_donors = gpd.GeoDataFrame()
    gdf_receivers = gpd.GeoDataFrame()
    donor_basin_all = []
    for vpu1 in donor_vpus:
        # first get the qualified donors
        donor_dict = config.donor.get_qualified_donors(vpu1, donor_basins)
        donors0 = donor_dict[id_name]
        donor_basin_all.extend(donor_dict[config.donor.id_name])

        # read the hydrofabric file for the VPU
        file1 = config.general.hydrofabric_file[vpu]
        if vpu1 != vpu:
            # rename the hydrofabric file to match the current VPU
            file1 = config.general.hydrofabric_file[vpu].replace("vpu_" + vpu, "vpu_" + vpu1)
            # make sure the file exists
            if not Path(file1).is_file():
                raise FileNotFoundError(f"Hydrofabric file for VPU {vpu1} not found: {file1}")

        gdf = gpd.read_file(file1, layer="divides")
        gdf1 = gdf[gdf[id_name].isin(donors0)]
        donors = gdf1[id_name].tolist()

        # check if all donors are in the hydrofabric
        donors_missing = set(donors0) - set(donors)
        if len(donors_missing) > 0:
            logger.warning(f"Missing donors in hydrofabric: {donors_missing}")

        # gather donors and receivers in GeoDataFrame
        gdf_donors = pd.concat([gdf_donors, gdf1])
        if vpu1 == vpu:
            gdf_receivers = gdf[~gdf[id_name].isin(donors)]

    if gdf_receivers.empty:
        raise ValueError(f"No receivers found in VPU {vpu}. Please check the hydrofabric file and donor gage file.")

    # gdf_receivers = gdf_receivers.sample(n=500, replace=False) # randomly sample a small number of receivers for testing
    receivers = gdf_receivers[id_name].tolist()
    donors = gdf_donors[id_name].tolist()

    logger.info(f"Total number of donor basins in VPU {vpu}: {len(donor_basin_all)}")
    logger.info(f"Total number of donor catchments in vpu {vpu}: {len(donors)}")
    logger.info(f"Total number of receiver catchments in vpu {vpu}: {len(receivers)}")

    # compute the donor-receiver spatial distance
    out = config.output.spatial_distance
    dist_file = Path(out.path, "donor_receiver_dist_" + config.general.domain + "_vpu" + vpu + "." + out.format)
    if dist_file.exists():
        logger.info(f"Spatial distance file already exists: {dist_file}")
        df_spatial_dist = utils.read_table(dist_file)

        # check if the spatial distance data includes all donors and receivers
        # if not, identify the missing donors and receivers, compute the distance for them and add to the existing dataframe
        logger.info("Updating existing spatial distance file (if needed) to include all donors and receivers ...")
        df_spatial_dist, file_changed1 = update_spatial_distance_donors(
            id_name, gdf_donors, gdf_receivers, df_spatial_dist
        )
        df_spatial_dist, file_changed2 = update_spatial_distance_receivers(
            id_name, gdf_donors, gdf_receivers, df_spatial_dist
        )
        file_changed = file_changed1 or file_changed2

    else:
        logger.info("Compute donor-receiver spatial distance ...")
        start_time = time.time()
        df_spatial_dist = utils_algo.compute_pairwise_centroid_distances(gdf_donors, gdf_receivers, id_name, id_name)
        end_time = time.time()
        logger.info(f"Spatial distance computed in {end_time - start_time:.4f} seconds")
        file_changed = True

    # save the spatial distance data
    if out.save and file_changed:
        if not dist_file.parent.is_dir():
            dist_file.parent.mkdir(parents=True, exist_ok=True)

        # if the file already exists, make a backup
        if dist_file.is_file():
            backup_file = dist_file.with_suffix(".bak")
            dist_file.rename(backup_file)
            logger.info(f"Backup of existing spatial distance file created: {backup_file}")

        # save the spatial distance data
        utils.save_data(df_spatial_dist, dist_file, index=True)
        logger.info(f"Spatial distance data saved to {dist_file}")

    return donors, receivers, df_spatial_dist


def process_attr_data(
    config: cs.Config,
    vpu: str,
    donors: list,
    receivers: list,
    df_spatial_dist: pd.DataFrame,
) -> Tuple[list, list, pd.DataFrame]:
    """Process the attribute data for a given VPU from the config.

    Args:
        config: the config object
        vpu: the VPU code
        donors: list of donors
        receivers: list of receivers
        df_spatial_dist: dataframe of pairwise spatial distances between donors and receivers

    Returns:
        donors: new list of donors (after screening wtih the attribute data)
        receivers: new list of receivers (after screening wtih the attribute data)
        df_attrs_all: dataframe of all attribute data for the donors and receivers

    """
    id_name = config.general.id_name
    datasets = config.general.attr_dataset_list
    logger.info(f"Processing attribute data for VPU {vpu} ... datasets: {datasets}")

    df_attrs_all = []
    for dataset_name in datasets:
        dataset = getattr(config.attr_datasets, dataset_name)
        df_attrs = dataset.get_attr_data()

        df_attrs = df_attrs.rename(columns=lambda x: x if x == id_name else f"{dataset_name}_{x}")

        # subset the attribute data to only include donors and receivers for the current VPU
        # TODO: add functionality to add additional donors from neighboring VPUs
        df_attrs = df_attrs[df_attrs[id_name].isin(donors + receivers)]

        df_attrs_all.append(df_attrs)

    # Merge all attribute data frames column-wise, based on divide_id
    df_attrs_all = reduce(lambda left, right: pd.merge(left, right, on=id_name, how="outer"), df_attrs_all)

    # add a column to indicate whether the divide_id is a donor or receiver
    df_attrs_all["is_donor"] = df_attrs_all[id_name].isin(donors)
    # move the is_donor column to be the second column
    df_attrs_all = df_attrs_all[
        [id_name, "is_donor"] + [col for col in df_attrs_all.columns if col not in [id_name, "is_donor"]]
    ]

    # check if all donors have attribute data
    if not set(donors).issubset(df_attrs_all[id_name]):
        logger.warning(f"Not all donors are included in the attribute data for VPU {vpu}.")
        missing_donors = [x for x in donors if x not in df_attrs_all[id_name].values]
        logger.info(f"Missing donors: {missing_donors}")

    # check if all receivers have attribute data
    if not set(receivers).issubset(df_attrs_all[id_name]):
        logger.warning(f"Not all receivers are included in the attribute data for VPU {vpu}.")
        missing_receivers = [x for x in receivers if x not in df_attrs_all[id_name].values]
        logger.info(f"Missing receivers: {missing_receivers}")

    # reset donor and receiver lists based on the attribute data
    donors = df_attrs_all[df_attrs_all["is_donor"]][id_name].tolist()
    receivers = df_attrs_all[~df_attrs_all["is_donor"]][id_name].tolist()

    logger.info(f"Number of donors with attribute data: {len(donors)}")
    logger.info(f"Number of receivers with attribute data: {len(receivers)}")

    # check if all donors in attribute data are inlcuded in the columns of the spatial distance data
    if not set(donors).issubset(df_spatial_dist.columns):
        logger.warning(f"Not all donors in the attribute data are present in the spatial distance data for VPU {vpu}.")
        missing_donor_ids = [x for x in donors if x not in df_spatial_dist.columns]
        logger.info(f"Missing donors: {missing_donor_ids}")

    # check if all receivers in attribute data are inlcuded in the indices of the spatial distance data
    if not set(receivers).issubset(df_spatial_dist.index):
        logger.warning(
            f"Not all receivers in the attribute data are present in the spatial distance data for VPU {vpu}."
        )
        missing_receiver_ids = [x for x in receivers if x not in df_spatial_dist.index]
        logger.info(f"Missing receivers: {missing_receiver_ids}")

    # sort the attribute data by is_donor and divide_id
    df_attrs_all = df_attrs_all.sort_values(by=["is_donor", id_name], ascending=[False, True])

    # check percentage of missing data
    df_missing = df_attrs_all.isna().mean() * 100
    if df_missing.sum() > 0:
        logger.warning(f"There are missing data for attributes in vpu {vpu}")
        # logger.info(f"Missing data percentage for each attribute:\n{df_missing.loc[df_missing > 0]}")

        # plot the missing attribute counts
        po.plot_missing_attr_counts(config, vpu, df_attrs_all)

    # plot spatial map of attribute data
    po.plot_attribute_spatial_map(config, vpu, df_attrs_all)

    # save the attribute data
    out1 = config.output.attr_data_final
    if out1.save:
        if not Path(out1.path).is_dir():
            Path(out1.path).mkdir(parents=True, exist_ok=True)
        out_file = Path(out1.path, "attr_" + config.general.domain + "_vpu" + vpu + "." + out1.format)

        logger.info(f"Saving attribute data to {out_file}")
        utils.save_data(df_attrs_all, out_file)

    return donors, receivers, df_attrs_all


def set_snow_flag(df_attrs: pd.DataFrame, min_snow_frac: float) -> pd.DataFrame:
    """Set a boolean flag to indicate whether a catchment is snow-driven.

    Add a boolean 'snowy' column to existing attributes dataframe to indicate whether
    a catchment is snow-driven or not.

    Args:
        df_attrs: DataFrame of attributes for donors and receivers
        min_snow_frac: minimum snow_frac value for a catchment to be considered snow-driven

    Returns:
        New DataFrame of attributes with a new boolean column added to indicate whether the catchment is snow-driven

    """
    # detemine whether the catchments are snowy (as snowy and non-snowy catchments are processed separately)
    if "snow_frac" in [col.lower() for col in df_attrs.columns]:
        # check if the snow_frac column is present in the attribute data
        n1 = df_attrs["snow_frac"].isna().sum()
        if n1 > 0:
            logger.warning(f"There are {n1} missing values in the snow_frac column. Setting them to non-snowy.")
            df_attrs["snow_frac"] = df_attrs["snow_frac"].fillna(0.0)

        # create a new column to indicate whether the catchment is snowy
        df_attrs["snowy"] = df_attrs["snow_frac"].apply(lambda x: True if x >= min_snow_frac else False)

    else:
        # if the snow_frac column is not present, set all catchments to non-snowy
        df_attrs["snowy"] = False
        logger.warning(
            "The snow_frac column is not present in the attribute data. All catchments are set to non-snowy."
        )

    return df_attrs


def generate_pairing(conf: cs.Config, vpu: str, df_attrs_all: pd.DataFrame, df_dist_spatial: pd.DataFrame):
    """Conduct donor-receiver pairing for a given VPU based on the configuration.

    For a given VPU, generate donor-receiver pairing results for each algorithm selected in the configuration,
    based on the attributes and spatial distance DataFrame.

    Args:
        conf: configuration
        vpu: VPU to conduct pairing algorithms for
        df_attrs_all: dataframe containing the full attribute data for all receivers and donors
        df_dist_spatial: dataframe containing the pair-wise spatial distance between donors and receivers

    Returns:
        None, but saves the pairing results to a file.

    """
    # pairing/regionalization algorithms
    functions = {
        "proximity": funcs_dist,
        "gower": funcs_dist,
        "urf": funcs_dist,
        "kmeans": funcs_clust,
        "kmedoids": funcs_clust,
        "hdbscan": funcs_clust,
        "birch": funcs_clust,
    }
    funcs = functions.keys()

    # run only those algorithms specified to run in the config file
    funcs = [x for x in funcs if x in conf.general.algorithm_list]

    logger.info(f"Algorithms to run: {funcs}")

    # loop through regionalization algorithms to generate donor-receiver pairings for each algorithm/scenario combination
    for func1 in funcs:
        file_name_str = "pairs_" + func1 + "_" + conf.general.domain + "_vpu" + vpu
        outfile = conf.output.pairs.get_file_path(file_name_str)

        if outfile.exists():
            logger.info(f"Pair file already exist: {outfile}")
            logger.info(f"Skip the current run: {func1}")
        else:
            logger.info(f"\nIdentify donors for VPU {vpu} using: {func1}\n")
            df_donor_all = pd.DataFrame()
            start_time = time.time()
            config1 = conf.model_dump()["algorithms"][func1]
            config1["max_spa_dist"] = conf.model_dump()["algorithms"]["general"]["max_spa_dist"]
            config1["njobs"] = conf.model_dump()["general"]["n_procs"]
            config1["non_attr_cols"] = ["divide_id", "is_donor", "snowy"]
            config1["attrs"] = {
                "main": [x for x in df_attrs_all.columns if x not in config1["non_attr_cols"]],
                "base": ["ngen_elevation", "ngen_slope", "ngen_aspect"],
            }
            df_donor_all = functions[func1].func(config1, df_attrs_all, df_dist_spatial, func1)

            # save donor receiver pairing to csv file
            conf.output.pairs.save_data(df_donor_all, outfile)
            logger.info(f"Pairing results saved to {outfile}")
            logger.info(f"Donor-receiver pairing for VPU {vpu} using {func1} completed.")
            end_time = time.time()
            logger.info(f"Execution time: {end_time - start_time:.4f} seconds")

        # plot the results if requested
        po.plot_pairing_outputs(conf, vpu, func1, outfile)
