"""Functions for generating plots from the output data of regionalization."""

import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from shapely.geometry import Point

from parreg.logging_config import setup_logging

from . import config_schema as cs
from . import utils

setup_logging()
logger = logging.getLogger(__name__)


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

    # project the GeoDataFrame to lat/lon for plotting
    gdf0 = gdf0.to_crs(epsg=4326)

    for col in attrs:
        # check if the column exists in the DataFrame
        if col in df_attrs_all.columns:
            plt.figure(figsize=(8, 6))
            gdf = gpd.GeoDataFrame(df_attrs_all[[col]], geometry=gdf0.geometry)
            gdf.plot(column=col, cmap="viridis", legend=True, edgecolor=None)
            plt.title(f"Spatial distribution of attribute {col}")

            outfile = Path(
                Path(config.output.attr_data_final.path).parent,
                f"plots/map_attr_{col}_{config.general.domain}_vpu{vpu}.png",
            )
            outfile.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(outfile, bbox_inches="tight")
            logger.info(f"Attribute spatial map saved to {outfile}")
            plt.close()


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
    plt.title(f"Donors available for VPU {vpu} regionalization")

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


def plot_pairing_outputs(config: cs.Config, vpu: str, algorithm: str, outfile: Path) -> None:
    """Generate plots for the donor-receiver pairings.

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
    # get plotting flags from the config
    plot_flag = getattr(config.output.pairs, "plots", {}) or {}
    plot_flag1 = plot_flag.get("pair_spatial_distance_histogram", False)
    plot_flag2 = plot_flag.get("pair_attribute_distance_histogram", False)

    # read the pairing data
    if plot_flag1 or plot_flag2:
        try:
            df_pairing = pd.read_parquet(outfile)
        except Exception as e:
            logger.error(f"Error reading pairing data from {outfile}: {e}")
            return
        if df_pairing.empty:
            logger.warning(f"No pairing data found in {outfile}. Skipping creation of pairing plots.")
            return

    # plot the spatial distance distribution of donor-receiver pairings
    if plot_flag1:
        # check if the required column exists
        if "distSpatial" not in df_pairing.columns:
            logger.warning("Column 'distSpatial' not found in df_pairing. Skipping spatial distance histogram plot.")
            return
        plt.figure(figsize=(8, 4))
        sns.histplot(
            df_pairing["distSpatial"],
            kde=True,
            bins=30,
            color="lightblue",
            edgecolor="grey",
            stat="density",
        )
        sns.kdeplot(df_pairing["distSpatial"], color="darkblue", linewidth=1.5)
        plt.title("Spatial distance distribution of donor-receiver pairings")
        plt.xlabel("Spatial distance (km)")
        plt.ylabel("Frequency")

        outfile = Path(
            Path(config.output.pairs.path).parent,
            f"plots/hist_spatial_dist_{algorithm}_{config.general.domain}_vpu{vpu}.png",
        )
        outfile.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(outfile, bbox_inches="tight")
        plt.close()

        logger.info(f"Spatial distance histogram saved to {outfile}")

    # plot the attribute distance distribution of donor-receiver pairings
    if plot_flag2:
        if "distAttr" not in df_pairing.columns:
            logger.warning("Column 'distAttr' not found in df_pairing. Skipping attribute distance histogram plot.")
            return

        plt.figure(figsize=(8, 4))
        sns.histplot(
            df_pairing["distAttr"],
            kde=True,
            bins=30,
            color="lightblue",
            edgecolor="grey",
            stat="density",
        )
        sns.kdeplot(df_pairing["distAttr"], color="darkblue", linewidth=1.5)
        plt.title("Attribute distance distribution of donor-receiver pairings")
        plt.xlabel("Attribute distance")
        plt.ylabel("Frequency")

        outfile = Path(
            Path(config.output.pairs.path).parent,
            f"plots/hist_attr_dist_{algorithm}_{config.general.domain}_vpu{vpu}.png",
        )
        outfile.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(outfile, bbox_inches="tight")
        plt.close()

        logger.info(f"Attribute distance histogram saved to {outfile}")
