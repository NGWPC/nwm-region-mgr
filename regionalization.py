"""Main function to run regionalization."""

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
    """Context Manager for timing processes."""
    start = time()
    yield
    end = time()
    logger.info(f"  Execution time for {step_str}: {end - start} seconds")


if __name__ == "__main__":
    # read and validate config
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
