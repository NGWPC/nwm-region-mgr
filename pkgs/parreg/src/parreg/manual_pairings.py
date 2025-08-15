from functools import lru_cache

import pandas as pd


class ManualPairer:
    """Class to handle manual pairings of donor-receiver pairings based on user input."""

    def __init__(self, config: dict):
        """Initialize the ManualPairer."""
        self.config = config

    @property
    def manual_pairings_file(self):
        """Path to the manual pairings file."""
        return self.config.get("general", {}).get("manual_pairings_file")

    @property
    def divide_col(self):
        """Get the divide column name from the configuration."""
        return self.config.general.id_col.get("divide", "divide_id")

    @property
    def donor_col(self):
        """Get the donor column name from the configuration."""
        return self.config.general.id_col.get("donor", "donor_id")

    @property
    @lru_cache
    def manual_pairings_df(self) -> pd.DataFrame:
        """Load and return the manual pairings DataFrame."""
        if not self.manual_pairings_file:
            raise ValueError(
                "Manual pairings file path is not provided in the configuration."
            )

        df = pd.read_csv(self.manual_pairings_file)
        required_columns = {self.divide_col, self.donor_col}
        if not required_columns.issubset(df.columns):
            raise ValueError(
                f"Manual pairings file must contain the columns: {required_columns}"
            )

        return df

    @property
    def regionalization_output_file(self) -> str:
        """Get the output file path for manual pairings."""
        return self.config.get_file_path()

    @property
    @lru_cache
    def regionalization_df(self) -> pd.DataFrame:
        """Get the regionalization DataFrame based on manual pairings."""
        return pd.read_parquet(self.regionalization_output_file)

    @property
    @lru_cache
    def manually_updated_pairings(self) -> pd.DataFrame:
        """Update the regionalization DataFrame with manual pairings."""
        manually_updated_pairings = self.regionalization_df.copy()
        manually_updated_pairings = manually_updated_pairings.merge(
            self.manual_pairings_df[[self.divide_col, self.donor_col]],
            on=self.divide_col,
            how="left",
            suffixes=("", "_manual"),
        )
        manually_updated_pairings[self.donor_col] = manually_updated_pairings[
            f"{self.donor_col}_manual"
        ].combine_first(manually_updated_pairings[self.donor_col])

        return manually_updated_pairings.drop(columns=[f"{self.donor_col}_manual"])
