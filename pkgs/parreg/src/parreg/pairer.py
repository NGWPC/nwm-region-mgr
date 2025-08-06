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

    # formulation_dict: dict | None = None
    # """Formulation dictionary for donors and receivers."""

    # def get_formulation_dict(self, id_list: list[str] | None = None) -> dict:
    #     """Return the formulation dictionary."""
    #     if id_list is None:
    #         return self.formulation_dict
    #     return {k: self.formulation_dict[k] for k in id_list if k in self.formulation_dict}
