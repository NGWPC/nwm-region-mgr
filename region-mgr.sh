#!/bin/bash

set -euo pipefail

OPTIND=1

docker_region=false
docker_ngen=false
docker_eval=false
docker=false
region=false
formreg=false
ngen=false
eval=false
ARGS=$(getopt -o drfneh --long docker_region,docker_ngen,docker_eval,docker,region,formreg,ngen,eval,help -- "$@")

if [ $? != 0 ] ; then echo "Failed parsing options." >&2 ; exit 1 ; fi
eval set -- "$ARGS"

while true; do
    case "$1" in
        --docker_region) docker_region=true # docker image for regionalization
            shift;;
        --docker_ngen) docker_ngen=true # docker image for ngen run
            shift;;
        --docker_eval) docker_eval=true # docker image for evaluation
            shift;;

        -d|--docker) docker=true # all three docker images
            shift;;
        -f|--formreg) formreg=true # run formulation regionalization only
            shift;;
        -r|--region) region=true # run full regionalization (formulation + parameter regionalization)
            shift;;
        -n|--ngen) ngen=true # run ngen simulation
            shift;;
        -e|--eval) eval=true # run evaluation
            shift;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]

        Options:
        --docker_region           Build Docker image for regionalization (region_rte)
        --docker_ngen             Build Docker image for ngen execution (ngen_rte)
        --docker_eval             Build Docker image for evaluation (eval_rte)
        -d,  --docker             Build all Docker images (region_rte + ngen_rte + eval_rte)

        -r,  --region             Run the regionalization workflow
        -f,  --formreg            Run formulation regionalization only
        -n,  --ngen               Run the NGEN model workflow
        -e,  --eval               Run the evaluation workflow

        -h,  --help               Show this help message and exit
        " >&2
            exit 0
            ;;
        --) shift; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
done

function docker_run {
    local mounts="-v $(pwd)/data/:/ngen-app/nwm-region-mgr/data"

    if [[ "$RTE" == "ngen_rte_new" ]]; then
        # Include ulimit before running ngen for a VPU
        time docker run --entrypoint /bin/bash \
            $mounts \
            --rm $RTE -c "ulimit -n 60000 && python $*"
    else
        # Normal Python entrypoint for other images
        time docker run --entrypoint python \
            $mounts \
            --rm $RTE "$@"
    fi
}


######### Docker Build #########
# build all three docker images
if [ "$docker" = true ]; then
    (cd docker_region && \
    ./rte_build.sh)
    (cd docker_ngen && \
    ./rte_build.sh)
    (cd docker_eval && \
    ./rte_build.sh)    
fi


# build selected docker images
if [ "$docker_region" = true ]; then
    (cd docker_region && \
    ./rte_build.sh)
fi
if [ "$docker_ngen" = true ]; then
    (cd docker_ngen && \
    ./rte_build.sh)
fi
if [ "$docker_eval" = true ]; then
    (cd docker_eval && \
    ./rte_build.sh)
fi

######### RUN Regionalization #########
if [ "$region" = true ] || [ "$formreg" = "true" ]; then
    export RTE="region_rte"
    if [ "$region" = false ] || [ "$formreg" = "true" ]; then
        mode="formreg"
    else
        mode="region"
    fi
    docker_run "/ngen-app/nwm-region-mgr/regionalization.py" \
        "/ngen-app/nwm-region-mgr/configs" ${mode}
fi


######### RUN NGEN #########
if [ "$ngen" = true ]; then
    export RTE="ngen_rte_new"
    docker_run "/ngen-app/nwm-region-mgr/run_ngen_vpu_docker.py" \
        --config_ngen "/ngen-app/nwm-region-mgr/configs/config_ngen.yaml"
fi

######### RUN EVAL #########
if [ "$eval" = true ]; then
    export RTE="eval_rte"
    docker_run -m nwm.verf \
        "/ngen-app/nwm-region-mgr/configs/config_eval.yaml" 
fi