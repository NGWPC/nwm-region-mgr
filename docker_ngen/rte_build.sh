#!/bin/bash
# 
# rte_build.sh
# 
# This script builds the ngen_rte image for setting up the NGEN runtime environment. 
# It includes, mswm, ngen, and ngen-forcing components, as well as 
#    run_ngen_vpu_docker.py and configs/config_ngen.yaml from nwm-region-mgr.
# 
# See config.bashrc for configuration. Components can be installed from GitHub or from local source code.
# 
# Input data required (s3://ngwpc-dev/regionalization/data/inputs/) can be downloaded or mounted at runtime.

set -euo pipefail
set -x

source config.bashrc

TIMESTAMP=`date '+%Y%m%d%H%M%S'`

### Build ngen base image if specified, otherwise just set var to ghcr URL
if [[ $NGEN_SOURCE_MODE == "ghcr" ]]; then
    NGEN_BASE_IMAGE="ghcr.io/ngwpc/ngen:${NGEN_BASE__REMOTE_GHCR_TAG}"

elif [[ $NGEN_SOURCE_MODE == "existing_local_tag" ]]; then
    NGEN_BASE_IMAGE="${NGEN_BASE__EXISTING_LOCAL_TAG}"

elif [[ $NGEN_SOURCE_MODE == "build_from_local" ]]; then
    NGEN_BASE_IMAGE="ngen:${NGEN_SOURCE_MODE}"
    NGEN_SOURCE_LOCAL="${HOME}/repos/ngen"
    # NGEN_SOURCE_LOCAL="${HOME}/ngwpc/ngen"
    ( cd ${NGEN_SOURCE_LOCAL} && sudo docker build -t ${NGEN_BASE_IMAGE} . )

elif [[ $NGEN_SOURCE_MODE == "build_from_remote" ]]; then
    NGEN_BASE_IMAGE="ngen:${NGEN_SOURCE_MODE}"
    NGEN_SOURCE_LOCAL="${HOME}/ngwpc/ngen_tmp"
    NGEN_GIT_URL="https://github.com/NGWPC/ngen.git"
    if test -d ${NGEN_SOURCE_LOCAL}; then
        info "Pulling branch ${NGEN_BASE__REMOTE_REPO_TAG} and submodules from ${NGEN_SOURCE_LOCAL}"
        ( \
            cd ${NGEN_SOURCE_LOCAL} && \
            git fetch && \
            git checkout ${NGEN_BASE__REMOTE_REPO_TAG} && \
            git pull --recurse-submodules && \
            git submodule update --init --recursive \
        )
    else
        info "Cloning branch ${NGEN_BASE__REMOTE_REPO_TAG} from ${NGEN_GIT_URL}"
        git clone --branch ${NGEN_BASE__REMOTE_REPO_TAG} --recurse-submodules "${NGEN_GIT_URL}" "${NGEN_SOURCE_LOCAL}"
    fi
    ( cd ${NGEN_SOURCE_LOCAL} && sudo docker build -t ${NGEN_BASE_IMAGE} . )

else
    fatal "Not implemented: NGEN_SOURCE_MODE=${NGEN_SOURCE_MODE}"
fi
# exit 0

### Build RTE image from ngen base image
info "Building image: ${TARGET_IMAGE_NAME}"
sudo docker build -t ${TARGET_IMAGE_NAME} -f Dockerfile.rte ${NO_CACHE} \
    --build-arg NGEN_BASE_IMAGE=${NGEN_BASE_IMAGE} \
    --build-arg REPO_TAG__REGION_MGR="${COMPONENT__REGION_MGR__REMOTE_REPO_TAG}" \
    ".." \
    |& tee "docker_logs/build/${TARGET_IMAGE_NAME}-${TIMESTAMP}.log"

info "Built image: ${TARGET_IMAGE_NAME}"
info "Command to start and enter container without executing anything: sudo docker run --entrypoint /bin/bash -it --rm ${TARGET_IMAGE_NAME}"
# exit 0


    # time sudo docker run --entrypoint /bin/sh -it \
function docker_run {
    time sudo docker run --entrypoint python \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER_1}" \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER_2}" \
        -v "${MNT__NGEN_FORCING__HOST}:${MNT__NGEN_FORCING__CONTAINER_1}" \
        -v "${MNT__NGEN_FORCING__HOST}:${MNT__NGEN_FORCING__CONTAINER_2}" \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER_1}" \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER_2}" \
        -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1}" \
        -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2}" \
        -v "${HOME}/ngwpc/ngen/data":"/ngen-app/data" \
        -v "${HOME}/ngwpc/run_ngen/data/geo_em_CONUS.nc:/ngen-app/data/esmf_mesh/NWM/domain/geo_em_CONUS.nc" \
        -v "$(pwd)/docker_logs/run:/ngencerf/data/run-logs" \
        -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        -v "${MNT_REGION_MGR_INPUT_DATA_HOST}:${MNT_REGION_MGR_INPUT_DATA_CONTAINER_1}" \
        -v "${MNT_REGION_MGR_INPUT_DATA_HOST}:${MNT_REGION_MGR_INPUT_DATA_CONTAINER_2}" \
        -v "${MNT_REGION_MGR_CONFIGS_HOST}:${MNT_REGION_MGR_CONFIGS_CONTAINER_1}" \
        -v "${MNT_REGION_MGR_CONFIGS_HOST}:${MNT_REGION_MGR_CONFIGS_CONTAINER_2}" \
        \
        --rm ${TARGET_IMAGE_NAME}
}


# docker_run "/ngen-app/bin/bin_mounted/example_workflow.py"
# docker_run

exit 0

##### These mounts might be needed in some branches
        # -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1}" \
        # -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2}" \
