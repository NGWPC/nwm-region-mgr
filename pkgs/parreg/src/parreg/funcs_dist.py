import sys
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from . import utils_algo
from .unsupervised_random_forest import urf


# This function performs donor-receiver pairing using either Gower's distance (method = "gower") or
#   the distance computed by unsurpervised random forest classification (method = "urf")
#
def func(config, dfAttrAll, dist_spatial, method="gower"):
    print("calling function funcs_dist using the " + str(method) + " approach ...")

    if method == "proximity":
        recs0 = dfAttrAll[~dfAttrAll["is_donor"]]["divide_id"].tolist()
        donors0 = dfAttrAll[dfAttrAll["is_donor"]]["divide_id"].tolist()
        dfDonorAll = utils_algo.assign_donors("proximity", donors0, recs0, config, None, dist_spatial, None)
    else:
        dfDonorAll = pd.DataFrame()

        # two rounds of processing, first with attributes defined by the selected scenario (e.g., 'hlr'),
        # and then with 'base' attrs for catchments with no donors found in the 1st round
        attrs1 = {"main": config["attrs"]["main"], "base": config["attrs"]["base"]}
        for run1 in attrs1:  # attr round
            # check if donors are identified for all receivers
            recs0 = dfAttrAll[~dfAttrAll["is_donor"]]["divide_id"].values
            if dfDonorAll.shape[1] > 0:
                recs0 = [value for value in recs0 if value not in dfDonorAll["divide_id"].values]
            if len(recs0) == 0:
                continue

            # reduce the attribute table to attributes for the current round
            dfAttr0 = dfAttrAll[config["non_attr_cols"] + attrs1[run1]]

            # iteratively process all the receivers to handle data gaps so that
            # receivers with the same missing attributes are processed in the same round
            recs1 = list()  # receivers that have already been processed in previous krounds
            kround = 0
            while len([x for x in recs0 if x in recs1]) != len(recs0):
                kround = kround + 1
                print(
                    "\n------------------------" + run1 + " attributes,  Round " + str(kround) + "--------------------"
                )

                # figure out valid attributes to use this round
                dfAttr = utils_algo.get_valid_attrs(recs0, recs1, dfAttr0, attrs1[run1], config)

                # apply principal component analysis
                if (method == "urf") and (not config["pca"]):
                    myscores = dfAttr.drop(config["non_attr_cols"], axis=1)
                else:
                    myscores, weights = utils_algo.apply_pca(dfAttr.drop(config["non_attr_cols"], axis=1))

                # myscores.to_csv("myscores_1.csv", index=False, float_format="%.3f")

                # donors and receivers for this round
                donorsAll1 = dfAttr[dfAttr["is_donor"]]["divide_id"].tolist()
                receiversAll1 = dfAttr[~dfAttr["is_donor"]]["divide_id"].tolist()

                time1 = time.time()
                if method == "gower":
                    # compute Gower's distance between donors and receivers only, i.e., avoid calculating distance
                    # between donors and donors, receivers and receivers (faster)
                    nd1 = len(donorsAll1)
                    nr1 = len(receiversAll1)
                    rng1 = myscores.max() - myscores.min()
                    rng2 = np.repeat(np.matrix(rng1), nr1, axis=0)
                    wgt2 = np.repeat(np.matrix(weights), nr1, axis=0)
                    distAttr0 = pd.DataFrame()
                    scores_receiver = myscores.iloc[nd1:]
                    distAttr0 = Parallel(n_jobs=config["njobs"])(
                        delayed(compute_gower_distance_slow)(r1, myscores, scores_receiver, rng2, wgt2, nr1)
                        for r1 in range(nd1)
                    )
                    distAttr0 = pd.concat(distAttr0, axis=1)
                    # for r1 in range(nd1):
                    #     scores_donor = np.repeat(np.matrix(myscores.iloc[r1]),nr1,axis=0)
                    #     df1 = ((scores_donor - scores_receiver).abs()/rng2*wgt2).sum(axis=1)
                    #     distAttr0 = pd.concat((distAttr0,df1),axis=1)

                elif method == "urf":
                    # compute attribute distance using unsupervised random forecast classification
                    rf1 = urf(n_trees=config["n_trees"], max_depth=config["max_depth"])
                    distAttr0 = pd.DataFrame(rf1.get_distance(myscores.to_numpy(), njob=config["njobs"]))
                    distAttr0 = distAttr0.iloc[len(donorsAll1) :, : len(donorsAll1)]

                else:
                    sys.exit("ERROR: " + method + " is not supported for distance based donor-receiver pairing")

                print(
                    "\nTime consumed for distance calculation using "
                    + method
                    + " is : --- %s seconds ---" % (time.time() - time1)
                )

                distAttr0.columns = donorsAll1
                distAttr0.index = receiversAll1
                distAttr0 = distAttr0.round(3)

                # determine which receivers to be processed for the current round
                # process only those not-yet processed receivers
                recs = [r1 for r1 in recs0 if r1 in receiversAll1 and r1 not in recs1]
                recs1 = recs1 + recs
                print(str(len(recs)) + " receivers to be processed this round")

                dfDonorAll1 = Parallel(n_jobs=config["njobs"])(
                    delayed(identify_donor_slow)(rec1, config, method, dfAttr, dfAttrAll, dist_spatial, distAttr0, run1)
                    for rec1 in recs
                )

                dfDonorAll1 = pd.concat(dfDonorAll1, axis=0)
                dfDonorAll = pd.concat((dfDonorAll, dfDonorAll1), axis=0)

    return dfDonorAll


# function for calculating Gower's distance between donors and receivers (to be used in parallel computing)
def compute_gower_distance_slow(r1, myscores, scores_receiver, rng2, wgt2, nr1):
    scores_donor = np.repeat(np.matrix(myscores.iloc[r1]), nr1, axis=0)
    df1 = ((scores_donor - scores_receiver).abs() / rng2 * wgt2).sum(axis=1)
    return df1


# function to identify donors (to be used in parallel computing)
def identify_donor_slow(rec1, config, method, dfAttr, dfAttrAll, dist_spatial, distAttr0, run1):
    dfDonor = pd.DataFrame()
    donorsAll1 = dfAttr[dfAttr["is_donor"]]["divide_id"].tolist()

    # all donors in the same snow category as the receiver
    snow1 = dfAttr["snowy"][(dfAttr["divide_id"] == rec1) & (~dfAttr["is_donor"])].squeeze()
    donors0 = dfAttr[(dfAttr["is_donor"]) & (dfAttr["snowy"] == snow1)]["divide_id"].to_list()

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
        dist1 = distAttr0.loc[rec1, donors1]
        ix1 = [x for x in dist1.index if dist1[x] <= config["max_attr_dist"]]
        if len(ix1) == 0:  # if not, continue to the next round with a larger neighbourhood
            continue

        # if a suitable donor is found (or all donors have been assessed), break the loop and stop searching
        if dist1[ix1].min() <= config["min_attr_dist"] or len(donors1) == len(donorsAll1):
            break

    # if donors are identified
    if len(donors1) > 0:
        # narrow down to those that satisfy the maxAttrDist threshold
        dist1 = dist1.loc[ix1]
        donor1 = dist1.index.tolist()

        # assign donor
        dfDonor = pd.concat(
            (dfDonor, utils_algo.assign_donors(run1, donor1, [rec1], config, dist1, dist_spatial, dfAttrAll)), axis=0
        )

    # if no donors found (after both 'main' and 'base' attribute rounds),
    # get the spatially closest donor with some constraints
    if len(donors1) == 0 and run1 == "base":
        # get all donors and their spatial distance to the receiver
        donor0 = dfAttrAll[dfAttrAll["is_donor"]]["divide_id"].tolist()
        dist0 = dist_spatial.loc[rec1,]

        # assign donor
        dfDonor = pd.concat(
            (dfDonor, utils_algo.assign_donors("proximity", donor0, [rec1], config, dist0, dist_spatial, dfAttrAll)),
            axis=0,
        )

    return dfDonor
