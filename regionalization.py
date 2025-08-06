"""Main script for parameter regionalization.

This script reads a configuration file and processes the parameter regionalization
using the specified algorithms and configurations.
"""

import argparse
import logging
from argparse import RawTextHelpFormatter
from pathlib import Path

from formreg import config_schema as fcs
from formreg.process_config import FormulationRegionalizationProcessor
from parreg import config_schema as pcs
from parreg.process_config import RegionalizationProcessor

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)

    config_files = ["config_general.yaml", "config_formreg.yaml", "config_parreg.yaml"]

    # Add arguments
    help_text = """Path to the folder containing the following three YAML config files:
    config_general.yaml: contains general settings for the regionalization process.
    config_formreg.yaml: contains specific settings for the formulation regionalization process.
    config_parreg.yaml: contains specific settings for the parameter regionalization process.
    """
    parser.add_argument(
        "config_dir",
        type=str,
        help=help_text,
        # help="Path to the folder containing the following three yaml config files: \n"
        # + ", ".join(config_files)
        # + "\n\n"
        # + "config_general.yaml: contains general settings for the regionalization process.\n\n"
        # + "config_formreg.yaml: contains specific settings for the formulation regionalization process.\n\n"
        # + "config_parreg.yaml: contains specific settings for the parameter regionalization process.",
    )

    # Parse the arguments
    args = parser.parse_args()
    config_dir = Path(args.config_dir)

    # Build full paths to each config file
    config_paths = {file: config_dir / file for file in config_files}

    # Access individual files if needed
    file_general_config = config_paths["config_general.yaml"]
    file_formreg_config = config_paths["config_formreg.yaml"]
    file_parreg_config = config_paths["config_parreg.yaml"]

    # Check that all config files exist
    missing = [str(p) for p in config_paths.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required config files: {', '.join(missing)}")

    # Load and process the formulation regionalization config
    frp = FormulationRegionalizationProcessor(
        config_file=[file_general_config, file_formreg_config], config_schema=fcs.Config
    )

    # Load and process the parameter regionalization config
    rp = RegionalizationProcessor(
        config_file=[file_general_config, file_parreg_config], config_schema=pcs.Config, sample_size=None
    )

    # process by VPU
    for vpu in rp.config.general.vpu_list:
        rp.run_parreg_for_vpu(vpu, frp)
