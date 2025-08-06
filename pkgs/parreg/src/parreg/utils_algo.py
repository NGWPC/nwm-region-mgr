"""Utils for algorithms."""

import concurrent.futures
import logging
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from pyproj import CRS
from scipy.spatial import cKDTree
from shapely.geometry import Point
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn")
logger = logging.getLogger(__name__)

# def ensure_projected(
#     gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:5070"
# ) -> gpd.GeoDataFrame:
#     """Reprojects a GeoDataFrame to a projected CRS if currently in geographic CRS."""
#     crs = CRS.from_user_input(gdf.crs)
#     if crs.is_geographic:
#         return gdf.to_crs(target_crs)
#     return gdf


def compute_pairwise_centroid_distances(
    group_a: gpd.GeoDataFrame,
    group_b: gpd.GeoDataFrame,
    id_col_a: str = "divide_id",
    id_col_b: str = "divide_id",
    id_col_a_return: str = "donor_id",
    id_col_b_return: str = "receiver_id",
    distance_threshold: float = None,
    n_jobs: int | None = None,  # Use all available cores
) -> pd.DataFrame:
    """Compute pairwise distances between centroids of two GeoDataFrames.

    Parameters
    ----------
    group_a : gpd.GeoDataFrame
        The first GeoDataFrame containing geometries and IDs.
    group_b : gpd.GeoDataFrame
        The second GeoDataFrame containing geometries and IDs.
    id_col_a : str, optional
        The name of the ID column in group_a. Default is "divide_id".
    id_col_b : str, optional
        The name of the ID column in group_b. Default is "divide_id".
    id_col_a_return : str, optional
        The name of the ID column to return from group_a. Default is "donor_id".
    id_col_b_return : str, optional
        The name of the ID column to return from group_b. Default is "receiver_id".
    distance_threshold : float, optional
        If provided, only distances less than or equal to this value will be included in the output.
    n_jobs : int, optional
        The number of jobs to run in parallel. Default is None, which uses all available cores.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the centroid distances between each pair of polygons from the two GeoDataFrames in (km),
        where the columns are indexed by polygon ids from group_a, and the rows are indexed by polygon ids from group_b.

    """
    # Precompute centroids to speed up
    centroids_a = group_a.to_crs(5070).geometry.centroid
    centroids_b = group_b.to_crs(5070).geometry.centroid

    a_ids = group_a[id_col_a].values
    b_ids = group_b[id_col_b].values

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_jobs) as executor:
        futures = {}
        data = {}
        for i in range(len(group_a)):
            futures[
                executor.submit(
                    compute_distances_for_a,
                    centroids_a.iloc[i],
                    centroids_b,
                    distance_threshold,
                )
            ] = a_ids[i]
        for future in concurrent.futures.as_completed(futures):
            data[futures[future]] = future.result()
    data = pd.DataFrame(data.values(), columns=b_ids, index=data.keys()).T
    data = data.sort_index(axis=0)
    return data.sort_index(axis=1)


def compute_distances_for_a(
    centroid_a: Point,
    centroids_b: gpd.GeoSeries,
    distance_threshold: int | float | None,
) -> list:
    """Compute distance between a point and a series of points."""
    distances = centroids_b.distance(centroid_a)

    result = []
    for dist in distances:
        if distance_threshold is None or dist <= distance_threshold:
            result.append(round(dist / 1000))  # Convert to km
        else:
            result.append(None)
    return result


def get_valid_attrs(recs0: list, recs1: list, df_attr0: pd.DataFrame, attrs: dict, config: dict) -> pd.DataFrame:
    """Get the valid attributes to be processed based on the valid attributes of the first receiver."""
    dt1 = df_attr0[~df_attr0["is_donor"]]
    dt1 = dt1[dt1.divide_id.isin(recs0) & ~dt1.divide_id.isin(recs1)].iloc[0]
    dt1 = dt1[~dt1.index.isin(config["non_attr_cols"])]
    vars = config["non_attr_cols"] + dt1.index[~dt1.isna()].tolist()
    df_attr = df_attr0[vars]
    vars = [value for value in vars if value in attrs]  # attrs included for current round
    vars0 = [value for value in attrs if value not in vars]  # attrs excluded for current round

    if len(vars) > 0:
        if len(vars0) > 0:
            logger.info("Excluding " + str(len(vars0)) + " attributes: " + ",".join(vars0))
        else:
            logger.info("Using all attributes")

    # ignore donors & receivers with NA attribute values
    df_attr = df_attr.dropna(subset=[x for x in attrs if x not in vars0], inplace=False)

    if df_attr.shape[0] == 0:
        logger.warning("No valid attributes found for the following receivers: ")

    return df_attr


def apply_pca(data0: pd.DataFrame, min_var: float = 0.8) -> pd.DataFrame:
    """Apply Principal Component Analysis to the attributes."""
    # standardize the data
    scaled_data = StandardScaler().fit_transform(data0)

    # perform PCA given the required minimum total explained variance
    pca = PCA(min_var, svd_solver="auto", random_state=7777)
    pca.fit(scaled_data)
    n1 = pca.n_components_

    logger.info(f"Number of PCs selected: {n1}")
    logger.info(f"PCA total portion of variance explained ... {sum(pca.explained_variance_ratio_)}")
    x_pca = pca.transform(scaled_data)

    # standardize the reduced data (comment out because it is not necessary)
    # x_pca = StandardScaler().fit_transform(x_pca)

    # convert to dataframe
    strs1 = ["pc"] * n1
    strs2 = list(map(str, list(range(1, n1 + 1))))
    cols = [i + j for i, j in zip(strs1, strs2)]
    x_pca = pd.DataFrame(x_pca, columns=cols)

    # weights for chosen PCs are proportional to the variances they explained
    w1 = pca.explained_variance_ratio_ / sum(pca.explained_variance_ratio_)

    # return scores and weights
    return x_pca, w1


def apply_donor_constraints(rec: str, donors: list, dists: pd.DataFrame, config: dict, df_attr: pd.DataFrame) -> tuple:
    """Apply a few additional constraints to donors identified (e.g., via Gower's distance or other techniques)."""
    # 1. narrow down to donors with the same snowiness category
    # snowy = df_attr.query("id == @rec & tag=='receiver'")['snowy']
    # snowy1 = df_attr.query("id in @donors & tag=='donor'")['snowy']
    # snowy = df_attr[df_attr["divide_id"] == rec]["snowy"].values[0]
    # snowy1 = df_attr[df_attr["divide_id"].isin(donors)]["snowy"].values
    # # ix1 = snowy1.isin(snowy)
    # ix1 = np.isin(snowy1, snowy)
    # if sum(ix1) > 0:
    #     dists = np.array(dists)[ix1]
    #     donors = np.array(donors)[ix1]

    # 1. narrow down to donors with the same snowiness category
    # get receiver's snowiness
    try:
        snowy = df_attr.loc[df_attr["divide_id"] == rec, "snowy"].values[0]
    except IndexError:
        raise ValueError(f"Receiver '{rec}' not found in attribute dataframe.")

    # Get donor snowiness in same order as donor list
    try:
        donor_index = pd.Index(donors)
        donor_rows = df_attr.set_index("divide_id").loc[donor_index]
    except KeyError as e:
        raise ValueError(f"Some donors not found in attribute dataframe: {e}")

    snowy1 = donor_rows["snowy"].values

    # Apply constraint
    ix1 = np.isin(snowy1, snowy)
    if ix1.sum() > 0:
        donors = donor_index[ix1].tolist()
        dists = np.array(dists)[ix1]

    # 2. further narrow down to those donors within maximum spatial distance defined
    ix1 = dists <= config["max_spa_dist"]
    if sum(ix1) > 0:
        dists = np.array(dists)[ix1]
        donors = np.array(donors)[ix1]

    # 3. further narrow down based on screening attributes
    # for att1 in pars['max_attr_diff'].keys():
    #     ix1 = abs(np.array(df_attr[~df_attr['is_donor']][att1]) - \
    #         np.array(df_attr[df_attr['is_donor']][att1])) \
    #             <= pars['max_attr_diff'][att1]
    #     if sum(ix1) > 0:
    #         dists = np.array(dists)[ix1]
    #         donors = np.array(donors)[ix1]

    # 4. further narrow down to donors in the same HSG
    # hsg = df_attr.query("id==@rec & tag=='receiver'")['hsg']
    # hsg1 = df_attr.query("id in @donors & tag=='donor'")['hsg']
    # ix1 = hsg1.isin(hsg)
    # if sum(ix1) > 0:
    #     dists = np.array(dists)[ix1]
    #     donors = np.array(donors)[ix1]

    return donors, dists


def assign_donors(
    scenario: str,
    donors: list,
    receivers: list,
    config: dict,
    dist_attr: pd.DataFrame,
    dist_spatial: pd.DataFrame,
    df_attr: pd.DataFrame,
    # formulation_dict: dict | None = None,
) -> pd.DataFrame:
    """Assign donors based on clusters and spatial distance and apply additional constrains."""
    df_donor = pd.DataFrame()
    for receiver in receivers:
        # get spatial distances
        dists1 = dist_spatial.loc[receiver, donors].to_numpy()
        donors1 = donors.copy()

        # # filter donors based on the receiver's formulation
        # if formulation_dict is not None:
        #     receiver_formulation = formulation_dict.get(receiver, None)
        #     donor_formulation = {k: formulation_dict[k] for k in donors1 if k in formulation_dict}
        #     if receiver_formulation:
        #         if receiver_formulation not in donor_formulation.values() and scenario == "proximity":
        #             logger.warning(
        #                 f"Pairing with proximity: receiver {receiver} has formulation {receiver_formulation}, "
        #                 "but no donors with this formulation found. Formulation will not be considered."
        #             )
        #         else:
        #             # filter donors to those with the same formulation as the receiver
        #             donors1 = [d for d in donors1 if donor_formulation.get(d) == receiver_formulation]
        #             dists1 = dists1[[donors.index(donor) for donor in donors1]]
        #     else:
        #         logger.warning(
        #             f"Receiver {receiver} has no formulation defined. Donor selection will not consider formulation."
        #         )

        # apply additional donor constraints1
        if df_attr is not None:
            donors1, dists1 = apply_donor_constraints(receiver, donors1, dists1, config, df_attr)

        # if applicable, choose donor with the smallest attribute distances
        if dist_attr is not None:
            ix0 = [donors.index(i) for i in donors1]
            dist_attr = [dist_attr.iloc[i] for i in ix0]
            ix1 = np.argsort(dist_attr)[range(min(len(dist_attr), config["n_donor_max"]))]
            dist_attr1 = np.array(dist_attr)[ix1]
            dists1 = dists1[ix1]
            donors1 = np.array(donors1)[ix1]

        # order donors by spatial distance
        ix1 = np.argsort(dists1)
        # dists1 = dists1.iloc[ix1]
        dists1 = dists1[ix1]
        donors1 = np.array(donors1)[ix1]

        # if the number of donors is greater than nDonorMax, ignore the additional donors
        nd_max = min(len(dists1), config["n_donor_max"])
        dists1 = dists1[range(nd_max)]
        donors1 = donors1[range(nd_max)]

        # if scenario == "proximity":
        #     print(f"Receiver: {receiver}, Donors: {donors1}, Distances: {dists1}")

        # add the donor/receiver pair to the pairing table
        if len(donors1) > 0:
            pair1 = {
                "divide_id": receiver,
                "tag": scenario,
                "donor": donors1[0],
                "distSpatial": dists1[0],
                "donors": ",".join(donors1),
                "distSpatials": ",".join(map(str, pd.Series(dists1))),
            }

            # add attribute distance if applicable (e.g., for Gower & URF)
            if dist_attr is not None:
                dist_attr1 = np.array(dist_attr1)[ix1]  # sort according to spatial distance
                dist_attr1 = dist_attr1[
                    range(nd_max)
                ]  # ignore unneeded donor (likely not necessary given the treatment above)
                pair1["distAttr"] = dist_attr1[0]
                pair1["distAttrs"] = ",".join(map(str, pd.Series(dist_attr1)))

            df_donor = pd.concat((df_donor, pd.DataFrame(pair1, index=[0])), axis=0)

    return df_donor


def plot_clusters(data1, labels, ndonor):
    """Plot the clusters (using the first 6 components)."""
    fig = plt.figure(figsize=(20, 14))
    cols_all = [[0, 1], [0, 2], [3, 4], [3, 5]]
    for i1, cols in enumerate(cols_all):
        if max(cols) > data1.shape[1]:
            break
        _ = fig.add_subplot(2, 2, i1 + 1)

        # receiver - noise
        d1 = labels[ndonor:] == -1
        plt.scatter(
            data1.iloc[:, cols[0]][ndonor:][d1],
            data1.iloc[:, cols[1]][ndonor:][d1],
            c="grey",
            marker=".",
        )

        # receiver non-noise
        d1 = labels[ndonor:] != -1
        plt.scatter(
            data1.iloc[:, cols[0]][ndonor:][d1],
            data1.iloc[:, cols[1]][ndonor:][d1],
            c=labels[ndonor:][d1],
            cmap="rainbow",
            marker=".",
        )
        plt.colorbar()

        # donor - noise
        d1 = labels[:ndonor] == -1
        plt.scatter(
            data1.iloc[:, cols[0]][:ndonor][d1],
            data1.iloc[:, cols[1]][:ndonor][d1],
            c="black",
            marker="x",
            s=100,
        )

        # donor non-noise
        d1 = labels[:ndonor] != -1
        plt.scatter(
            data1.iloc[:, cols[0]][:ndonor][d1],
            data1.iloc[:, cols[1]][:ndonor][d1],
            c="green",
            marker="x",
            s=100,
        )

        plt.title(
            data1.columns[cols[1]] + " vs " + data1.columns[cols[0]],
            fontsize=20,
            fontweight="bold",
        )
        plt.scatter(
            data1.iloc[:, cols[0]][:ndonor][d1],
            data1.iloc[:, cols[1]][:ndonor][d1],
            c="green",
            marker="x",
            s=100,
        )

        plt.title(
            data1.columns[cols[1]] + " vs " + data1.columns[cols[0]],
            fontsize=20,
            fontweight="bold",
        )

    plt.subplots_adjust(left=0.07, bottom=0.07, right=0.95, top=0.93, hspace=0.15, wspace=0.03)
    plt.show()


def calculate_spatial_distance(shp_file: str | Path, donors: list, receivers: list):
    """Calculate spatial distances."""
    logger.info("Compute donor-receiver spatial distance ...")

    # read in shapefile as GeoDataFrame
    shps = gpd.read_file(shp_file, layer="divides")

    # reproject from geodetic coordinates to meters (for distance calculation)
    shps = shps.to_crs(crs=3857)

    # narrow down donors and receiver GeoDataFrames to those needed
    id1 = "id"
    if "divide_id" in shps.columns:
        id1 = "divide_id"
    shps_rec = shps[shps[id1].isin(receivers)]
    shps_don = shps[shps[id1].isin(donors)]

    # reindex the GeoDataFrames by order of ids
    shps_rec = shps_rec.set_index(id1)
    shps_rec = shps_rec.reindex(receivers)

    # calculate centroids of donor and receiver catchments
    cent_don = shps_don["geometry"].centroid
    cent_rec = shps_rec["geometry"].centroid

    # convert centroids from GeoSeries to GeoDataFrame
    cent_don = gpd.GeoDataFrame(geometry=cent_don)
    cent_rec = gpd.GeoDataFrame(geometry=cent_rec)

    # calculate distance between all receiver and donor centroids
    def calculate_distances(row):
        return cent_don.distance(row.geometry)

    distances = cent_rec.apply(calculate_distances, axis=1)

    # convert to km
    distances = distances.div(1000)
    distances = distances.astype(int)

    # reset the columns and index of the distance matrix
    distances.columns = donors
    distances.index = receivers

    return distances
