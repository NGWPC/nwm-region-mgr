#!/bin/bash
# 
# rte_build.sh
# 
# This script builds the EVAL image for evaluating NGEN simulation outputs. 
# It includes nwm-eval-mgr and nwm-verf components, as well as configs/config_eval.yaml from nwm-region-mgr.
# 
# See config.bashrc for configuration. Components can be installed from GitHub or from local source code.
# 
# Input data required (s3://ngwpc-dev/regionalization/data/inputs/) can be downloaded or mounted at runtime.

set -euo pipefail
set -x

source config.bashrc

TIMESTAMP=`date '+%Y%m%d%H%M%S'`

info "Building image: ${TARGET_IMAGE_NAME}"
sudo docker build -t ${TARGET_IMAGE_NAME} -f Dockerfile.rte ${NO_CACHE} \
    --build-arg REPO_TAG__REGION_MGR="${COMPONENT__REGION_MGR__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__EVAL_MGR="${COMPONENT__EVAL_MGR__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__VERF_MGR="${COMPONENT__VERF_MGR__REMOTE_REPO_TAG}" \
    ".." \
    |& tee "docker_logs/build/${TARGET_IMAGE_NAME}-${TIMESTAMP}.log"

info "Built image: ${TARGET_IMAGE_NAME}"
info "Command to start and enter container without executing anything: sudo docker run --entrypoint /bin/bash -it --rm ${TARGET_IMAGE_NAME}"
# exit 0


# docker_run "/ngen-app/bin/bin_mounted/example_workflow.py"
# docker_run

exit 0

##### These mounts might be needed in some branches
        # -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1}" \
        # -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2}" \
