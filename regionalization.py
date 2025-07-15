"""Main script for parameter regionalization.

This script reads a configuration file and processes the parameter regionalization
using the specified algorithms and configurations.
"""

import argparse
import logging
from contextlib import contextmanager
from pathlib import Path
from time import time

from pkgs.parreg.src.parreg.logging_config import setup_logging
from pkgs.parreg.src.parreg.process_config import RegionalizationProcessor

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
    if not config_file.exists():
        raise FileNotFoundError(config_file)

    # initialize RegionalizationProcessor
    rp = RegionalizationProcessor(config_file)

    # process by VPU
    for vpu in rp.config.general.vpu_list:
        # set vpu
        rp.set_vpu(vpu)

        # get receivers and qualified donors in the VPU, and compute pairwise spatial distances between them
        with timing_block("get_donors_receivers"):
            rp.get_donors_receivers()

        # assemble the attribute data for donors and receivers
        with timing_block("process_attr_data"):
            rp.process_attr_data()

        # determine whether the catchments are snowy (as snowy and non-snowy catchments are processed separately)
        df_attr_all = rp.set_snow_flag(rp.df_attrs_all)

        # loop through regionalization algorithms to generate donor-receiver pairings
        with timing_block("generate_pairing"):
            rp.generate_pairing(df_attr_all, rp.dist_spatial)
