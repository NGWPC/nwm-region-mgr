"""Base model of Pairer for donor-receiver pairing."""

import pandas as pd
from pydantic import BaseModel, ConfigDict


class Pairer(BaseModel):
    """Base Pairer."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: dict
    """Configuration for the Pairer."""

    df_attr_all: pd.DataFrame
    """DataFrame containing attributes for all donors and receivers."""

    dist_spatial: pd.DataFrame
    """DataFrame containing spatial distances between donors and receivers."""
