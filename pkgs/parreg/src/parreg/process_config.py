import yaml
import pandas as pd
import geopandas as gpd
import time
from typing import Any, Tuple
from pydantic import BaseModel,ValidationError
import re
from pathlib import Path
from functools import reduce
from . import config_schema as cs
from . import utils, utils_algo
import logging
logger = logging.getLogger(__name__)

def expand_with_vpu(string_with_vpu: str, context: dict) -> dict:
    
    """
    Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
    Returns a dictionary where keys are vpu codes and values are the formatted strings.
    """

    if "{vpu_list}" not in string_with_vpu or "vpu_list" not in context:
        return {"default": string_with_vpu.format(**context)}

    return {
        vpu: string_with_vpu.format(**{**context, "vpu_list": vpu})
        for vpu in context["vpu_list"]
    }

def recursive_substitute(obj: Any, context: dict) -> Any:
    """
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
            if '{vpu_list}' in obj and 'vpu_list' in context:
                # If the string contains {vpu} and vpu_list is in context, expand it and substitute the placeholders
                return expand_with_vpu(obj, context)            
            else: # Otherwise, just substitute the placeholders
                return obj.format(**context)
        except KeyError:
            return obj  # leave unchanged if context is incomplete

    else:
        return obj  # return as-is if not str, dict, or BaseModel
    

def validate_by_section(config:dict) -> dict:
    """
    Perform pydantic validation separately for different sections of the config file to 
    allow specific validation for certain sections

    Args:
        config: dictionary of config prior to validation
    
    Return:
        Dictionary of config after validation

    """
    # Define the mapping of section names to Pydantic models
    section_map = {
        'general': cs.GeneralConfig,
        'donor': cs.DonorConfig,
        'attr_datasets': cs.AttrDatasets,
        'output': cs.OutputConfig,
        'algorithms': cs.AlgorithmConfig,
    }

    # Define the mapping of algorithm names to Pydantic models
    algorithm_map = {
        'general': cs.AlgoGeneral,
        'gower': cs.Gower,
        'urf': cs.URF,
        'kmeans': cs.KMeans,
        'kmedoids': cs.KMedoids,
        'hdbscan': cs.HDBSCAN,
        'birch': cs.Birch,
    }

    valid_config = dict()
    for section_name, section_content in config.items():

        if section_name != 'algorithms':
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

def find_occurrences(obj, target, path=""):
    """
    Recursively find occurrences of a target string in a Pydantic model, dictionary, or list.
    
    Args:
        obj: The object to search (can be a Pydantic model, dictionary, or list).
        target: The target string to find. 
    
    returns:
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
    """
    Load a YAML file, validate its structure using Pydantic, and substitue placeholders in the config.

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
        #config.donor.check_files()
        out = config.output.config_final
        if out.save:
            logger.info(f"Saving config to {out.path}")
            if Path(out.path).is_file():
                utils.save_data(config, Path(out.path))
            elif Path(out.path).is_dir():                
                utils.save_data(config, Path(out.path, 'config_final.' + out.format))
        
        return config
        
    except ValidationError as e:
        raise Exception(f'Validation Error: {e}')
    except Exception as e:
        raise Exception(f'Error loading YAML file: {e}')

def get_donors_receivers(config:cs.Config, vpu: str) -> Tuple[list, list, pd.DataFrame]:
    """
    Get the donors and receivers for a given VPU from the config.
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

    # first get the qualified donors
    donors_dict = config.donor.get_qualified_donors(vpu)
    donors0 = donors_dict[id_name]

    # read the hydrofabric file and get the donors and receivers    
    gdf = gpd.read_file(config.general.hydrofabric_file[vpu], layer = 'divides')
    gdf_donors = gdf[gdf[id_name].isin(donors0)]
    donors = gdf_donors[id_name].tolist()
   
    # check if all donors are in the hydrofabric
    donors_missing = set(donors0) - set(donors)
    if len(donors_missing) > 0:
        logger.warning(f"Missing donors in hydrofabric: {donors_missing}")
    
    gdf_receivers = gdf[~gdf[id_name].isin(donors0)]
    # randomly sample a small number of receivers to speed up testing
    gdf_receivers = gdf_receivers.sample(n=500, replace=False)    
    receivers = gdf_receivers[id_name].tolist()
    logger.info(f"Total number of donors in vpu {vpu}: {len(donors)}")
    logger.info(f"Total number of receivers in vpu {vpu}: {len(receivers)}")

    # compute the donor-receiver spatial distance
    out = config.output.spatial_distance
    dist_file = Path(out.path, 'donor_receiver_dist_' + config.general.domain + '_vpu' + vpu + '.' + out.format)
    if dist_file.exists():
        logger.info(f"Spatial distance file already exists: {dist_file}\nSkip computing.")
        df_spatial_dist = utils.read_table(dist_file)
        #TODO: check if the spatial distance data includes all pairs of donors and receivers
        # if not, identify the missing pairs and compute the distance for them
    else:
        logger.info(f'Compute donor-receiver spatial distance ...')
        start_time = time.time()
        df_spatial_dist = utils_algo.compute_pairwise_centroid_distances(gdf_donors, gdf_receivers, id_name, id_name)
        end_time = time.time()
        logger.info(f"Spatial distance comptued in {end_time - start_time:.4f} seconds")

        # save the spatial distance data
        if out.save:
            if not dist_file.parent.is_dir():
                dist_file.parent.mkdir(parents=True, exist_ok=True)
            
            utils.save_data(df_spatial_dist, dist_file, index=True)
            logger.info(f"Spatial distance data saved to {dist_file}")  
    
    return donors, receivers, df_spatial_dist

def process_attr_data(
        config:cs.Config, 
        vpu: str, 
        donors: list, 
        receivers: list, 
        df_spatial_dist:pd.DataFrame,
) -> Tuple[list, list, pd.DataFrame]:

    """
    Process the attribute data for a given VPU from the config.
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
        #TODO: add functionality to add additional donors from neighboring VPUs
        df_attrs = df_attrs[df_attrs[id_name].isin(donors + receivers)]

        df_attrs_all.append(df_attrs)

    # Merge all attribute data frames column-wise, based on divide_id
    df_attrs_all= reduce(
        lambda left, right: pd.merge(left, right, on=id_name, how='outer'),
        df_attrs_all
    )

    # add a column to indicate whether the divide_id is a donor or receiver
    df_attrs_all['is_donor'] = df_attrs_all[id_name].isin(donors)
    # move the is_donor column to be the second column
    df_attrs_all = df_attrs_all[[id_name, 'is_donor'] + [col for col in df_attrs_all.columns if col not in [id_name, 'is_donor']]]

    # check if all donors have attribute data
    if not set(donors).issubset(df_attrs_all[id_name]):
        logger.warning(f"Not all donors are included in the attribute data for VPU {vpu}.")
        missing_donors = [x for x in donors if x not in df_attrs_all[id_name].values]
        print("Missing donors:")
        print(missing_donors)

    # check if all receivers have attribute data
    if not set(receivers).issubset(df_attrs_all[id_name]):
        logger.warning(f"Not all receivers are included in the attribute data for VPU {vpu}.")
        missing_receivers = [x for x in receivers if x not in df_attrs_all[id_name].values]
        print("Missing receivers:")
        print(missing_receivers)

    # reset donor and receiver lists based on the attribute data
    donors = df_attrs_all[df_attrs_all['is_donor']][id_name].tolist()
    receivers = df_attrs_all[~df_attrs_all['is_donor']][id_name].tolist()

    print(f'Number of donors with attribute data: {len(donors)}')
    print(f'Number of receivers with attribute data: {len(receivers)}')

    # check if all donors in attribute data are inlcuded in the columns of the spatial distance data
    if not set(donors).issubset(df_spatial_dist.columns):
        logger.warning(f"Not all donors in the attribute data are present in the spatial distance data for VPU {vpu}.")
        missing_donor_ids = [x for x in donors if x not in df_spatial_dist.columns]
        print("Missing donors:")
        print(missing_donor_ids)

    # check if all receivers in attribute data are inlcuded in the indices of the spatial distance data
    if not set(receivers).issubset(df_spatial_dist.index):
        logger.warning(f"Not all receivers in the attribute data are present in the spatial distance data for VPU {vpu}.")
        missing_receiver_ids = [x for x in receivers if x not in df_spatial_dist.index]
        print("Missing receivers:")
        print(missing_receiver_ids)

    # sort the attribute data by is_donor and divide_id
    df_attrs_all = df_attrs_all.sort_values(by=['is_donor', id_name], ascending=[False, True])

    # check percentage of missing data
    df_missing = df_attrs_all.isna().mean()*100
    if df_missing.sum()>0:
        logger.warning(f"There are missing data for attributes in vpu {vpu}")
        print("Missing data percentage for each attribute:")
        print(df_missing.loc[df_missing > 0])

    # save the attribute data
    out1 = config.output.attr_data_final
    if out1.save:
        if not Path(out1.path).is_dir():
            Path(out1.path).mkdir(parents=True, exist_ok=True)
        out_file = Path(out1.path, 'attr_' + config.general.domain + '_vpu' + vpu + '.' + out1.format)

        logger.info(f"Saving attribute data to {out_file}")
        utils.save_data(df_attrs_all, out_file)

    return donors, receivers, df_attrs_all