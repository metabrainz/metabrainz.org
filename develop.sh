#!/bin/bash

# HELP
# ./develop.sh                            build and bring up containers
# ./develop.sh manage ...                 executes the manage.py script with the given arguments in a docker container
# ./develop.sh compile-translations       compiles backend (.mo) and frontend (i18next JSON) translation catalogs
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

function run_in_service {
    local service="$1"; shift
    $DOCKER_COMPOSE_CMD -f docker/docker-compose.dev.yml -p metabrainz \
        run --rm "$service" "$@"
}

if [[ $# -eq 0 ]]; then
    invoke_docker_compose up --build
elif [[ "$1" == "manage" ]]; then shift
    echo "Running manage.py..."
    invoke_manage "$@"
elif [[ "$1" == "compile-translations" ]]; then
    echo "Compiling backend (.mo) translations..."
    run_in_service web python3 manage.py compile_translations
    echo "Compiling frontend (i18next JSON) translations..."
    run_in_service static_builder npm run build:i18n
else
    echo "Running docker-compose with the given command..."
    invoke_docker_compose "$@"
fi
