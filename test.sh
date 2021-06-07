#!/bin/bash

function invoke_docker_compose {
    docker-compose -f docker/docker-compose.test.yml \
        -p metabrainz_test \
        "$@"
}

invoke_docker_compose up -d db redis
invoke_docker_compose run --rm web
RET=$?
invoke_docker_compose down
exit $RET
