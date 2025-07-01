"""Function to create donor-receiver paring using distance methods.

This function performs donor-receiver pairing using either Gower's distance (method = "gower") or
  the distance computed by unsupervised random forest classification (method = "urf")

"""

import logging
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from pydantic import BaseModel

from . import utils_algo
from .unsupervised_random_forest import URF

logger = logging.getLogger(__name__)


class DistancePairer(BaseModel):
    """Distance Pairer."""

    config: dict
    df_attr_all: pd.DataFrame
    dist_spatial: pd.DataFrame

    @property
    def attrs(self):
        """Attributes"""
        return {
            "main": self.config["attrs"]["main"],
            "base": self.config["attrs"]["base"],
        }

    @property
    def receivers(self):
        """Receivers."""
        # check if donors are identified for all receivers
        recs0 = self.df_attr_all[~self.df_attr_all["is_donor"]]["divide_id"].values
        if self.df_donor_all.shape[1] > 0:
            recs0 = [
                value
                for value in recs0
                if value not in self.df_donor_all["divide_id"].values
            ]
        return recs0

    def identify_donor_slow(
        self, rec1, config, method, df_attr, df_attr_all, dist_spatial, dist_attr0, run1
    ):
        """Identify donors (to be used in parallel computing)."""
        df_donor = pd.DataFrame()
        donors_all1 = df_attr[df_attr["is_donor"]]["divide_id"].tolist()

        # all donors in the same snow category as the receiver
        snow1 = df_attr["snowy"][
            (df_attr["divide_id"] == rec1) & (~df_attr["is_donor"])
        ].squeeze()
        donors0 = df_attr[(df_attr["is_donor"]) & (df_attr["snowy"] == snow1)][
            "divide_id"
        ].to_list()

        # find donors within the defined buffer iteratively so that closest donors
        # with attr distance below the predefined value can be found
        buffer = config["min_spa_dist"] - 100  # unit: km
        while buffer < config["max_spa_dist"] - 100:
            buffer = buffer + 100

            # if there exists donor catchment within a short distance,
            s1 = dist_spatial.loc[rec1]
            # s1 = dist_spatial[dist_spatial['receiver_id']==rec1].set_index('donor_id')['centroid_distance']
            donors1 = s1.loc[s1 <= config["zero_spa_dist"]].index.tolist()

            # select that catchment as donor;
            if len(donors1) > 0:
                # select that catchment as donor;
                donors1 = [s1[donors1].idxmin()]
            else:
                # otherwise, narrow down to donors within the buffer
                donors1 = s1.loc[s1 <= buffer].index.tolist()

            # potential donors in the same snowy category
            donors1 = list(set(donors1).intersection(set(donors0)))

            # potential donors with dist <= maxAttrDist
            dist1 = dist_attr0.loc[rec1, donors1]
            ix1 = [x for x in dist1.index if dist1[x] <= config["max_attr_dist"]]
            if (
                len(ix1) == 0
            ):  # if not, continue to the next round with a larger neighborhood
                continue

            # if a suitable donor is found (or all donors have been assessed), break the loop and stop searching
            if dist1[ix1].min() <= config["min_attr_dist"] or len(donors1) == len(
                donors_all1
            ):
                break

        # if donors are identified
        if len(donors1) > 0:
            # narrow down to those that satisfy the maxAttrDist threshold
            dist1 = dist1.loc[ix1]
            donor1 = dist1.index.tolist()

            # assign donor
            df_donor = pd.concat(
                (
                    df_donor,
                    utils_algo.assign_donors(
                        run1, donor1, [rec1], config, dist1, dist_spatial, df_attr_all
                    ),
                ),
                axis=0,
            )

        # if no donors found (after both 'main' and 'base' attribute rounds),
        # get the spatially closest donor with some constraints
        if len(donors1) == 0 and run1 == "base":
            # get all donors and their spatial distance to the receiver
            donor0 = df_attr_all[df_attr_all["is_donor"]]["divide_id"].tolist()
            dist0 = dist_spatial.loc[rec1,]

            # assign donor
            df_donor = pd.concat(
                (
                    df_donor,
                    utils_algo.assign_donors(
                        "proximity",
                        donor0,
                        [rec1],
                        config,
                        dist0,
                        dist_spatial,
                        df_attr_all,
                    ),
                ),
                axis=0,
            )

        return df_donor

    def update_columns_index(
        self, donors_for_round: list, receivers_for_round: list, dist_attr: pd.DataFrame
    ) -> pd.DataFrame:
        """Update the columns and index for distance attributes."""
        dist_attr.columns = donors_for_round
        dist_attr.index = receivers_for_round
        return dist_attr.round(3)

    def pair(self):
        """Perform donor-receiver pairing using Gower's distance."""
        logger.info(
            "calling function funcs_dist using the Gower's distance approach ..."
        )

        processed_receivers_df = pd.DataFrame()

        # two rounds of processing, first with attributes defined by the selected scenario (e.g., 'hlr'),
        # and then with 'base' attrs for catchments with no donors found in the 1st round
        for run in self.attrs:  # attr round
            if len(self.receivers) == 0:
                continue

            # reduce the attribute table to attributes for the current round
            df_attr0 = self.df_attr_all[self.config["non_attr_cols"] + self.attrs[run]]

            # iteratively process all the receivers to handle data gaps so that
            # receivers with the same missing attributes are processed in the same round
            processed_receivers = []  # receivers that have already been processed in previous krounds
            kround = 0
            while len([x for x in self.receivers if x in processed_receivers]) != len(
                self.receivers
            ):
                kround = kround + 1
                logger.info(
                    f"------------------------{run} attributes,  Round {kround}--------------------"
                )

                # figure out valid attributes to use this round
                df_attr = utils_algo.get_valid_attrs(
                    self.receivers,
                    processed_receivers,
                    df_attr0,
                    self.attrs[run],
                    self.config,
                )
                # donors and receivers for this round
                donors_for_round = df_attr[df_attr["is_donor"]]["divide_id"].tolist()
                receivers_for_round = df_attr[~df_attr["is_donor"]][
                    "divide_id"
                ].tolist()

                dist_attr = self.process(df_attr, donors_for_round, receivers_for_round)
                dist_attr = self.update_columns_index(
                    donors_for_round, receivers_for_round
                )

                # determine which receivers to be processed for the current round
                # process only those not-yet processed receivers
                receivers_to_process = [
                    r1
                    for r1 in self.receivers
                    if r1 in receivers_for_round and r1 not in processed_receivers
                ]
                processed_receivers += receivers_to_process
                logger.info(
                    f"{len(receivers_to_process)} receivers to be processed this round"
                )

                processed_receivers_run = Parallel(n_jobs=self.config["njobs"])(
                    delayed(self.identify_donor_slow)(
                        rec,
                        self.config,
                        self.method,
                        df_attr,
                        self.df_attr_all,
                        self.dist_spatial,
                        dist_attr,
                        run,
                    )
                    for rec in receivers_to_process
                )

                processed_receivers_run_df = pd.concat(processed_receivers_run, axis=0)
                processed_receivers_df = pd.concat(
                    (processed_receivers_df, processed_receivers_run_df), axis=0
                )

        return processed_receivers_df


class GowerPairer(DistancePairer):
    """Pairer using Gower distance."""

    def __init__(self):
        """Initialize Gower pairer."""
        super().__init__()
        self.method = "gower"

    def process(self, df_attr, donors_all1, receivers_all1):
        """Process data."""
        df_attr_reduced, weights = utils_algo.apply_pca(
            df_attr.drop(self.config["non_attr_cols"], axis=1)
        )

        # df_attr_reduced.to_csv("myscores_1.csv", index=False, float_format="%.3f")

        time1 = time.time()
        # compute Gower's distance between donors and receivers only, i.e., avoid calculating distance
        # between donors and donors, receivers and receivers (faster)
        nd1 = len(donors_all1)
        nr1 = len(receivers_all1)
        rng1 = df_attr_reduced.max() - df_attr_reduced.min()
        rng2 = np.repeat(np.matrix(rng1), nr1, axis=0)
        wgt2 = np.repeat(np.matrix(weights), nr1, axis=0)
        dist_attr0 = pd.DataFrame()
        scores_receiver = df_attr_reduced.iloc[nd1:]
        dist_attr0 = Parallel(n_jobs=self.config["njobs"])(
            delayed(self.compute_gower_distance_slow)(
                r1, df_attr_reduced, scores_receiver, rng2, wgt2, nr1
            )
            for r1 in range(nd1)
        )
        dist_attr0 = pd.concat(dist_attr0, axis=1)

        logger.info(
            f"Time consumed for distance calculation using Gower's distance is : --- {time.time() - time1} seconds ---"
        )
        return dist_attr0

    def compute_gower_distance_slow(
        self, r1, df_attr_reduced, scores_receiver, rng2, wgt2, nr1
    ):
        """Calculate Gower's distance between donors and receivers (to be used in parallel computing)."""
        scores_donor = np.repeat(np.matrix(df_attr_reduced.iloc[r1]), nr1, axis=0)
        df1 = ((scores_donor - scores_receiver).abs() / rng2 * wgt2).sum(axis=1)
        return df1


class URFPairer(DistancePairer):
    """Pairer using Gower distance."""

    def __init__(self):
        """Initialize Gower pairer."""
        super().__init__()
        self.method = "urf"

    def process(self, df_attr, donors_all1):
        """Process data."""
        # apply principal component analysis
        if not self.config["pca"]:
            df_attr_reduced = df_attr.drop(self.config["non_attr_cols"], axis=1)
        else:
            df_attr_reduced, _ = utils_algo.apply_pca(
                df_attr.drop(self.config["non_attr_cols"], axis=1)
            )

        # df_attr_reduced.to_csv("myscores_1.csv", index=False, float_format="%.3f")

        time1 = time.time()

        # compute attribute distance using unsupervised random forecast classification
        rf1 = URF(n_trees=self.config["n_trees"], max_depth=self.config["max_depth"])
        dist_attr0 = pd.DataFrame(
            rf1.get_distance(df_attr_reduced.to_numpy(), njob=self.config["njobs"])
        )
        dist_attr0 = dist_attr0.iloc[len(donors_all1) :, : len(donors_all1)]

        logger.info(
            f"Time consumed for distance calculation using URF is : --- {time.time() - time1} seconds ---"
        )
        return dist_attr0


class ProximityPairer(BaseModel):
    """Pairer using proximity."""

    config: dict
    df_attr_all: pd.DataFrame
    dist_spatial: pd.DataFrame

    @property
    def recs0(self):
        """Receivers."""
        return self.df_attr_all[~self.df_attr_all["is_donor"]]["divide_id"].tolist()

    @property
    def donors0(self):
        """Donors."""
        return self.df_attr_all[self.df_attr_all["is_donor"]]["divide_id"].tolist()

    def pair(self):
        """Perform donor-receiver pairing using proximity."""
        return utils_algo.assign_donors(
            "proximity",
            self.donors0,
            self.recs0,
            self.config,
            None,
            self.dist_spatial,
            None,
        )


# def func(config, df_attr_all, dist_spatial, method="gower"):
#     """Perform donor-receiver pairing.

#     Perform donor-receiver pairing using either Gower's distance (method = "gower") or
#     the distance computed by unsupervised random forest classification (method = "urf").
#     """
#     logger.info("calling function funcs_dist using the " + str(method) + " approach ...")

#     if method == "proximity":
#         recs0 = df_attr_all[~df_attr_all["is_donor"]]["divide_id"].tolist()
#         donors0 = df_attr_all[df_attr_all["is_donor"]]["divide_id"].tolist()
#         df_donor_all = utils_algo.assign_donors(
#             "proximity", donors0, recs0, config, None, dist_spatial, None
#         )
#     else:
#         df_donor_all = pd.DataFrame()

#         # two rounds of processing, first with attributes defined by the selected scenario (e.g., 'hlr'),
#         # and then with 'base' attrs for catchments with no donors found in the 1st round
#         attrs1 = {"main": config["attrs"]["main"], "base": config["attrs"]["base"]}
#         for run1 in attrs1:  # attr round
#             # check if donors are identified for all receivers
#             recs0 = df_attr_all[~df_attr_all["is_donor"]]["divide_id"].values
#             if df_donor_all.shape[1] > 0:
#                 recs0 = [
#                     value
#                     for value in recs0
#                     if value not in df_donor_all["divide_id"].values
#                 ]
#             if len(recs0) == 0:
#                 continue

#             # reduce the attribute table to attributes for the current round
#             df_attr0 = df_attr_all[config["non_attr_cols"] + attrs1[run1]]

#             # iteratively process all the receivers to handle data gaps so that
#             # receivers with the same missing attributes are processed in the same round
#             recs1 = (
#                 list()
#             )  # receivers that have already been processed in previous krounds
#             kround = 0
#             while len([x for x in recs0 if x in recs1]) != len(recs0):
#                 kround = kround + 1
#                 logger.info(
#                     "\n------------------------"
#                     + run1
#                     + " attributes,  Round "
#                     + str(kround)
#                     + "--------------------"
#                 )

#                 # figure out valid attributes to use this round
#                 df_attr = utils_algo.get_valid_attrs(
#                     recs0, recs1, df_attr0, attrs1[run1], config
#                 )

#                 # apply principal component analysis
#                 if (method == "urf") and (not config["pca"]):
#                     myscores = df_attr.drop(config["non_attr_cols"], axis=1)
#                 else:
#                     myscores, weights = utils_algo.apply_pca(
#                         df_attr.drop(config["non_attr_cols"], axis=1)
#                     )

#                 # myscores.to_csv("myscores_1.csv", index=False, float_format="%.3f")

#                 # donors and receivers for this round
#                 donors_all1 = df_attr[df_attr["is_donor"]]["divide_id"].tolist()
#                 receivers_all1 = df_attr[~df_attr["is_donor"]]["divide_id"].tolist()

#                 time1 = time.time()
#                 if method == "gower":
#                     # compute Gower's distance between donors and receivers only, i.e., avoid calculating distance
#                     # between donors and donors, receivers and receivers (faster)
#                     nd1 = len(donors_all1)
#                     nr1 = len(receivers_all1)
#                     rng1 = myscores.max() - myscores.min()
#                     rng2 = np.repeat(np.matrix(rng1), nr1, axis=0)
#                     wgt2 = np.repeat(np.matrix(weights), nr1, axis=0)
#                     dist_attr0 = pd.DataFrame()
#                     scores_receiver = myscores.iloc[nd1:]
#                     dist_attr0 = Parallel(n_jobs=config["njobs"])(
#                         delayed(compute_gower_distance_slow)(
#                             r1, myscores, scores_receiver, rng2, wgt2, nr1
#                         )
#                         for r1 in range(nd1)
#                     )
#                     dist_attr0 = pd.concat(dist_attr0, axis=1)
#                     # for r1 in range(nd1):
#                     #     scores_donor = np.repeat(np.matrix(myscores.iloc[r1]),nr1,axis=0)
#                     #     df1 = ((scores_donor - scores_receiver).abs()/rng2*wgt2).sum(axis=1)
#                     #     dist_attr0 = pd.concat((dist_attr0,df1),axis=1)

#                 elif method == "urf":
#                     # compute attribute distance using unsupervised random forecast classification
#                     rf1 = URF(n_trees=config["n_trees"], max_depth=config["max_depth"])
#                     dist_attr0 = pd.DataFrame(
#                         rf1.get_distance(myscores.to_numpy(), njob=config["njobs"])
#                     )
#                     dist_attr0 = dist_attr0.iloc[len(donors_all1) :, : len(donors_all1)]

#                 else:
#                     sys.exit(
#                         "ERROR: "
#                         + method
#                         + " is not supported for distance based donor-receiver pairing"
#                     )

#                 logger.info(
#                     "\nTime consumed for distance calculation using "
#                     + method
#                     + " is : --- %s seconds ---" % (time.time() - time1)
#                 )

#                 dist_attr0.columns = donors_all1
#                 dist_attr0.index = receivers_all1
#                 dist_attr0 = dist_attr0.round(3)

#                 # determine which receivers to be processed for the current round
#                 # process only those not-yet processed receivers
#                 recs = [r1 for r1 in recs0 if r1 in receivers_all1 and r1 not in recs1]
#                 recs1 = recs1 + recs
#                 logger.info(str(len(recs)) + " receivers to be processed this round")

#                 df_donor_all1 = Parallel(n_jobs=config["njobs"])(
#                     delayed(identify_donor_slow)(
#                         rec1,
#                         config,
#                         method,
#                         df_attr,
#                         df_attr_all,
#                         dist_spatial,
#                         dist_attr0,
#                         run1,
#                     )
#                     for rec1 in recs
#                 )

#                 df_donor_all1 = pd.concat(df_donor_all1, axis=0)
#                 df_donor_all = pd.concat((df_donor_all, df_donor_all1), axis=0)

#     return df_donor_all
