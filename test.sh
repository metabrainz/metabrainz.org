#!/bin/bash

function invoke_docker_compose {
    docker compose -f docker/docker-compose.test.yml \
        -p metabrainz_test \
        "$@"
}

invoke_docker_compose up -d db redis
invoke_docker_compose build web
invoke_docker_compose run --rm web \
    dockerize -wait tcp://db:5432 -timeout 60s \
    bash -c "python manage.py init-db --create-db && pytest --junitxml=reports/tests.xml"
RET=$?
invoke_docker_compose down
exit $RET
