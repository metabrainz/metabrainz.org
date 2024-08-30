#!/bin/bash

# HELP
# ./develop.sh                            build and bring up containers
# ./develop.sh manage ...                 executes the manage.py script with the given arguments in a docker container
# ./develop.sh ...                        passes the arguments to docker-compose command

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "Checking docker compose version"
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

function invoke_docker_compose {
    exec $DOCKER_COMPOSE_CMD -f docker/docker-compose.dev.yml \
        -p metabrainz \
        "$@"
}

function invoke_manage {
    invoke_docker_compose run --rm web \
        python3 manage.py \
        "$@"
}

if [[ $# -eq 0 ]]; then
    invoke_docker_compose up --build
elif [[ "$1" == "manage" ]]; then shift
    echo "Running manage.py..."
    invoke_manage "$@"
else
    echo "Running docker-compose with the given command..."
    invoke_docker_compose "$@"
fi
