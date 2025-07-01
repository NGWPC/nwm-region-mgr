"""Functions for generating plots from the output data of regionalization.

plot_outputs.py

Functions:
- plot_attribute_spatial_map: Plots spatial maps of selected attributes for catchments in a VPU.
- plot_missing_attr_counts: Plots the number of catchments with missing values for each selected attribute.
- plot_donor_spatial_map: Plots the spatial distribution of donors within a VPU and its buffer zone.
- plot_pairing_outputs: Generates plots for the donor-receiver pairings, including histograms and spatial maps.

"""

import logging
import re
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from shapely.geometry import Point
from shapely.ops import unary_union

from parreg.logging_config import setup_logging

from . import config_schema as cs
from . import utils

setup_logging()
logger = logging.getLogger(__name__)


def _contruct_outfile_name(d1: dict) -> Path:
    """Construct the output filename based on the provided dictionary.

    Args:
        d1: dict
            Dictionary containing information needed to construct the filename.

    Returns:
        Path
            The constructed output filename.

    """
    fn_parts = [
        d1["plot_type"],
        d1["var_str"],
    ]
    if d1.get("algorithm"):
        fn_parts.append(d1["algorithm"])
    fn_parts.extend([d1["domain"], f"vpu{d1['vpu']}.png"])
    filename = "_".join(fn_parts)

    outfile = Path(d1["out_path"], d1["plot_subdir"], filename)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    return outfile


def _plot_spatial_map(gdf: gpd.GeoDataFrame, d1: dict) -> None:
    """Generate a spatial map plot for the given data.

    Args:
        gdf : gpd.GeoDataFrame
            GeoDataFrame containing the data to be plotted.
        d1: dict
            Information needed for creating the plot

    """
    # check if the required column exists
    if d1["column"] not in gdf:
        logger.warning(f"Column '{d1['column']}' not found in gdf. Skipping spatial map plot.")
        return

    _, ax = plt.subplots(figsize=(8, 6))

    # project the GeoDataFrame to lat/lon for plotting
    gdf = gdf.to_crs(epsg=4326)

    # create spatial map
    gdf.plot(ax=ax, column=d1["column"], cmap="viridis", legend=True, edgecolor=None)

    # add outer boundary of the VPU
    combined_polygon = unary_union(gdf.geometry)
    boundary = combined_polygon.boundary
    gpd.GeoSeries(boundary).plot(ax=ax, color="black", linewidth=0.8)

    d1["title"] = d1.get("title", f"Spatial map of {d1['column']} for VPU {d1['vpu']}")
    plt.title(d1["title"])
    plt.xlabel(d1.get("xlab", "Longitude"))
    plt.ylabel(d1.get("ylab", "Latitude"))

    # define the output filename (and create the directory if it does not exist)
    outfile = _contruct_outfile_name(d1)

    # save the figure
    plt.savefig(outfile, bbox_inches="tight")
    plt.close()

    logger.info(f"Spatial map plot of {d1['var_str']} saved to {outfile}")


def plot_attribute_spatial_map(config: cs.Config, vpu: str, df_attrs_all: pd.DataFrame) -> None:
    """Plot spatial maps of selected attributes for the catchments in a VPU.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            The VPU (Virtual Processing Unit) identifier.
        df_attrs_all : pd.DataFrame
            DataFrame containing all attributes for the catchments.

    """
    # get list of attributes to plot from the config
    plot_flag = getattr(config.output.attr_data_final, "plots", {}) or {}
    attr_dict = plot_flag.get("attrs_to_plot", False)
    attrs = []
    for dataset, attrlist in attr_dict.items():
        attrs.extend(
            [f"{dataset}_{attr}" for attr in getattr(config.attr_datasets, dataset).attr_list if attr in attrlist]
        )
    if not attrs:
        return

    # read the hydrofabric file
    hydrofabric_file = Path(config.general.hydrofabric_file[vpu])
    gdf0 = gpd.read_file(hydrofabric_file, layer="divides")

    figure_dict = {
        "domain": config.general.domain,
        "vpu": vpu,
        "out_path": Path(config.output.attr_data_final.path).parent,
        "plot_subdir": "plots/attrs",
        "plot_type": "map",
        "algorithm": None,
    }

    for col in attrs:
        if col in df_attrs_all.columns:
            gdf = gpd.GeoDataFrame(df_attrs_all[[col]], geometry=gdf0.geometry)
            figure_dict["column"] = figure_dict["var_str"] = col
            _plot_spatial_map(gdf, figure_dict)
        else:
            logger.warning(f"Column '{col}' not found in df_attrs_all. Skipping spatial map plot for this attribute.")


def plot_missing_attr_counts(config: cs.Config, vpu: str, df_attrs_all: pd.DataFrame) -> None:
    """Plot the number of catchments with missing values for each selected attribute.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            The VPU (Virtual Processing Unit) identifier.
        df_attrs_all : pd.DataFrame
            DataFrame containing all attributes for the catchments.

    """
    # get plotting flag from the config
    plot_flag = getattr(config.output.attr_data_final, "plots", {}) or {}
    plot_flag = plot_flag.get("attr_missing_count", False)
    if not plot_flag:
        return

    cols = []
    for dataset in config.general.attr_dataset_list:
        cols = cols + [dataset + "_" + x for x in getattr(config.attr_datasets, dataset).attr_list]
    missing_cols = set(cols) - set(df_attrs_all.columns)
    cols1 = [col for col in cols if col not in missing_cols]
    if missing_cols:
        logger.warning(f"Missing columns in final attribute dataframe df_attrs_all: {missing_cols}.")
        logger.info("Please check the configuration.")
    plt.figure(figsize=(8, 4))
    df_attrs_all[cols1].isnull().sum().plot(kind="bar", color="skyblue", edgecolor="black")
    plt.title("Number of catchments with missing values for each selected attribute")

    outfile = Path(
        Path(config.output.attr_data_final.path).parent,
        f"plots/bar_attr_missing_count_{config.general.domain}_vpu{vpu}.png",
    )
    outfile.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outfile, bbox_inches="tight")
    logger.info(f"Missing attribute counts plot saved to {outfile}")

    plt.close()


def plot_donor_spatial_map(
    config: cs.Config, vpu: str, donor_basins: list, gdf_buffered: gpd.GeoDataFrame, combined_geom: gpd.GeoDataFrame
) -> None:
    """Plot the spatial distribution of donors within a VPU and its buffer zone.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            The VPU (Virtual Processing Unit) identifier.
        donor_basins : list
            List of donor basin identifiers.
        gdf_buffered : gpd.GeoDataFrame
            GeoDataFrame of the buffered VPU polygon.
        combined_geom : gpd.GeoDataFrame
            GeoDataFrame of the combined geometry of the VPU.

    """
    plot_flag = getattr(config.output.pairs, "plots", {}) or {}
    plot_flag = plot_flag.get("donor_spatial_map", False)
    if not plot_flag:
        return

    # read in lat/lon of all donors
    donors_all = utils.read_table(config.donor.donor_gage_file)

    # filter donors based on the donor_basins list (qualified donors)
    donors = donors_all[donors_all["gage_id"].isin(donor_basins)]
    donor_gdf = gpd.GeoDataFrame(
        donors, geometry=[Point(xy) for xy in zip(donors["longitude"], donors["latitude"])], crs="EPSG:4326"
    )

    # Project to meters for accurate distance calculations
    donor_gdf = donor_gdf.to_crs(epsg=3857)

    # visualize the donors selected
    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot base layer
    ring = gdf_buffered.difference(combined_geom)
    ring_gdf = gpd.GeoDataFrame(geometry=[ring], crs=donor_gdf.crs)
    ring_gdf.plot(
        ax=ax,
        color="lightgray",
        edgecolor="black",
    )

    # donors in the buffered VPU
    donor_gdf.plot(ax=ax, color="blue", markersize=10)

    # donors in the original VPU
    donors1 = donor_gdf[donor_gdf.geometry.within(combined_geom)]
    donors1.plot(ax=ax, color="red", markersize=10)

    # Create custom legend handles
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label=f"Donors within VPU ({len(donors1)})",
            markerfacecolor="red",
            markersize=8,
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label=f"Donors in buffer zone ({len(donor_gdf) - len(donors1)})",
            markerfacecolor="blue",
            markersize=8,
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color="black",
            label=f"Buffer zone ({round(config.donor.buffer_km)} km)",
            markerfacecolor="lightgray",
            markersize=10,
        ),
    ]

    # Add legend
    ax.legend(handles=legend_elements, loc="center left", bbox_to_anchor=(1, 0.5))

    # title
    plt.title(f"Donor basins available for VPU {vpu} regionalization")

    # tidy up plot
    ax.set_axis_off()
    plt.tight_layout()

    # save the figure
    outfile = Path(
        Path(config.output.pairs.path).parent,
        f"plots/map_donors_{config.general.domain}_vpu{vpu}.png",
    )
    outfile.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outfile, bbox_inches="tight")
    logger.info(f"Donor spatial map saved to {outfile}")

    plt.close(fig)


def _plot_distance_hist(df_pair: pd.DataFrame, d1: dict) -> None:
    """Generate histogram plot for the spatial or attribute distance between donors and receivers.

    Args:
        df_pair : pd.DataFrame
            DataFrame containg the donor-receiver pairing results.
        d1: dict
            Infomation needed for creating the plot

    """
    # check if the required column exists
    if d1["column"] not in df_pair:
        logger.warning(f"Column '{d1['column']}' not found in df_pairing. Skipping spatial distance histogram plot.")
        return

    plt.figure(figsize=(8, 4))
    sns.histplot(
        df_pair[d1["column"]],
        kde=True,
        bins=30,
        color="lightblue",
        edgecolor="grey",
        stat="density",
    )
    sns.kdeplot(df_pair[d1["column"]], color="darkblue", linewidth=1.5)
    plt.title(d1["title"])
    plt.xlabel(d1["xlab"])
    plt.ylabel(d1["ylab"])

    # define the output filename (and create the directory if it does not exist)
    outfile = _contruct_outfile_name(d1)
    plt.savefig(outfile, bbox_inches="tight")
    plt.close()

    logger.info(f"Histogram plot of ({d1['var_str']}) saved to {outfile}")


def _plot_pair_groups(config: cs.Config, plot_str: str, gdf: gpd.GeoDataFrame, d1: dict) -> None:
    """Plot donor-receiver pairing maps.

    This function generates plots for the donor-receiver pairings for the biggest categories in the dataset.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        plot_str : str
            A string indicating the type of plot to generate.
        gdf : gpd.GeoDataFrame
            GeoDataFrame containing the geometries and attributes for the catchments.
        d1: dict
            Information needed for creating the plot

    """
    # get the number of top categories to plot from plot_str, default to 10 if not specified
    match = re.search(r"\d+", plot_str)
    if match:
        top_n = int(match.group())
    else:
        top_n = 10
    logger.info(f"Plotting top {top_n} categories for donor-receiver pairings.")

    # check if the required column exists
    col_basin = config.donor.id_name
    col_divide = config.general.id_name
    if col_basin not in gdf.columns:
        # get col_basin from the crosswalk file
        crosswalk_file = Path(config.donor.donor_ngen_cwt_file)
        if not crosswalk_file.exists():
            logger.error(f"Crosswalk file {crosswalk_file} does not exist. Cannot determine {col_basin}.")
            return
        crosswalk_df = utils.read_table(crosswalk_file)
        if col_basin not in crosswalk_df.columns:
            logger.error(
                f"Column '{col_basin}' not found in crosswalk file {crosswalk_file}. Cannot determine {col_basin}."
            )
            return
        # gdf[col_basin] = gdf[col_divide].map(crosswalk_df.set_index(col_divide)[col_basin])
        mapping = (
            crosswalk_df[[col_divide, col_basin]].drop_duplicates(subset=col_divide).set_index(col_divide)[col_basin]
        )
        gdf[col_basin] = gdf[col_divide].map(mapping)

    top_basins = gdf[col_basin].value_counts().nlargest(top_n).index

    # Create a new column with 'Other' as fallback
    gdf["pair_group"] = gdf[col_basin].where(gdf[col_basin].isin(top_basins), "Other")

    # project the GeoDataFrame to lat/lon for plotting
    gdf = gdf.to_crs(epsg=4326)

    # Plot the pairing groups
    fig, ax = plt.subplots(figsize=(8, 6))
    # gdf.plot(ax=ax, column="pair_group", legend=True, categorical=True)
    gdf.plot(
        ax=ax,
        column="pair_group",
        legend=True,
        categorical=True,
        legend_kwds={
            "loc": "center left",
            "bbox_to_anchor": (1, 0.5),  # Place legend outside right
        },
    )

    # add outer boundary of the VPU
    combined_polygon = unary_union(gdf.geometry)
    boundary = combined_polygon.boundary
    gdf1 = gpd.GeoSeries(boundary, crs=gdf.crs).to_crs(epsg=4326)
    gdf1.plot(ax=ax, color="black", linewidth=0.8)

    plt.title(d1["title"])
    plt.xlabel(d1["xlab"])
    plt.ylabel(d1["ylab"])

    # define the output filename (and create the directory if it does not exist)
    outfile = _contruct_outfile_name(d1)

    # save the figure
    plt.savefig(outfile, bbox_inches="tight")
    logger.info(f"Map of donor-receiver pair groups saved to {outfile}")

    plt.close(fig)


def plot_pairing_outputs(config: cs.Config, vpu: str, algorithm: str, outfile: Path) -> None:
    """Generate plots for the donor-receiver pairing results.

    Args:
        config : cs.Config
            Configuration object containing settings for the regionalization.
        vpu : str
            The VPU (Virtual Processing Unit) identifier.
        algorithm : str
            The algorithm used for donor-receiver pairing.
        outfile : Path
            Path to the output file containing the pairing results.

    """
    # check if any pairing plots are requested
    plot_flag = getattr(config.output.pairs, "plots", {}) or {}
    if not any(plot_flag.values()):
        logger.info("No pairing plots requested. Skipping pairing outputs plotting.")
        return
    else:
        logger.info("Creating pairing plots as requested in the configuration.")

    # determine which plots to create based on plot_flag disctionary
    plots = [p1 for p1, v1 in plot_flag.items() if v1]

    # read the pairing data
    if any(plots):
        try:
            df_pairing = pd.read_parquet(outfile)
        except Exception as e:
            logger.error(f"Error reading pairing data from {outfile}: {e}")
            return
        if df_pairing.empty:
            logger.warning(f"No pairing data found in {outfile}. Skipping creation of pairing plots.")
            return

    if any("map" in v for v in plots):
        # read the hydrofabric file
        hydrofabric_file = Path(config.general.hydrofabric_file[vpu])
        gdf0 = gpd.read_file(hydrofabric_file, layer="divides")

        # Ensure df_pairing and gdf0 share a common divide_id column
        id_col = config.general.id_name
        assert id_col in df_pairing.columns
        assert id_col in gdf0.columns

        # Merge df_pairing with geometries from gdf0 based on divide_id
        gdf_pairing = df_pairing.merge(gdf0[[id_col, "geometry"]], on=id_col, how="right")

        # Convert to GeoDataFrame
        gdf_pairing = gpd.GeoDataFrame(gdf_pairing, geometry="geometry", crs=gdf0.crs)

        # identify rows with divide_id in gdf_pairing but not in df_pairing (those would be the donors)
        donor_ids = gdf_pairing[~gdf_pairing[id_col].isin(df_pairing[id_col])][id_col].unique()
        if donor_ids.size > 0:
            # assign zero spatial and attribute distances to these rows
            gdf_pairing.loc[gdf_pairing[id_col].isin(donor_ids), ["distSpatial", "distAttr"]] = 0

    # common configuration for figure plotting
    figure_dict0 = {
        "domain": config.general.domain,
        "vpu": vpu,
        "algorithm": algorithm,
        "xlab": "Longitude",
        "ylab": "Latitude",
        "out_path": Path(config.output.pairs.path).parent,
        "plot_subdir": "plots/pairing",
        "plot_type": "map",
    }

    if "pair_spatial_distance_histogram" in plots:
        # plot the spatial distance histogram
        figure_dict = {
            "column": "distSpatial",
            "title": "Spatial distance distribution of donor-receiver pairings",
            "xlab": "Spatial distance (km)",
            "ylab": "Frequency",
            "plot_type": "hist",
            "var_str": "spatial_dist",
        }
        _plot_distance_hist(df_pairing, {**figure_dict0, **figure_dict})

    if "pair_attribute_distance_histogram" in plots:
        # plot the attribute distance histogram
        figure_dict = {
            "column": "distAttr",
            "title": "Attribute distance distribution of donor-receiver pairings",
            "xlab": "Attribute distance",
            "ylab": "Frequency",
            "plot_type": "hist",
            "var_str": "attr_dist",
        }
        _plot_distance_hist(df_pairing, {**figure_dict0, **figure_dict})

    if "pair_spatial_distance_map" in plots:
        # plot the spatial distance map
        figure_dict = {
            "column": "distSpatial",
            "title": "Spatial distance (km) of donor-receiver pairings",
            "var_str": "spatial_dist",
        }
        _plot_spatial_map(gdf_pairing, {**figure_dict0, **figure_dict})

    if "pair_attribute_distance_map" in plots:
        # plot the attribute distance map
        figure_dict = {
            "column": "distAttr",
            "title": "Attribute distance of donor-receiver pairings",
            "var_str": "attr_dist",
        }
        _plot_spatial_map(gdf_pairing, {**figure_dict0, **figure_dict})

    plot_string = next((s for s in plots if "pair_group_map" in s), None)
    if plot_string:
        # plot the pairing groups map
        figure_dict = {
            "column": None,
            "title": f"Top Donor-receiver pair groups in vpu {vpu}",
            "var_str": plot_string.split("_")[0] + "_pair_group",
        }
        _plot_pair_groups(config, plot_string, gdf_pairing, {**figure_dict0, **figure_dict})
