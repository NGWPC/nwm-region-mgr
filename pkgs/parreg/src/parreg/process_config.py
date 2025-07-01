"""Process configuration."""

import logging
import time
from functools import lru_cache, reduce
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

logger = logging.getLogger(__name__)


class RegionalizationProcessor:
    """Regionalization Processor."""

    def __init__(self, config_file: str | Path):
        """Initialize regionalzation processor."""
        self.config_file = config_file
        self.config = self.load_and_validate_config

    def expand_with_vpu(self, string_with_vpu: str, context: dict) -> dict:
        """Expand a string with {vpu_list} placeholders.

        Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
        Returns a dictionary where keys are vpu codes and values are the formatted strings.
        """
        if "{vpu_list}" not in string_with_vpu or "vpu_list" not in context:
            return {"default": string_with_vpu.format(**context)}

        return {
            vpu: string_with_vpu.format(**{**context, "vpu_list": vpu})
            for vpu in context["vpu_list"]
        }

    def recursive_substitute(self, obj: Any, context: dict) -> Any:
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
            substituted = self.recursive_substitute(data, context)
            return obj.__class__(**substituted)

        elif isinstance(obj, dict):
            return {k: self.recursive_substitute(v, context) for k, v in obj.items()}

        elif isinstance(obj, str):
            try:
                if "{vpu_list}" in obj and "vpu_list" in context:
                    # If the string contains {vpu} and vpu_list is in context, expand it and substitute the placeholders
                    return self.expand_with_vpu(obj, context)
                else:  # Otherwise, just substitute the placeholders
                    return obj.format(**context)
            except KeyError:
                return obj  # leave unchanged if context is incomplete

        else:
            return obj  # return as-is if not str, dict, or BaseModel

    def validate_by_section(self, config: dict) -> dict:
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

    def find_occurrences(self, obj: Any, target: str, path: str = "") -> list:
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
                occurrences.extend(self.find_occurrences(v, target, new_path))

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                occurrences.extend(self.find_occurrences(item, target, new_path))

        elif isinstance(obj, str):
            if target in obj:
                occurrences.append(path)

        return occurrences

    @property
    @lru_cache
    def load_and_validate_config(self):
        """Load a YAML file, validate its structure using Pydantic, and substitute placeholders in the config.

        Args:
            file_path: path to the config file

        """
        try:
            with open(Path(self.config_file), "r") as file:
                data = yaml.safe_load(file)

            # validate the config
            validated_config = self.validate_by_section(data)
            config = cs.Config(**validated_config)

            # resolve placeholders in the config
            context = {
                "domain": config.general.domain,
                "run_name": config.general.run_name,
                "base_dir": config.general.base_dir,
                "vpu_list": config.general.vpu_list,
            }
            config = self.recursive_substitute(config, context)

            # additional validation after substitution
            # config.donor.check_files()
            out = config.output.config_final
            if out.save:
                logger.info(f"Saving config to {out.path}")
                if Path(out.path).is_file():
                    utils.save_data(config, Path(out.path))
                elif Path(out.path).is_dir():
                    utils.save_data(
                        config, Path(out.path, "config_final." + out.format)
                    )

            return config

        except ValidationError as e:
            raise Exception(f"Validation Error: {e}")
        except Exception as e:
            raise Exception(f"Error loading YAML file: {e}")

    def set_vpu(self, vpu: str):
        """Set the vpu."""
        self.vpu = vpu
        self.donor_receiver_gdfs.cache_clear()

    @property
    @lru_cache
    def donors_df(self) -> pd.DataFrame:
        """Donors."""
        donors = utils.read_table(self.config.donor.donor_gage_file)
        if donors.empty:
            raise ValueError(
                f"No donors found in the donor gage file: {self.config.donor.donor_gage_file}"
            )
        if "longitude" not in donors.columns or "latitude" not in donors.columns:
            raise ValueError(
                f"Donor gage file must contain 'longitude' and 'latitude' columns: {self.config.donor.donor_gage_file}"
            )
        if "gage_id" not in donors.columns:
            raise ValueError(
                f"Donor gage file must contain 'gage_id' column: {self.config.donor.donor_gage_file}"
            )
        return donors

    @property
    @lru_cache
    def donors_gdf(self) -> gpd.GeoDataFrame:
        """Create a GeoDataFrame of donors with geometry as points."""
        return gpd.GeoDataFrame(
            self.donors_df,
            geometry=[
                Point(xy)
                for xy in zip(self.donors_df["longitude"], self.donors_df["latitude"])
            ],
            crs="EPSG:4326",
        )

    @property
    def hydrofabric_gdf(self) -> gpd.GeoDataFrame:
        """Hydrofabric geodataframe with only valid geometries."""
        gdf = gpd.read_file(
            self.config.general.hydrofabric_file[self.vpu], layer="divides"
        )
        return gdf[gdf.is_valid]

    @property
    @lru_cache
    def donor_gdf_3857(self):
        """Create a GeoDataFrame of donors with geometry as points projected to 3857."""
        return self.donors_gdf.to_crs(3857)

    @property
    def hydrofabric_gdf_3857(self):
        """Hydrofabric geodataframe with only valid geometries projected to 3857."""
        return self.hydrofabric_gdf.to_crs(3857)

    @property
    def hydrofabric_buffered_polygon(self):
        """Buffered hydrofabric Polygon."""
        # dissolve all polygons into one before buffering
        combined_geom = unary_union(self.hydrofabric_gdf_3857.geometry)

        # Create a buffer around the VPU polygon
        return combined_geom.buffer(self.config.donor.buffer_km * 1000)

    @property
    def donor_basins(self) -> list:
        """Get the donor basins for a given VPU from the config.

        Returns:
            donor_basins: list of donor basins (gage_ids) within the buffered VPU polygon

        """
        # Find donors in the buffered VPU
        donor_basins = self.donor_gdf_3857[
            self.donor_gdf_3857.geometry.within(self.hydrofabric_buffered_polygon)
        ]["gage_id"].tolist()

        if not donor_basins:
            logger.warning(
                "No donor basins found. Please check the donor gage file and hydrofabric file."
            )

        return donor_basins

    def update_spatial_distance_donors(
        self,
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
            missing_donors_gdf = donors_gdf[
                donors_gdf["divide_id"].isin(missing_donors)
            ]

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
        self,
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
            missing_receivers_gdf = receivers_gdf[
                receivers_gdf["divide_id"].isin(missing_receivers)
            ]

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

    @property
    def general_id_name(self):
        """Id_name from the config."""
        return self.config.general.id_name

    @property
    def donor_vpus(self):
        """Determine the VPUs of the donor basins."""
        df_cwt = utils.read_table(self.config.donor.donor_ngen_cwt_file)
        return (
            df_cwt[df_cwt["gage_id"].isin(self.donor_basins)]["vpuid"].unique().tolist()
        )

    def build_hydrofabric_path(self, vpu1):
        """Build hydrofabric path."""
        file1 = self.config.general.hydrofabric_file[self.vpu]
        if vpu1 != self.vpu:
            # rename the hydrofabric file to match the current VPU
            file1 = self.config.general.hydrofabric_file[self.vpu].replace(
                "vpu_" + self.vpu, "vpu_" + vpu1
            )
            # make sure the file exists
            if not Path(file1).is_file():
                raise FileNotFoundError(
                    f"Hydrofabric file for VPU {vpu1} not found: {file1}"
                )
        return file1

    @lru_cache
    def donor_receiver_gdfs(self):
        """Get valid donor and receiver geodataframes."""
        # loop through the VPUs of the donor basins to get donor & receiver catchments
        # note that the donor basins may be from multiple VPUs, but receivers are only from the current VPU
        gdf_donors = gpd.GeoDataFrame()
        gdf_receivers = gpd.GeoDataFrame()
        donor_basin_all = []
        for vpu1 in self.donor_vpus:
            # first get the qualified donors
            donor_dict = self.config.donor.get_qualified_donors(vpu1, self.donor_basins)
            donors0 = donor_dict[self.general_id_name]
            donor_basin_all.extend(donor_dict[self.config.donor.id_name])

            file1 = self.build_hydrofabric_path(vpu1)
            gdf = gpd.read_file(file1, layer="divides")
            gdf1 = gdf[gdf[self.general_id_name].isin(donors0)]
            donors = gdf1[self.general_id_name].tolist()

            # check if all donors are in the hydrofabric
            donors_missing = set(donors0) - set(donors)
            if len(donors_missing) > 0:
                logger.warning(f"Missing donors in hydrofabric: {donors_missing}")

            # gather donors and receivers in GeoDataFrame
            gdf_donors = pd.concat([gdf_donors, gdf1])
            if vpu1 == self.vpu:
                gdf_receivers = gdf[~gdf[self.general_id_name].isin(donors)]

            if gdf_receivers.empty:
                raise ValueError(
                    f"No receivers found in VPU {self.vpu}. Please check the hydrofabric file and donor gage file."
                )
        logger.info(
            f"Total number of donor basins in VPU {self.vpu}: {len(donor_basin_all)}"
        )
        return gdf_receivers, gdf_donors

    @property
    def gdf_receivers(self) -> gpd.GeoDataFrame:
        """Geodataframe of receivers."""
        gdf_receivers, _ = self.donor_receiver_gdfs()
        return gdf_receivers

    @property
    def gdf_donors(self) -> gpd.GeoDataFrame:
        """Geodataframe of donors."""
        _, gdf_donors = self.donor_receiver_gdfs()
        return gdf_donors

    @property
    def receivers(self) -> list:
        """Receivers."""
        # gdf_receivers = gdf_receivers.sample(n=500, replace=False) # randomly sample a small number of receivers for testing
        return self.gdf_receivers[self.general_id_name].tolist()

    @property
    def donors(self) -> list:
        """Donors."""
        return self.gdf_donors[self.general_id_name].tolist()

    @property
    def dist_file(self) -> Path:
        """Build dist file path."""
        out = self.config.output.spatial_distance
        return Path(
            out.path,
            f"donor_receiver_dist_{self.config.general.domain}_vpu{self.vpu}.{out.format}",
        )

    def compute_donor_receiver_spatial_distance(self):
        """Compute spatial distance."""
        if self.dist_file.exists():
            logger.info(f"Spatial distance file already exists: {self.dist_file}")
            df_spatial_dist = utils.read_table(self.dist_file)

            # check if the spatial distance data includes all donors and receivers
            # if not, identify the missing donors and receivers, compute the distance for them and add to the existing dataframe
            logger.info(
                "Updating existing spatial distance file (if needed) to include all donors and receivers ..."
            )
            df_spatial_dist, file_changed1 = self.update_spatial_distance_donors(
                self.general_id_name,
                self.gdf_donors,
                self.gdf_receivers,
                df_spatial_dist,
            )
            df_spatial_dist, file_changed2 = self.update_spatial_distance_receivers(
                self.general_id_name,
                self.gdf_donors,
                self.gdf_receivers,
                df_spatial_dist,
            )
            file_changed = file_changed1 or file_changed2

        else:
            logger.info("Compute donor-receiver spatial distance...")
            start_time = time.time()
            df_spatial_dist = utils_algo.compute_pairwise_centroid_distances(
                self.gdf_donors,
                self.gdf_receivers,
                self.general_id_name,
                self.general_id_name,
            )
            end_time = time.time()
            logger.info(
                f"Spatial distance computed in {end_time - start_time:.4f} seconds"
            )
            file_changed = True
        return df_spatial_dist, file_changed

    def write_spatial_file(self, file_changed: bool, df_spatial_dist: pd.DataFrame):
        """Save the spatial distance data."""
        if self.config.output.spatial_distance.save and file_changed:
            if not self.dist_file.parent.is_dir():
                self.dist_file.parent.mkdir(parents=True, exist_ok=True)

            # if the file already exists, make a backup
            if self.dist_file.is_file():
                backup_file = self.dist_file.with_suffix(".bak")
                self.dist_file.rename(backup_file)
                logger.info(
                    f"Backup of existing spatial distance file created: {backup_file}"
                )

            # save the spatial distance data
            utils.save_data(df_spatial_dist, self.dist_file, index=True)
            logger.info(f"Spatial distance data saved to {self.dist_file}")

    def get_donors_receivers(self):
        """Get the donors and receivers for a given VPU from the config."""
        logger.info(
            f"Total number of donor catchments in vpu {self.vpu}: {len(self.donors)}"
        )
        logger.info(
            f"Total number of receiver catchments in vpu {self.vpu}: {len(self.receivers)}"
        )

        # compute spatial distance file
        df_spatial_dist, file_changed = self.compute_donor_receiver_spatial_distance()

        # save spatial distance file
        self.write_spatial_file(df_spatial_dist, file_changed)

        self.df_spatial_dist = df_spatial_dist

    @property
    def datasets(self) -> list:
        """List of datasets."""
        return self.config.general.attr_dataset_list

    @property
    @lru_cache
    def df_attrs_all(self) -> pd.DataFrame:
        """Dataframe containing all attributes."""
        df_attrs_all = []
        for dataset_name in self.datasets:
            dataset = getattr(self.config.attr_datasets, dataset_name)
            df_attrs = dataset.get_attr_data()

            df_attrs = df_attrs.rename(
                columns=lambda x: x
                if x == self.general_id_name
                else f"{dataset_name}_{x}"
            )

            # subset the attribute data to only include donors and receivers for the current VPU
            # TODO: add functionality to add additional donors from neighboring VPUs
            df_attrs = df_attrs[
                df_attrs[self.general_id_name].isin(self.donors + self.receivers)
            ]

            df_attrs_all.append(df_attrs)

        # Merge all attribute data frames column-wise, based on divide_id
        df_attrs_all = reduce(
            lambda left, right: pd.merge(
                left, right, on=self.general_id_name, how="outer"
            ),
            df_attrs_all,
        )

        # add a column to indicate whether the divide_id is a donor or receiver
        df_attrs_all["is_donor"] = df_attrs_all[self.general_id_name].isin(self.donors)
        # move the is_donor column to be the second column
        return df_attrs_all[
            [self.general_id_name, "is_donor"]
            + [
                col
                for col in df_attrs_all.columns
                if col not in [self.general_id_name, "is_donor"]
            ]
        ]

    def check_missing_attrs(self, ids: list, list_type: str):
        """Check for missing attributes."""
        if list_type not in ["donors", "receivers"]:
            raise TypeError(
                f"Expected either 'donors' or 'receivers'; received '{list_type}'"
            )

        if not set(ids).issubset(self.df_attrs_all[self.general_id_name]):
            logger.warning(
                f"Not all {list_type} are included in the attribute data for VPU {self.vpu}."
            )
            missing_ids = [
                x
                for x in ids
                if x not in self.df_attrs_all[self.general_id_name].values
            ]
            logger.info(f"Missing {list_type}: {missing_ids}")

    @property
    def donors_w_attrs(self):
        """Donors with attributes."""
        return self.df_attrs_all[self.df_attrs_all["is_donor"]][
            self.general_id_name
        ].tolist()

    @property
    def receivers_w_attrs(self):
        """Receivers with attributes."""
        return self.df_attrs_all[~self.df_attrs_all["is_donor"]][
            self.general_id_name
        ].tolist()

    @property
    def number_of_receivers_w_attrs(self):
        """Number of receivers with attributes."""
        return len(self.receivers_w_attrs)

    @property
    def number_of_donors_w_attrs(self):
        """Number of donors with attributes."""
        return len(self.donors_w_attrs)

    def check_attrs_in_spatial_distance_data(
        self, ids: list, list_type: str, df_spatial_dist: pd.DataFrame
    ):
        """Check if all donors in attribute data are included in the columns of the spatial distance data."""
        if list_type not in ["donors", "receivers"]:
            raise TypeError(
                f"Expected either 'donors' or 'receivers'; received '{list_type}'"
            )

        if not set(ids).issubset(df_spatial_dist.columns):
            logger.warning(
                f"Not all {list_type} in the attribute data are present in the spatial distance data for VPU {self.vpu}."
            )
            missing_donor_ids = [x for x in ids if x not in df_spatial_dist.columns]
            logger.info(f"Missing {list_type}: {missing_donor_ids}")

    @property
    def sorted_df_attrs_all(self):
        """Df_attrs_all sorted by is_donor and divide_id."""
        return self.df_attrs_all.sort_values(
            by=["is_donor", self.general_id_name], ascending=[False, True]
        )

    def check_percent_missing(self):
        """Check percentage of missing data."""
        df_missing = self.sorted_df_attrs_all.isna().mean() * 100
        if df_missing.sum() > 0:
            logger.warning(f"There are missing data for attributes in vpu {self.vpu}")
            logger.info(
                f"Missing data percentage for each attribute:\n{df_missing.loc[df_missing > 0]}"
            )

    def save_attribute_data(self):
        """Save the attribute data."""
        out1 = self.config.output.attr_data_final
        if out1.save:
            if not Path(out1.path).is_dir():
                Path(out1.path).mkdir(parents=True, exist_ok=True)
            out_file = Path(
                out1.path,
                f"attr_{self.config.general.domain}_vpu{self.vpu}.{out1.format}",
            )

            logger.info(f"Saving attribute data to {out_file}")
            utils.save_data(self.sorted_df_attrs_all, out_file)

    def process_attr_data(self):
        """Process the attribute data for a given VPU from the config."""
        logger.info(
            f"Processing attribute data for VPU {self.vpu} ... datasets: {self.datasets}"
        )

        # check if all donors/receivers have attributes
        self.check_missing_attrs(self.donors, "donors")
        self.check_missing_attrs(self.receivers, "receivers")

        logger.info(
            f"Number of donors with attribute data: {self.number_of_donors_w_attrs}"
        )
        logger.info(
            f"Number of receivers with attribute data: {self.number_of_receivers_w_attrs}"
        )

        self.check_attrs_in_spatial_distance_data(
            self.donors_w_attrs, "donors", self.df_spatial_dist
        )
        self.check_attrs_in_spatial_distance_data(
            self.receivers_w_attrs, "receivers", self.df_spatial_dist
        )

        # check percent missing
        self.check_percent_missing()

        # save attribute data
        self.save_attribute_data()

    def set_snow_flag(self, df_attrs: pd.DataFrame) -> pd.DataFrame:
        """Set a boolean flag to indicate whether a catchment is snow-driven.

        Add a boolean 'snowy' column to existing attributes dataframe to indicate whether
        a catchment is snow-driven or not.

        Args:
            df_attrs: DataFrame of attributes for donors and receivers

        Returns:
            New DataFrame of attributes with a new boolean column added to indicate whether the catchment is snow-driven

        """
        # determine whether the catchments are snowy (as snowy and non-snowy catchments are processed separately)
        if "snow_frac" in [col.lower() for col in df_attrs.columns]:
            # check if the snow_frac column is present in the attribute data
            n1 = df_attrs["snow_frac"].isna().sum()
            if n1 > 0:
                logger.warning(
                    f"There are {n1} missing values in the snow_frac column. Setting them to non-snowy."
                )
                df_attrs["snow_frac"] = df_attrs["snow_frac"].fillna(0.0)

            # create a new column to indicate whether the catchment is snowy
            df_attrs["snowy"] = df_attrs["snow_frac"].apply(
                lambda x: True
                if x >= self.config.algorithms.general.min_snow_frac
                else False
            )

        else:
            # if the snow_frac column is not present, set all catchments to non-snowy
            df_attrs["snowy"] = False
            logger.warning(
                "The snow_frac column is not present in the attribute data. All catchments are set to non-snowy."
            )

        return df_attrs

    @property
    def functions(self) -> dict:
        """Pairing/regionalization algorithms."""
        return {
            "proximity": funcs_dist,
            "gower": funcs_dist,
            "urf": funcs_dist,
            "kmeans": funcs_clust,
            "kmedoids": funcs_clust,
            "hdbscan": funcs_clust,
            "birch": funcs_clust,
        }

    @property
    def function_names(self) -> list:
        """Run only those algorithms specified to run in the config file."""
        return [
            x for x in self.functions.keys() if x in self.config.general.algorithm_list
        ]

    def construct_output_filepath(self, function_name: str) -> Path:
        """Construct output filepath."""
        file_name_str = (
            f"pairs_{function_name}_{self.config.general.domain}_vpu{self.vpu}"
        )
        return self.config.output.pairs.get_file_path(file_name_str)

    def update_algorithm_config(
        self, function_name: str, df_attrs_all: pd.DataFrame
    ) -> dict:
        """Update the algorithm config."""
        algorithm_config = self.config.model_dump()["algorithms"][function_name]
        algorithm_config["max_spa_dist"] = self.config.model_dump()["algorithms"][
            "general"
        ]["max_spa_dist"]
        algorithm_config["njobs"] = self.config.model_dump()["general"]["n_procs"]
        algorithm_config["non_attr_cols"] = ["divide_id", "is_donor", "snowy"]
        algorithm_config["attrs"] = {
            "main": [
                x
                for x in df_attrs_all.columns
                if x not in algorithm_config["non_attr_cols"]
            ],
            "base": ["ngen_elevation", "ngen_slope", "ngen_aspect"],
        }
        return algorithm_config

    def generate_pairing(
        self,
        df_attrs_all: pd.DataFrame,
        df_dist_spatial: pd.DataFrame,
    ):
        """Conduct donor-receiver pairing for a given VPU based on the configuration.

        For a given VPU, generate donor-receiver pairing results for each algorithm selected in the configuration,
        based on the attributes and spatial distance DataFrame.

        Args:
            df_attrs_all: dataframe containing the full attribute data for all receivers and donors
            df_dist_spatial: dataframe containing the pair-wise spatial distance between donors and receivers

        Returns:
            None. The pairing results are saved to designed locations based on the configurations.

        """
        logger.info(f"Algorithms to run: {self.function_names}")

        # loop through regionalization algorithms to generate donor-receiver pairings for each algorithm/scenario combination
        for function_name in self.function_names:
            outfile = self.construct_output_filepath(function_name)
            if outfile.exists():
                logger.info(f"Pair file already exist: {outfile}")
                logger.info(f"Skip the current run: {function_name}")
                continue

            logger.info(
                f"\nIdentify donors for VPU {self.vpu} using: {function_name}\n"
            )
            start_time = time.time()

            algorithm_config = self.update_algorithm_config(function_name, df_attrs_all)

            # execute function
            df_donor_all = self.functions[function_name].func(
                algorithm_config, df_attrs_all, df_dist_spatial, function_name
            )

            # save donor receiver pairing to csv file
            self.config.output.pairs.save_data(df_donor_all, outfile)
            logger.info(f"Pairing results saved to {outfile}")

            end_time = time.time()
            logger.info(f"Execution time: {end_time - start_time:.4f} seconds")
