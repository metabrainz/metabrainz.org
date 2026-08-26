#!/bin/bash

echo "Checking docker compose version"
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

function invoke_docker_compose {
    $DOCKER_COMPOSE_CMD -f docker/docker-compose.test.yml \
        -p metabrainz_test \
        "$@"
}

invoke_docker_compose up -d meb_db redis
invoke_docker_compose build web
# "$@" must be passed as separate argv entries: interpolating it into the bash -c
# string makes bash split it, so only the first argument reaches pytest and the
# rest are silently swallowed as the inner shell's $0/$1/...
invoke_docker_compose run --rm web \
    dockerize -wait tcp://meb_db:5432 -timeout 60s \
    bash -c 'python manage.py init-db --create-db && pytest --junitxml=reports/tests.xml "$@"' _ "$@"
RET=$?
invoke_docker_compose down
exit $RET
