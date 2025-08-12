"""Main script for formulation regionalization.

This script reads a configuration file and processes the formulation regionalization
using the specified configurations.
"""

import argparse
import logging
from contextlib import contextmanager
from time import time

from formreg import config_schema as cs
from formreg import select_formulation as sf
from formreg import summary_score as ss
from utils import load_and_process_config

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
        "formreg_config",
        type=str,
        help="Path to the specific config yaml file for formulation regionalization",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Combine the config files into a list
    config_paths = [args.general_config, args.formreg_config]

    # Load, validate, process, and save the configuration
    config = load_and_process_config(config_paths, config_schema=cs.Config)

    # process by VPU
    for vpu in config.general.vpu_list:
        logger.info(f"========= Processing formulation regionalization for VPU: {vpu} =========")

        # compute the summary score for the VPU
        with timing_block("compute_summary_score"):
            df_score = ss.compute_summary_score(config, vpu)

        # select the best formulation based on the summary score and optionally costs
        with timing_block("select_formulation"):
            df_selected = sf.select_formulation(config, vpu, df_score)
