"""Functions for generating specific/interim plots from parameter regionalization.

plot_outputs.py

Functions:
- plot_missing_attr_counts: Plots the number of catchments with missing values for each selected attribute.
- plot_donor_spatial_map: Plots the spatial distribution of donors within a VPU and its buffer zone.

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
    # plot_flag = getattr(config.output["attr_data_final"], "plots", {}) or {}
    # plot_flag = plot_flag.get("attr_missing_count", False)
    # if not plot_flag:
    #     return

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
        config.output["attr_data_final"].path,
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
    # plot_flag = getattr(config.output["pairs"], "plots", {}) or {}
    # plot_flag = plot_flag.get("donor_spatial_map", False)
    # if not plot_flag:
    #    return

    # read in lat/lon of all donors
    donors_all = utils.read_table(config.general.donor_gage_file)

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
        config.output["pairs"].path,
        f"plots/map_donors_{config.general.domain}_vpu{vpu}.png",
    )
    outfile.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outfile, bbox_inches="tight")
    logger.info(f"Donor spatial map saved to {outfile}")

    plt.close(fig)
