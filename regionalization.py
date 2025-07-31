"""Main script for parameter regionalization.

This script reads a configuration file and processes the parameter regionalization
using the specified algorithms and configurations.
"""

import argparse
import logging
from contextlib import contextmanager
from pathlib import Path
from time import time

from formreg import config_schema as fcs
from formreg import select_formulation as sf
from formreg import summary_score as ss
from parreg import config_schema as pcs
from parreg import process_config as pc

# setup_logging()
from parreg.logging_config import setup_logging
from parreg.process_config import RegionalizationProcessor

# from parreg.logging_config import setup_logging
from utils import load_and_process_config

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
        "general_config",
        type=str,
        help="Path to the general config yaml file for regionalization",
    )

    parser.add_argument(
        "--formreg_config",
        type=str,
        help="Path to the specific config yaml file for formulation regionalization",
    )

    parser.add_argument(
        "--parreg_config",
        type=str,
        help="Path to the specific config yaml file for parameter regionalization",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Load and process the formulation regionalization config if specified
    if args.formreg_config is not None:
        form_config = load_and_process_config([args.general_config, args.formreg_config], config_schema=fcs.Config)
    else:
        form_config = None

    # Load and process the parameter regionalization config if specified
    if args.parreg_config is not None:
        par_config = load_and_process_config([args.general_config, args.parreg_config], config_schema=pcs.Config)
    else:
        par_config = None

    if form_config is None and par_config is None:
        logger.error("No formulation or parameter configuration files provided. Exiting.")
        exit(1)

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
        df_attr_all = rp.set_snow_flag(rp.sorted_df_attrs_all)

        # loop through regionalization algorithms to generate donor-receiver pairings
        with timing_block("generate_pairing"):
            rp.generate_pairing(df_attr_all, rp.dist_spatial)
