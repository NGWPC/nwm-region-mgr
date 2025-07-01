"""Clustering functions.

This function performs donor-receiver pairing based on clustering using
  k-means clustering (method = "kmeans")
  k-medoids clustering (method = "kmedoids")
  HDBSCAN (method = "hdbscan") - Hierarchical Density-Based Spatial Clustering of Applications with Noise.
     Finds core samples of high density and expands clusters from them.
  BIRCH (method = "birch") - Balanced Iterative Reducing & Clustering with Hierarchy. Scalable for large datasets.
     Order of points in the dataset influences the outcome. Hence interactive resampling is implemented here.

Notes:
  1) the clustering is done in multiple rounds to handle data gaps in attributes
  2) snow and non-snow basins are processed separately

"""

import logging
import warnings
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from hdbscan import HDBSCAN
from joblib import Parallel, delayed
from pydantic import BaseModel
from sklearn.cluster import Birch, KMeans
from sklearn_extra.cluster import KMedoids

from . import utils_algo

warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn")

logger = logging.getLogger(__name__)


class ClusterPairer(BaseModel, ABC):
    """Cluster Pairer."""

    config: dict
    df_attr_all: pd.DataFrame
    dist_spatial: pd.DataFrame

    @property
    def attrs(self):
        """Attributes."""
        return self.config["attrs"]["main"]

    @property
    def receivers(self):
        """All receivers to find donor for."""
        return self.df_attr_all[~self.df_attr_all["is_donor"]]["divide_id"].values

    @property
    def total_number_of_receivers(self):
        """Total number of receivers."""
        return len(self.receivers)

    @property
    def df_attributes(self):
        """Reduce attribute table to the attributes for the current run.

        Note in the attribute table, donors are listed first, followed by receivers.
        """
        return self.df_attr_all[self.config["non_attr_cols"] + self.attrs]

    @abstractmethod
    def _pair(self):
        """Perform donor-receiver pairing using clustering methods.

        1.  Identify groups of catchments with the same types of attributes.
        2.  Perform dimensionality reduction on the attributes (Principal Component Analysis).
        3.  Further split catchment groups by snow/no snow.
        4.  Apply clustering to pair each receiver catchment with a donor catchment.
        5.  If a receiver is not able to be clustered with a donor, then associate it with the spatially nearest donor in the group.
        """
        logger.info(
            f"Total number of receivers to be paired with donors: {self.total_number_of_receivers}"
        )

        processed_receivers_df = pd.DataFrame()

        # iteratively process all the receivers to handle data gaps (because some attributes may be missing for some catchments)
        kround = 0
        processed_receiver_ids = []
        while True:
            kround = kround + 1
            logger.info(f"------------------------ Round {kround}--------------------")

            # when all receivers are paired with donors, exit
            if len(processed_receiver_ids) == self.total_number_of_receivers:
                break

            # determine valid attributes to use this round
            df_attr = utils_algo.get_valid_attrs(
                self.receivers,
                processed_receiver_ids,
                self.df_attributes,
                self.config,
            )

            # apply principal component analysis to reduce dimensionality
            df_attr_reduced, _ = utils_algo.apply_pca(
                df_attr.drop(self.config["non_attr_cols"], axis=1)
            )

            # process snowy and non-snowy catchments separately
            processed_receivers_df = self.process_snow_groups(
                df_attr, df_attr_reduced, processed_receivers_df, snowy=True
            )
            processed_receivers_df = self.process_snow_groups(
                df_attr, df_attr_reduced, processed_receivers_df, snowy=False
            )

            processed_receiver_ids = processed_receivers_df["divide_id"].unique()

        return processed_receivers_df

    @abstractmethod
    def process_snow_groups(
        self,
        df_attr: pd.DataFrame,
        df_attr_reduced: pd.DataFrame,
        processed_receivers_df,
        snowy: bool,
    ):
        """Process a group subsetting further by snowy vs non-snowy.

        snowy is a bool
        """
        df_attr = df_attr[df_attr["snowy"] == snowy]
        df_attr_reduced = df_attr_reduced[df_attr["snowy"] == snowy]

        donors = df_attr[df_attr["is_donor"]]["divide_id"].tolist()
        receivers = df_attr[~df_attr["is_donor"]]["divide_id"].tolist()

        if snowy:
            logger.info(f"======= {len(receivers)} snowy  catchments ========")
        else:
            logger.info(f"======= {len(receivers)} non-snowy  catchments ========")

        cgp = ClusterGroupPairer(
            donors,
            receivers,
            df_attr_reduced,
            processed_receivers_df,
            self.config,
            self.dist_spatial,
            self.df_attr_all,
            self._apply_algorithm,
        )
        return cgp.process_group()


class ClusterGroupPairer:
    """Cluster Group Pairer."""

    def __init__(
        self,
        donors: pd.DataFramer,
        receivers: pd.DataFrame,
        df_attr_reduced: pd.DataFrame,
        processed_receivers_df: pd.DataFrame,
        config: dict,
        dist_spatial: pd.DataFrame,
        df_attr_all: pd.DataFrame,
        _apply_algorithm,
    ):
        """Initialize Cluster Group Pairer."""
        self.donors = donors
        self.receivers = receivers
        self.df_attr_reduced = df_attr_reduced
        self.processed_receivers_df = processed_receivers_df
        self.config = config
        self.dist_spatial = dist_spatial
        self.df_attr_all = df_attr_all
        self._apply_algorithm = _apply_algorithm

    @property
    def receivers_to_be_processed_for_group(self) -> list:
        """Get receivers that need to be processed."""
        return [
            x
            for x in self.receivers
            if x not in self.processed_receivers_df["divide_id"].tolist()
        ]

    @property
    def initial_labels(self) -> np.array:
        """Get initial labels."""
        # define starting labels
        labels = np.zeros(
            len(self.df_attr_reduced)
        )  # start with a single cluster (label = 0)

        # for those already processed, assign "label_done"
        if self.processed_receivers_df.shape[0] > 0:
            labels[
                [
                    self.number_of_donors + self.receivers.index(x)
                    for x in self.receivers
                    if x in self.all_donor_ids
                ]
            ] = self.label_done  # label = -99 indicates donor identified

    @property
    def processed_receiver_ids(self) -> list:
        """Processed receivers ids."""
        return self.processed_receivers_df["divide_id"].tolist()

    @property
    def number_of_donors(self) -> int:
        """Number of donors for this grouping."""
        return len(self.donors)

    @property
    def label_done(self) -> int:
        """Label = -99 indicates donor identified."""
        return -99

    def receiver_label(self, labels: np.array) -> np.array:
        """Receiver_label."""
        receiver_label = np.unique(labels[self.number_of_donors :], return_counts=False)
        return receiver_label[receiver_label != self.label_done]

    @property
    def njob(self) -> int:
        """Number of jobs."""
        njob = self.config["njobs"]
        if njob > len(self.receiver_label):
            njob = len(self.receiver_label)
        return njob

    def update_processed_receivers_and_labels(
        self,
        pairing_results: tuple,
        processed_receivers_for_group_df: pd.DataFrame,
        labels: np.array,
    ) -> tuple:
        """Update donors and labels."""
        for result, result_labels in pairing_results:
            processed_receivers_for_group_df = pd.concat(
                (processed_receivers_for_group_df, result), axis=0
            )

            label_rec1 = np.unique(
                result_labels[self.number_of_donors :], return_counts=False
            )

            label_rec1 = label_rec1[label_rec1 != 0]
            for l1 in label_rec1:
                if l1 == self.label_done:
                    labels = np.where(result_labels == l1, self.label_done, labels)
                else:
                    labels = np.where(result_labels == l1, labels.max() + 1, labels)
        return processed_receivers_for_group_df, labels

    def update_iteration(
        self,
        iteration: int,
        processed_receivers_for_group_df: pd.DataFrame,
        number_of_receivers_with_donor: int,
    ) -> int:
        """Update the iteration based on number of receivers with donors and receivers that have already been processed."""
        if number_of_receivers_with_donor != processed_receivers_for_group_df.shape[0]:
            return 0
        else:
            return iteration + 1

    def check_convergence(
        self, iteration: int, number_of_receivers_with_donor: int
    ) -> bool:
        """Check for convergence.

        If the number of receivers with donors identified has not changed for a number of iterations,
        or if the number of receivers without donors identified becomes really small,
        consider the algorithm converging.
        """
        if (
            (iteration > 50)
            | (
                number_of_receivers_with_donor
                / len(self.receivers_to_be_processed_for_group)
                * 100
                > 98
            )
            | (len(self.receivers_to_be_processed_for_group) < 5)
        ):
            return True

    def get_receivers_for_proximity_algorithm(
        self,
        processed_receivers_for_group_df: pd.DataFrame,
    ) -> list:
        """Get receivers that will use did not converge and will use the proximity algorithm."""
        if processed_receivers_for_group_df.shape[0] == 0:
            return self.receivers_to_be_processed_for_group.copy()
        else:
            return [
                x
                for x in self.receivers_to_be_processed_for_group
                if x not in processed_receivers_for_group_df["divide_id"].tolist()
            ]

    def apply_proximity_algorithm(
        self,
        receivers_for_proximity_algorithm: pd.DataFrame,
        processed_receivers_for_group_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Apply proximity algorithm."""
        logger.info(
            f"Algorithm converged without donors identified for {len(receivers_for_proximity_algorithm)} receivers ... use proximity for these receivers"
        )
        proximity_results = utils_algo.assign_donors(
            "proximity",
            self.donors,
            receivers_for_proximity_algorithm,
            self.config,
            None,
            self.dist_spatial,
            self.df_attr_all,
        )
        processed_receivers_for_group_df = pd.concat(
            [processed_receivers_for_group_df, proximity_results],
            axis=0,
        )

    def process_group(
        self,
    ) -> pd.DataFrame:
        """Process a group of receivers.

        Iterate through all receivers to be processed for this group until all receivers in
        the group have been processed.

            1.

        """
        if len(self.receivers_to_be_processed_for_group) == 0:
            return self.processed_receivers_df

        # identify donors iteratively
        # data frame to hold donor table for the current snowy group
        processed_receivers_for_group_df = pd.DataFrame()
        iter1 = iter2 = 0
        number_of_receivers_with_donor = processed_receivers_for_group_df.shape[0]
        labels = self.initial_labels
        while len(processed_receivers_for_group_df) < len(
            self.receivers_to_be_processed_for_group
        ):
            iter1 += 1

            logger.info(f"===== iter1= {iter1} ======")
            logger.info(f"Using {self.njob} processors ...")

            # iterate through all clusters, break the cluster if necessary, or choose donors if the cluster is no longer breakable
            pairing_results = Parallel(n_jobs=self.njob)(
                delayed(self.identify_donor_by_cluster)(
                    ll, labels, processed_receivers_for_group_df
                )
                for ll in self.receiver_label(labels)
            )

            # update donors and labels
            processed_receivers_for_group_df, labels = (
                self.update_processed_receivers_and_labels(
                    pairing_results, processed_receivers_for_group_df, labels
                )
            )
            # update iter2 as necessary
            iter2 = self.update_iteration(
                iter2, processed_receivers_for_group_df, number_of_receivers_with_donor
            )
            if iter2 != 0:
                # check convergence
                if self.check_convergence(iter2, number_of_receivers_with_donor):
                    # get receivers for proximity algorithm
                    receivers_for_proximity_algorithm = (
                        self.get_receivers_for_proximity_algorithm(
                            processed_receivers_for_group_df
                        )
                    )
                    if len(receivers_for_proximity_algorithm) > 0:
                        # apply proximity algorithm
                        processed_receivers_for_group_df = (
                            self.apply_proximity_algorithm(
                                receivers_for_proximity_algorithm,
                                processed_receivers_for_group_df,
                            )
                        )
                    break

            # update progress
            self.update_progress(processed_receivers_for_group_df)

            # update number of receivers with donors identified
            number_of_receivers_with_donor = processed_receivers_for_group_df.shape[0]

        # add to the final donor table
        return pd.concat(
            (self.processed_receivers_df, processed_receivers_for_group_df), axis=0
        )

    def update_progress(
        self, iter1: int, processed_receivers_for_group_df: pd.DataFrame
    ) -> None:
        """Update progress on donor-receiver pairing."""
        if iter1 > 1:
            logger.info(f"---------------- iteration = {iter1 - 1} -------------")
            logger.info(
                f"Number of receivers with donors identified: {processed_receivers_for_group_df.shape[0]}"
            )
            if processed_receivers_for_group_df.shape[0] > 0:
                uniq, freq = np.unique(
                    processed_receivers_for_group_df["tag"], return_counts=True
                )
                logger.info(dict(zip(uniq, freq)))

    def cluster_donors_receivers(self, receiver_label, labels: np.array):
        """Return the donors and receivers for the current cluster."""
        donors = [x for i, x in enumerate(self.donors) if labels[i] == receiver_label]
        receivers = [
            x
            for i, x in enumerate(self.receivers)
            if labels[i + len(self.donors)] == receiver_label
        ]
        return donors, receivers

    def get_receivers_to_be_processed(
        self, processed_receivers_for_group_df: pd.DataFrame, cluster_receivers: list
    ):
        """Receivers in the current cluster that still need to be processed."""
        processed_ids = set(
            processed_receivers_for_group_df["divide_id"].tolist()
            + self.processed_receivers_df["divide_id"].tolist()
        )
        if processed_ids > 0:
            return [x for x in cluster_receivers if x not in processed_ids]
        else:
            return cluster_receivers.copy()

    def get_cluster_df_attr_reduced(self, cluster_df_attr_reduced_index: list):
        """Get cluster df_attr_reduced."""
        return self.df_attr_reduced.iloc[cluster_df_attr_reduced_index]

    def get_cluster_df_attr_reduced_index(
        self, cluster_donors: list, cluster_receivers: list
    ):
        """Get cluster df_attr_reduced index."""
        idx1 = [self.donors.index(x) for x in cluster_donors]
        idx2 = [self.receivers.index(x) for x in cluster_receivers]
        return idx1 + [x + len(self.donors) for x in idx2]

    def update_fit_labels(self, fit):
        """Update fit labels."""
        fit.labels_ = (
            fit.labels_ + 2
        )  # add 2 to the cluster labels because hdbscan cluster starts with -1

    def get_cluster_receiver_donor_labels(
        self, fit: KMeans | KMedoids | HDBSCAN | Birch, cluster_donors: list
    ):
        """Get cluster labels for receivers and donors."""
        cluster_receiver_labels = np.unique(
            fit.labels_[len(cluster_donors) :], return_counts=False
        )  # receiver clusters
        cluster_donor_labels = np.unique(
            fit.labels_[: len(cluster_donors)], return_counts=False
        )  # donor clusters
        return cluster_receiver_labels, cluster_donor_labels

    def apply_clustering(
        self, cluster_donors: list, cluster_receivers: list, cluster_labels: np.array
    ):
        """Apply clustering algorithm.

        1.  Apply clustering alogrithm.
        2.  Update labels for clusters.
        3.  Identinfy receivers that are in clusters with no donors.
        4.  Assign donorless receivers a donor from the parent cluster (from the previous iteration).
        5.  Update labels for this cluster iteration.
        """
        # apply clustering
        cluster_df_attr_reduced_index = self.get_cluster_df_attr_reduced_index(
            cluster_donors, cluster_receivers
        )
        cluster_df_attr_reduced = self.get_cluster_df_attr_reduced(
            cluster_df_attr_reduced_index
        )
        fit = self._apply_algorithm(
            cluster_df_attr_reduced, cluster_receivers, cluster_donors
        )

        # update labels
        fit = self.update_fit_labels(fit)
        cluster_labels[cluster_df_attr_reduced_index] = fit.labels_
        cluster_receiver_labels, cluster_donor_labels = (
            self.get_cluster_receiver_donor_labels(fit, cluster_donors)
        )

        # for receivers in clusters without donors, or clusters that cannot be subset further,
        # choose donors from those in the parent cluster (donors1)
        cluster_receiver_labels_with_no_donor_in_cluster = [
            x for x in cluster_receiver_labels if x not in cluster_donor_labels
        ]
        if (
            (len(cluster_receiver_labels) == 1)
            and (len(cluster_donor_labels) == 1)
            and (cluster_donor_labels[0] == cluster_receiver_labels[0])
        ):
            cluster_receiver_labels_with_no_donor_in_cluster = cluster_receiver_labels

        # get receivers with with no donor in cluster
        if len(cluster_receiver_labels_with_no_donor_in_cluster) > 0:
            recs3 = [
                x
                for ii, x in enumerate(cluster_receivers)
                if fit.labels_[len(cluster_donors) :][ii]
                in cluster_receiver_labels_with_no_donor_in_cluster
            ]

            cluster_labels[
                [self.receivers.index(x) + len(self.donors) for x in recs3]
            ] = self.label_done

            return utils_algo.assign_donors(
                "main",
                cluster_donors,
                recs3,
                self.config,
                None,
                self.dist_spatial,
                self.df_attr_all,
            ), cluster_labels

    def identify_donor_by_cluster(
        self,
        receiver_label: int,
        labels: np.array,
        processed_receivers_for_group_df: pd.DataFrame,
    ):
        """Identify donor using clustering if possible, otherwise use spatial proximity.

        1.  Check if there are any donors in the cluster; if there are move to step 2.
            If there are no donors in the cluster choose from all donors based on spatial proximity

        2.  If number of donors in the cluster is larger than the defined 'nDonorMax',
            break the cluster into multiple clusters using the dimensionally reduced attributes.
            If the number of donors in the cluster is smaller than defined 'nDonorMax', do not
            perform further clustering; simply identify donors.
        """
        cluster_labels = np.zeros(self.df_attr_reduced.shape[0])

        # donors and receivers in the current cluster
        cluster_donors, cluster_receivers = self.cluster_donors_receivers(
            receiver_label, labels
        )

        # receivers in the current cluster that still need to be processed
        receivers_to_be_processed = self.get_receivers_to_be_processed(
            self, processed_receivers_for_group_df, cluster_receivers
        )

        # if there exist donors in the cluster
        if len(cluster_donors) > 0:
            # if number of donors in the cluster is larger than the defined 'nDonorMax', proceed to break the cluster further down
            if len(cluster_donors) > self.config["n_donor_max"]:
                return self.apply_clustering(
                    cluster_donors, cluster_receivers, cluster_labels
                )
            else:
                # for receivers in clusters with number of donors smaller than 'n_donor_max', no further clustering is needed
                # identify donors from the current cluster
                cluster_labels[labels == receiver_label] = self.label_done
                return utils_algo.assign_donors(
                    "main",
                    cluster_donors,
                    receivers_to_be_processed,
                    self.config,
                    None,
                    self.dist_spatial,
                    self.df_attr_all,
                ), cluster_labels
        # for receivers in clusters without donors, choose from all donors based on spatial proximity
        else:
            cluster_labels[labels == receiver_label] = self.label_done
            return utils_algo.assign_donors(
                "proximity",
                self.donors,
                receivers_to_be_processed,
                self.config,
                None,
                self.dist_spatial,
                self.df_attr_all,
            ), cluster_labels


class KmeansPairer(ClusterPairer):
    """Kmeans Pairer.

    A class for pairing donor-receiver catchments using sklearn's KMeans.
    https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html#sklearn.cluster.KMeans.fit
    """

    def pair(self):
        """Pair the donor-receiver using Kmeans."""
        logger.info("perform clustering using Kmeans approach ...")
        self._pair()

    def _apply_algorithm(
        self, df_attr_reduced: pd.DataFrame, receivers: list, donors: list
    ) -> KMeans:
        """Apply Kmeans alogrithm."""
        return KMeans(
            init=self.config["init"],
            n_clusters=2,
            n_init=self.config["n_init"],
            max_iter=self.config["n_iter_max"],
            random_state=42,
        ).fit(df_attr_reduced)


class KmedoidsPairer(ClusterPairer):
    """KMedoids Pairer.

    A class for pairing donor-receiver catchments using sklearn_extra's KMedoids.
    https://scikit-learn-extra.readthedocs.io/en/stable/generated/sklearn_extra.cluster.KMedoids.html
    """

    def pair(self):
        """Pair the donor-receiver using KMedoids."""
        logger.info("perform clustering using KMedoids approach ...")
        self._pair()

    def _apply_algorithm(
        self, df_attr_reduced: pd.DataFrame, receivers: list, donors: list
    ) -> KMedoids:
        """Apply KMedoids alogrithm."""
        return KMedoids(
            init=self.config["init"],
            n_clusters=2,
            max_iter=self.config["n_iter_max"],
            random_state=42,
        ).fit(df_attr_reduced)


class HDBSCANPairer(ClusterPairer):
    """HDBSCAN Pairer.

    A class for pairing donor-receiver catchments using hdbscan's HDBSCAN.
    https://hdbscan.readthedocs.io/en/latest/
    """

    def pair(self):
        """Pair the donor-receiver using HDBSCAN."""
        logger.info("perform clustering using HDBSCAN approach ...")
        self._pair()

    def _apply_algorithm(
        self, df_attr_reduced: pd.DataFrame, receivers: list, donors: list
    ) -> HDBSCAN:
        """Apply HDBSCAN alogrithm."""
        return HDBSCAN(
            min_samples=11,
            min_cluster_size=self.config["min_cluster_size"],
            allow_single_cluster=False,
        ).fit(df_attr_reduced)


class BIRCH(ClusterPairer):
    """BIRCH Pairer.

    A class for pairing donor-receiver catchments using sklearn's Birch.
    https://scikit-learn.org/stable/modules/generated/sklearn.cluster.Birch.html
    """

    def pair(self):
        """Pair the donor-receiver using BIRCH."""
        logger.info("perform clustering using BIRCH approach ...")
        self._pair()

    def _apply_algorithm(
        self, df_attr_reduced: pd.DataFrame, receivers: list, donors: list
    ) -> Birch:
        """Apply BIRCH algorithm."""
        # explore a range of threshold values to identify a proper threshold parameter for BIRCH
        for thresh in np.arange(
            self.config["min_thresh"], self.config["max_thresh"] + 0.1, 0.1
        ):
            # shuffle the donor/receiver positions in the data to get optimal results, via resampling
            kk = 0
            while kk < self.config["max_resample"]:
                kk = kk + 1
                mydata2 = self.mydata1.sample(frac=1)  # reorder the data
                fit1 = Birch(
                    branching_factor=self.config["branching_factor"],
                    n_clusters=None,
                    threshold=thresh,
                ).fit(mydata2)
                fit1.labels_ = fit1.labels_[
                    [mydata2.index.get_loc(x) for x in df_attr_reduced.index]
                ]
                u1 = np.unique(fit1.labels_[: len(donors)], return_counts=False)
                n_clust = len(np.unique(fit1.labels_, return_counts=False))
                nrec_donor = sum(np.in1d(fit1.labels_[len(donors) :], u1))

                # if a donor is identified for all receivers, quit the iteration loop
                if (n_clust > 1) and (nrec_donor == len(receivers)):
                    break

            if (n_clust > 1) and (nrec_donor == len(receivers)):
                break
        return fit1


def func(config, df_attr_all, dist_spatial, method):
    """Perform clustering using provided method."""
    logger.info("perform clustering using " + str(method) + " approach ...")

    df_donor_all = pd.DataFrame()

    # all receivers to find donor for
    recs0 = df_attr_all[~df_attr_all["is_donor"]]["divide_id"].values
    logger.info(
        "\n Total number of receivers to be paired with donors: " + str(len(recs0))
    )

    # attributes to be used for the current run
    # attrs1 = config['attrs'][scenario]
    attrs1 = config["attrs"]["main"]

    # reduce attribute table to the attributes for the current run
    # note in the attribute table, donors are listed first, followed by receivers
    df_attr0 = df_attr_all[config["non_attr_cols"] + attrs1]

    # iteratively process all the receivers to handle data gaps (because some attributes may be missing for some catchments)
    kround = 0
    while True:
        recs = list()
        if df_donor_all.shape[0] > 0:
            recs = np.unique(df_donor_all["divide_id"])

        # when all receivers are paired with donors, exit
        if len([x for x in recs0 if x in recs]) == len(recs0):
            break

        kround = kround + 1
        logger.info(
            "\n------------------------ Round " + str(kround) + "--------------------"
        )

        # figure out valid attributes to use this round
        df_attr = utils_algo.get_valid_attrs(recs0, recs, df_attr0, attrs1, config)

        # apply principal component analysis
        myscores, _ = utils_algo.apply_pca(
            df_attr.drop(config["non_attr_cols"], axis=1)
        )

        # process snowy and non-snowy catchments sparately
        for snow1 in np.unique(df_attr["snowy"]):
            str1 = "non-snowy" if snow1 else "snowy"

            # the current snowy group
            df_attr1 = df_attr[df_attr["snowy"] == snow1]
            scores1 = myscores[(df_attr["snowy"] == snow1).values]
            donors = df_attr1[df_attr1["is_donor"]]["divide_id"].tolist()
            receivers = df_attr1[~df_attr1["is_donor"]]["divide_id"].tolist()

            # receivers to be processed in this round
            recs1 = receivers.copy()
            if df_donor_all.shape[0] > 0:
                recs1 = [
                    x for x in recs1 if x not in df_donor_all["divide_id"].tolist()
                ]
            logger.info(
                "\n======= " + str(len(recs1)) + " " + str1 + " catchments ========"
            )
            if len(recs1) == 0:
                continue

            # define starting labels
            labels = np.zeros(
                scores1.shape[0]
            )  # start with a single cluster (label = 0)
            label_done = -99  # label = -99 indicates donor identified

            # for those already processed, assign "label_done"
            if df_donor_all.shape[0] > 0:
                labels[
                    [
                        len(donors) + receivers.index(x)
                        for x in receivers
                        if x in df_donor_all["divide_id"].tolist()
                    ]
                ] = label_done

            # identify donors iteratively
            df_donor_snow = (
                pd.DataFrame()
            )  # data frame to hold donor table for the current snowy group
            iter1 = iter2 = 0
            nrec_with_donor0 = df_donor_snow.shape[0]
            while df_donor_snow.shape[0] < len(recs1):
                iter1 = iter1 + 1

                # get receiver clusters (and ignore those already processed)
                label_rec, count_rec = np.unique(
                    labels[len(donors) :], return_counts=True
                )
                count_rec = count_rec[label_rec != label_done]
                label_rec = label_rec[label_rec != label_done]

                logger.info("===== iter1=" + str(iter1) + " ======")
                # logger.info("labels: " + str(np.unique(labels)))

                # make a copy of current labels (which will change during the iteration of clusters)
                # labels1 = labels.copy()

                # iterate through all clusters, break the cluster if necessary, or choose donors if the cluster is no longer breakable
                njob = config["njobs"]
                if njob > len(label_rec):
                    njob = len(label_rec)
                logger.info("Using " + str(njob) + " processors ...")
                results = Parallel(n_jobs=njob)(
                    delayed(identify_donor_by_cluster)(
                        donors,
                        ll,
                        labels,
                        receivers,
                        df_donor_all,
                        df_donor_snow,
                        config,
                        method,
                        scores1,
                        dist_spatial,
                        df_attr_all,
                        label_done,
                    )
                    for ll in label_rec
                )

                # update donors and labels
                for i1 in range(njob):
                    # logger.info("i1="+str(i1)+", # of receivers with donors=" + str(results[i1][0].shape[0]))
                    df_donor_snow = pd.concat((df_donor_snow, results[i1][0]), axis=0)

                    labels_temp = results[i1][1]
                    # logger.info("labels_temp: " + str(np.unique(labels_temp)))
                    label_rec1 = np.unique(
                        labels_temp[len(donors) :], return_counts=False
                    )
                    label_rec1 = label_rec1[label_rec1 != 0]
                    for l1 in label_rec1:
                        if l1 == label_done:
                            labels = np.where(labels_temp == l1, label_done, labels)
                        else:
                            labels = np.where(
                                labels_temp == l1, labels.max() + 1, labels
                            )
                    # logger.info("labels: " + str(np.unique(labels)))

                # check if algorithm converges (based on number of receivers with donors identified)
                if nrec_with_donor0 != df_donor_snow.shape[0]:
                    iter2 = 0
                else:
                    iter2 = iter2 + 1
                    # if the number of receivers with donors identified has not changed for a number of iterations,
                    # or if the number of receivers without donors identified becomes really small,
                    # consider the algorithm converging
                    if (
                        (iter2 > 50)
                        | (nrec_with_donor0 / len(recs1) * 100 > 98)
                        | (len(recs1) < 5)
                    ):
                        if df_donor_snow.shape[0] == 0:
                            recs2 = recs1.copy()
                        else:
                            recs2 = [
                                x
                                for x in recs1
                                if x not in df_donor_snow["divide_id"].tolist()
                            ]
                        if len(recs2) > 0:
                            logger.info(
                                "\nAlgorithm converged without donors identified for "
                                + str(len(recs2))
                                + " receivers ... use proximity for these receivers"
                            )
                            df_donor_snow = pd.concat(
                                (
                                    df_donor_snow,
                                    utils_algo.assign_donors(
                                        "proximity",
                                        donors,
                                        recs2,
                                        config,
                                        None,
                                        dist_spatial,
                                        df_attr_all,
                                    ),
                                ),
                                axis=0,
                            )
                        break

                # update progress on donor-receiver pairing
                if iter1 > 1:
                    logger.info(
                        "\n---------------- iteration = "
                        + str(iter1 - 1)
                        + " -------------"
                    )
                    logger.info(
                        "Number of receivers with donors identified: "
                        + str(df_donor_snow.shape[0])
                    )
                    if df_donor_snow.shape[0] > 0:
                        uniq, freq = np.unique(df_donor_snow["tag"], return_counts=True)
                        logger.info(dict(zip(uniq, freq)))

                # update number of receivers with donors identified
                nrec_with_donor0 = df_donor_snow.shape[0]

            # end while (iteration) loop

            # add to the final donor table
            df_donor_all = pd.concat((df_donor_all, df_donor_snow), axis=0)

        # end of loop snow1 (to separately processing for snow and non-snow dominated receivers)
    # end of loop kround (to use valid attributes)

    return df_donor_all


def identify_donor_by_cluster(
    donors,
    ll,
    labels,
    receivers,
    df_donor_all,
    df_donor_snow,
    config,
    method,
    scores1,
    dist_spatial,
    df_attr_all,
    label_done,
):
    """Identify donor using clustering."""
    df_donor = pd.DataFrame()

    # initialize new labels for the current cluster
    labels1 = np.zeros(scores1.shape[0])

    # donors and receivers in the current cluster
    donors1 = [x for jj, x in enumerate(donors) if labels[jj] == ll]
    receivers1 = [x for jj, x in enumerate(receivers) if labels[jj + len(donors)] == ll]

    # receivers in the current cluster that still need to be processed
    recs2 = receivers1.copy()
    if df_donor_snow.shape[0] > 0:
        recs2 = [x for x in recs2 if x not in df_donor_snow["divide_id"].tolist()]

    # if there exist donors in the cluster
    if len(donors1) > 0:
        # if number of donors in the cluster is larger than the defined 'nDonorMax', proceed to break the cluster further down
        if len(donors1) > config["n_donor_max"]:
            idx1 = [donors.index(x) for x in donors1]
            idx2 = [receivers.index(x) for x in receivers1]
            idx0 = idx1 + [x + len(donors) for x in idx2]
            mydata1 = scores1.iloc[idx0]

            if method in ["kmeans", "kmedoids"]:
                # break the dataset into two clusters each time
                if method == "kmeans":
                    fit1 = KMeans(
                        init=config["init"],
                        n_clusters=2,
                        n_init=config["n_init"],
                        max_iter=config["n_iter_max"],
                        random_state=42,
                    ).fit(mydata1)
                elif method == "kmedoids":
                    fit1 = KMedoids(
                        init=config["init"],
                        n_clusters=2,
                        max_iter=config["n_iter_max"],
                        random_state=42,
                    ).fit(mydata1)

            elif method == "hdbscan":
                fit1 = HDBSCAN(
                    min_samples=11,
                    min_cluster_size=config["min_cluster_size"],
                    allow_single_cluster=False,
                ).fit(mydata1)

            elif method == "birch":
                # explore a range of threshold values to identify a proper threshold parameter for BIRCH
                for thresh in np.arange(
                    config["min_thresh"], config["max_thresh"] + 0.1, 0.1
                ):
                    # shuffle the donor/receiver positions in the data to get optimal results, via resampling
                    kk = 0
                    while kk < config["max_resample"]:
                        kk = kk + 1
                        mydata2 = mydata1.sample(frac=1)  # reorder the data
                        fit1 = Birch(
                            branching_factor=config["branching_factor"],
                            n_clusters=None,
                            threshold=thresh,
                        ).fit(mydata2)
                        fit1.labels_ = fit1.labels_[
                            [mydata2.index.get_loc(x) for x in mydata1.index]
                        ]
                        u1 = np.unique(
                            fit1.labels_[: len(donors1)], return_counts=False
                        )
                        n_clust = len(np.unique(fit1.labels_, return_counts=False))
                        nrec_donor = sum(np.in1d(fit1.labels_[len(donors1) :], u1))

                        # if a donor is identified for all receivers, quit the iteration loop
                        if (n_clust > 1) and (nrec_donor == len(receivers1)):
                            break

                    if (n_clust > 1) and (nrec_donor == len(receivers1)):
                        break

            fit1.labels_ = (
                fit1.labels_ + 2
            )  # add 2 to the cluster labels because hdbscan cluster starts with -1
            labels1[idx0] = fit1.labels_  # + labels1.max()
            label_rec1 = np.unique(
                fit1.labels_[len(donors1) :], return_counts=False
            )  # receiver clusters
            label_don1 = np.unique(
                fit1.labels_[: len(donors1)], return_counts=False
            )  # donor clusters

            # logger.info('Group ' +str(ll) + ' receiver clusters: ' + str(label_rec1))
            # logger.info('Group ' +str(ll) + ' donor clusters: ' + str(label_don1))
            # logger.info('Group ' +str(ll) + ' # of donors: ' + str(len(donors1)))
            # logger.info('Group ' +str(ll) + ' # of receivers: ' + str(len(receivers1)))
            # logger.info('Group ' +str(ll) + ' # of receivers to be processed: ' + str(len(recs2)))

            # for receivers in clusters without donors, or clusters that cannot be subset further,
            # choose donors from those in the parent cluster (donors1)
            l1 = [x for x in label_rec1 if x not in label_don1]
            if (
                (len(label_rec1) == 1)
                and (len(label_don1) == 1)
                and (label_don1[0] == label_rec1[0])
            ):
                l1 = label_rec1
            if len(l1) > 0:
                recs3 = [
                    x
                    for ii, x in enumerate(receivers1)
                    if fit1.labels_[len(donors1) :][ii] in l1
                ]
                df_donor = pd.concat(
                    (
                        df_donor,
                        utils_algo.assign_donors(
                            "main",
                            donors1,
                            recs3,
                            config,
                            None,
                            dist_spatial,
                            df_attr_all,
                        ),
                    ),
                    axis=0,
                )
                labels1[[receivers.index(x) + len(donors) for x in recs3]] = label_done

        else:
            # for receivers in clusters with number of donors smaller than 'n_donor_max', no further clustering is needed
            # identify donors from the current cluster
            df_donor = pd.concat(
                (
                    df_donor,
                    utils_algo.assign_donors(
                        "main", donors1, recs2, config, None, dist_spatial, df_attr_all
                    ),
                ),
                axis=0,
            )
            labels1[labels == ll] = label_done

    # for receivers in clusters without donors, chooses from all donors based on spatial proximity
    else:
        # logger.info("cluster " + str(ll) + ", number of receivers with proximity donors: " + str(recs2))
        df_donor = pd.concat(
            (
                df_donor,
                utils_algo.assign_donors(
                    "proximity", donors, recs2, config, None, dist_spatial, df_attr_all
                ),
            ),
            axis=0,
        )
        labels1[labels == ll] = label_done

    return df_donor, labels1
