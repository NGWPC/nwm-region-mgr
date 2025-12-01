#!/bin/bash

set -euo pipefail


### NO_CACHE: Passed to `docker build` call. Choose from: ["--no-cache", ""]. Has mild effect on RTE build speed when using pre-built base ngen image.
NO_CACHE="--no-cache"
#NO_CACHE=""


### NGEN_SOURCE_MODE: Choose from: ["ghcr", "existing_local_tag", "build_from_local", "build_from_remote"]
# NGEN_SOURCE_MODE="ghcr" 

# Only used when ngen image source mode is "ghcr". Choose any ghcr tag, e.g. "latest" or a commit hash.
# NGEN_BASE__REMOTE_GHCR_TAG="latest"
# NGEN_BASE__REMOTE_GHCR_TAG="pr-82-build"

NGEN_SOURCE_MODE="existing_local_tag"
# Only used when ngen image source mode is "existing_local_tag". Choose any existing local image tag.
# To create the local iamge msmw:latest, follow these steps:
# 1) download docker image from s3 (aws s3 cp s3://ngwpc-dev/jeff.wade/docker/mswm.tar.gz mswm.tar.gz)
# 2) unpack (gunzip mswm.tar.gz)
# 3) load the image (docker load -i mswm.tar)
NGEN_BASE__EXISTING_LOCAL_TAG="mswm:latest"

# NGEN_SOURCE_MODE="build_from_remote"
## Only used when ngen source mode is "build_from_remote". Choose any GitHub tag (or branch name).
# NGEN_BASE__REMOTE_REPO_TAG="idt-regionalization-workflow-eval-debug"
# NGEN_BASE__REMOTE_REPO_TAG="philmiller-8862-finalize-forcings-engine"

# NGEN_SOURCE_MODE="build_from_local"


### Freeform name tag for image that is built in this process
# TARGET_IMAGE_NAME="ngen_rte:`date '+%Y%m%d%H%M%S'`-${NGEN_SOURCE_MODE}"
TARGET_IMAGE_NAME="ngen_rte"


##### Region Manager
### TODO implement this switch (currently need to edit Dockerfile.rte to switch). When implemented, will choose from ["remote", "local"]
COMPONENT__REGION_MGR__SOURCE_MODE="remote"
# COMPONENT__REGION_MGR__SOURCE_MODE="local"
### Only used when sourcing region manager from GitHub
#COMPONENT__REGION_MGR__REMOTE_REPO_TAG="mdeshotel_NGWPC-7004"
COMPONENT__REGION_MGR__REMOTE_REPO_TAG="yliu_test_old_image" 

### Logging functions
BASENAME="$(basename "$(readlink -f "$0")")"
function log_to_stderr() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%S%z')] ${BASENAME}: ${LINENO}: $*" >&2; }
function info() { log_to_stderr INFO: $*; }
function error() { log_to_stderr ERROR: $*; }
function fatal() { log_to_stderr FATAL ERROR: $*; exit 1; }
