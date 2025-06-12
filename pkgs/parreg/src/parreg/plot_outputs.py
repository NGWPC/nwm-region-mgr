"""This module contains functions for generating plots from the output data of regionalization."""

import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

from parreg.logging_config import setup_logging

from . import config_schema as cs

setup_logging()
logger = logging.getLogger(__name__)


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
    config1 = config.output.pairs.plots
    if not config1:
        return
    plot_flag1 = config1.get("pair_spatial_distance_histogram", False)
    plot_flag2 = config1.get("pair_attribute_distance_histogram", False)

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
        df_pairing["distSpatial"].plot(kind="hist", bins=50, color="skyblue")
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
        df_pairing["distAttr"].plot(kind="hist", bins=50, color="skyblue")
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
