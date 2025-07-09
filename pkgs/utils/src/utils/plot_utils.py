"""Utility functions for plotting spatial maps and histograms etc.

plot_utils.py

Functions:
- plot_spatial_map: Generate a spatial map plot for the given data.
- plot_histogram: Generate histogram plot for the spatial or attribute distance between donors and receivers.

"""

import logging
import math

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


def _plot_columns_by_dtype(
    gdf: gpd.GeoDataFrame,
    columns: list[str],
    fillna_value=None,
    num_bins: int = None,
    cmap_numeric: str = "viridis",
    cmap_categorical: str = "Set3",
    figsize=(10, 6),
    ncols: int = 3,
):
    """Plot multiple GeoDataFrame columns in subplots based on data type.

    Args:
        gdf: GeoDataFrame to plot
        columns: list of column names to plot
        fillna_value: value to fill NaNs
        num_bins: number of bins for numeric columns (optional)
        cmap_numeric: colormap for numeric values
        cmap_categorical: colormap for categorical values
        figsize: figure size
        ncols: number of columns in the subplot grid (default is 3)

    """
    n = len(columns)
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize)
    axes = np.array(axes).reshape(-1)  # Flatten in case of 2D grid

    # get the outer boundary of the GeoDataFrame
    combined_polygon = unary_union(gdf.geometry)
    boundary = combined_polygon.boundary

    for i, column in enumerate(columns):
        ax = axes[i]
        dtype = gdf[column].dtype

        # Copy gdf to avoid modifying original
        gdf_plot = gdf.copy()
        if fillna_value is not None:
            gdf_plot[column] = gdf_plot[column].fillna(fillna_value)

        if pd.api.types.is_numeric_dtype(dtype):
            if num_bins is not None:
                gdf_plot["__binned__"] = pd.cut(gdf_plot[column], bins=num_bins)
                gdf_plot.plot(ax=ax, column="__binned__", cmap=cmap_numeric, legend=True, edgecolor=None)
            else:
                gdf_plot.plot(ax=ax, column=column, cmap=cmap_numeric, legend=True, edgecolor=None)

        elif pd.api.types.is_categorical_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
            gdf_plot[column] = gdf_plot[column].astype("category")
            gdf_plot.plot(ax=ax, column=column, cmap=cmap_categorical, legend=True, edgecolor=None)
        else:
            ax.set_title(f"Unsupported dtype: {column}")
            ax.axis("off")
            continue

        # add outer boundary
        gpd.GeoSeries(boundary).plot(ax=ax, color="black", linewidth=0.8)

        ax.set_title(column)
        ax.set_axis_off()

    # Turn off any unused subplots
    for j in range(i + 1, len(axes)):
        axes[j].axis("off")

    return fig, axes[: i + 1]  # Return only used axes


def _plot_column_by_dtype(
    gdf: gpd.GeoDataFrame,
    column: str,
    ax=None,
    fillna_value=None,
    num_bins: int = None,
    cmap_numeric: str = "viridis",
    cmap_categorical: str = "Set3",
):
    """Plot a GeoDataFrame based on the data type of a column.

    Args:
        gdf: GeoDataFrame to plot
        column: column name to use for coloring
        ax: optional matplotlib axis
        fillna_value: value to fill NaNs before plotting
        num_bins: if specified, bin numeric data into this number of bins
        cmap_numeric: colormap for numeric data
        cmap_categorical: colormap for categorical/string data

    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))

    # Handle missing values
    if fillna_value is not None:
        gdf = gdf.copy()
        gdf[column] = gdf[column].fillna(fillna_value)

    dtype = gdf[column].dtype

    if pd.api.types.is_numeric_dtype(dtype):
        if num_bins is not None:
            # Discretize into bins
            gdf["__binned__"] = pd.cut(gdf[column], bins=num_bins)
            gdf.plot(ax=ax, column="__binned__", cmap=cmap_numeric, legend=True, edgecolor="black")
        else:
            gdf.plot(ax=ax, column=column, cmap=cmap_numeric, legend=True, edgecolor="black")

    elif pd.api.types.is_categorical_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
        gdf = gdf.copy()
        gdf[column] = gdf[column].astype("category")
        gdf.plot(ax=ax, column=column, cmap=cmap_categorical, legend=True, edgecolor="black")

    else:
        raise ValueError(f"Unsupported column data type for plotting: {dtype}")

    ax.set_title(f"Plot by '{column}'")
    ax.set_axis_off()
    return ax


def plot_spatial_map(gdf: gpd.GeoDataFrame, d1: dict) -> None:
    """Generate a spatial map plot for the given data.

    Args:
        gdf : gpd.GeoDataFrame
            GeoDataFrame containing the data to be plotted.
        d1: dict
            Information needed for creating the plot

    """
    # check if the required column existss
    for col in d1["columns"]:
        if col not in gdf:
            logger.warning(f"Column '{col}' not found in gdf. Skipping spatial map plot.")
            return

    _, ax = plt.subplots(figsize=(8, 6))

    # project the GeoDataFrame to lat/lon for plotting
    # gdf = gdf.to_crs(epsg=4326)

    # create spatial map
    fig, axes = _plot_columns_by_dtype(
        gdf,
        columns=d1["columns"],
        fillna_value=d1.get("fillna_value", None),
        num_bins=d1.get("num_bins", None),
        cmap_numeric=d1.get("cmap_numeric", "viridis"),
        cmap_categorical=d1.get("cmap_categorical", "Set3"),
        ncols=d1.get("ncols", 3),
    )
    # gdf.plot(ax=ax, column=d1["column"], cmap="viridis", legend=True, edgecolor=None)

    d1["title"] = d1.get("title", f"Spatial Map of {d1['var_str']}: VPU {d1['vpu']}")
    fig.suptitle(d1["title"], fontsize=16, fontweight="bold")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # Adjust layout to make room for the title

    # save the figure
    if d1.get("outfile") is not None:
        plt.savefig(d1["outfile"], bbox_inches="tight")
        plt.close()
        logger.info(f"Spatial map plot of {d1['var_str']} saved to {d1['outfile']}")
    else:
        logger.warning("No output file specified for spatial map plot. Skipping save.")


def plot_histogram(data: pd.DataFrame, d1: dict) -> None:
    """Generate histogram plots for multiple columns in dataframe.

    Args:
        data : pd.DataFrame
            DataFrame containing the donor-receiver pairing results.
        d1: dict
            Should include a key 'columns' which is a list of column names to plot.

    """
    columns = d1.get("columns", [])
    if not columns:
        raise ValueError("No columns specified in d1['columns'].")

    # Filter to columns that exist in data
    valid_columns = [col for col in columns if col in data.columns]
    if not valid_columns:
        raise ValueError("None of the specified columns exist in the dataframe.")
    missing_columns = set(columns) - set(valid_columns)
    if missing_columns:
        logger.warning(f"Columns {missing_columns} not found in data. Only plotting valid columns: {valid_columns}")

    n = len(valid_columns)
    ncols = d1.get("ncols", 3)
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(6 * ncols, 4 * nrows))
    axes = axes.flatten()  # Flatten in case of single row

    for i, col in enumerate(valid_columns):
        sns.histplot(
            data[col],
            ax=axes[i],
            kde=True,
            bins=30,
            color="lightblue",
            edgecolor="grey",
            stat="density",
        )
        sns.kdeplot(data[col], ax=axes[i], color="darkblue", linewidth=1.5)
        axes[i].set_title(f"{col}")

    # Hide any unused subplots
    for j in range(len(valid_columns), len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(f"Histograms of {d1['var_str']}: VPU {d1['vpu']}", fontsize=16, fontweight="bold")
    plt.xlabel(d1.get("xlabel", "Value"))
    plt.ylabel(d1.get("ylabel", "Density"))
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # leave space for main title

    # save the figure
    if d1.get("outfile") is not None:
        plt.savefig(d1["outfile"], bbox_inches="tight")
        plt.close()
        logger.info(f"Histogram of {d1['var_str']} saved to {d1['outfile']}")
    else:
        logger.warning("No output file specified for histogram plot. Skipping save.")
