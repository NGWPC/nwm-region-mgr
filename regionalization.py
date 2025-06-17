"""Main script for parameter regionalization.

This script reads a configuration file and processes the parameter regionalization
using the specified algorithms and configurations.
"""

import argparse
import logging
from contextlib import contextmanager
from pathlib import Path
from time import time

import parreg.process_config as pc
from parreg.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


# function to timing the execution of various steps
@contextmanager
def timing_block(step_str: str):
    """Context manager for timing code execution."""
    start = time()
    yield
    end = time()
    logger.info(f"  Execution time for {step_str}: {end - start} seconds")


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument(
        "config_file",
        type=str,
        help="Path to the config yaml file for parameter regionalization",
    )

    # Parse the arguments
    args = parser.parse_args()
    logger.info(f"  Config file to use: {args.config_file}")

    # read and validate config
    config_file = Path(args.config_file)
    config_file = Path("configs/config.yaml")
    if not config_file.exists():
        raise FileNotFoundError(config_file)

    config = pc.load_and_validate_config(config_file)

    # process by VPU
    for vpu in config.general.vpu_list:
        # get receivers and qualified donors in the VPU, and compute pairwise spatial distances between them
        with timing_block("get_donors_receivers"):
            donors, receivers, df_dist_spatial = pc.get_donors_receivers(config, vpu)

        # assemble the attribute data for donors and receivers
        with timing_block("process_attr_data"):
            donors, receivers, df_attrs_all = pc.process_attr_data(
                config, vpu, donors, receivers, df_dist_spatial
            )

        # detemine whether the catchments are snowy (as snowy and non-snowy catchments are processed separately)
        df_attrs_all = pc.set_snow_flag(
            df_attrs_all, config.algorithms.general.min_snow_frac
        )

        # loop through regionalization algorithms to generate donor-receiver pairings
        with timing_block("generate_pairing"):
            pc.generate_pairing(config, vpu, df_attrs_all, df_dist_spatial)
