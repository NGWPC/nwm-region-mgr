"""Unit tests for parameter regionalization (parreg).

Usage: pytest path/to/this/file/parreg_tests.py

Test data can be found here: s3://ngwpc-dev/Yuqiong.Liu/data/ngen_reg/
"""

import json
import os
import unittest

import pandas as pd
import pytest
from parreg.process_config import RegionalizationProcessor

SAMPLE_SIZE = 500
ALGORITHM_LIST = ["gower", "urf", "kmeans", "kmedoids", "hdbscan", "birch"]
ATTR_DATASET_LIST = ["ngen", "hlr"]

TEST_DIRECTORY = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(TEST_DIRECTORY, "test_config.yaml")

EXPECTED_OUTPUT_DIRECTORY = os.path.join(TEST_DIRECTORY, "test_data/expected_outputs")
EXPECTED_PAIRS_DIRECTORY = os.path.join(EXPECTED_OUTPUT_DIRECTORY, "pairs")

DONOR_RECEIVER_FILE = os.path.join(EXPECTED_OUTPUT_DIRECTORY, "donor_receivers.json")
ATTRS_PARQUET = os.path.join(EXPECTED_OUTPUT_DIRECTORY, "attrs.parquet")
DIST_SPATIAL_PARQUET = os.path.join(EXPECTED_OUTPUT_DIRECTORY, "dist_spatial.parquet")


@pytest.fixture(scope="class")
def setup_data(request):
    """Initialize RegionalizationProcessor."""
    request.cls.rp = RegionalizationProcessor(CONFIG_FILE, sample_size=SAMPLE_SIZE)
    with open(DONOR_RECEIVER_FILE) as f:
        donor_receivers = json.load(f)
    request.cls.donors = donor_receivers["donors"]
    request.cls.receivers = donor_receivers["receivers"]
    request.cls.attrs = pd.read_parquet(ATTRS_PARQUET)
    request.cls.dist_spatial = pd.read_parquet(DIST_SPATIAL_PARQUET)


@pytest.mark.usefixtures("setup_data")
class TestParameterRegionalization(unittest.TestCase):
    """Test class for regionalization."""

    def test_a_config(self):
        """Test config file."""
        self.rp.set_vpu(self.rp.config.general.vpu_list[0])
        self.rp.get_donors_receivers()
        self.assertEqual(self.rp.vpu, "01")
        self.assertEqual(self.rp.config.general.algorithm_list, ALGORITHM_LIST)
        self.assertEqual(self.rp.config.general.attr_dataset_list, ATTR_DATASET_LIST)

    def test_b_get_donor_receivers(self):
        """Test getting donor and receivers."""
        self.assertEqual(sorted(self.rp.receivers), sorted(self.receivers))
        self.assertEqual(sorted(self.rp.donors), sorted(self.donors))
        self.assertTrue(self.rp.dist_spatial.equals(self.dist_spatial))

    def test_c_process_attrs(self):
        """Test processing attributes."""
        self.assertTrue(self.df_attr_all.equals(self.attrs))

    @property
    def df_attr_all(self):
        """Dataframe of the attributes."""
        self.rp.process_attr_data()
        return self.rp.set_snow_flag(self.rp.sorted_df_attrs_all)

    def test_d_generate_pairings(self):
        """Test generate pairings."""
        self.rp.generate_pairing(self.df_attr_all, self.rp.dist_spatial)

        for algorithm in ALGORITHM_LIST:
            expected_pairing_path = os.path.join(
                EXPECTED_PAIRS_DIRECTORY, f"pairs_{algorithm}_conus_vpu01.parquet"
            )
            result_path = os.path.join(
                self.rp.config.output.pairs.path,
                f"pairs_{algorithm}_conus_vpu01.parquet",
            )

            expected_df = pd.read_parquet(expected_pairing_path)
            result_df = pd.read_parquet(result_path)
            self.assertEqual(
                (
                    result_df.sort_values(by="divide_id")["donors"].values
                    == expected_df.sort_values(by="divide_id")["donors"]
                ).sum(),
                SAMPLE_SIZE,
            )
