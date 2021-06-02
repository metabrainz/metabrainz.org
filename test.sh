#!/bin/bash
docker-compose -f docker/docker-compose.test.yml up -d --build --remove-orphans db_test redis
docker-compose -f docker/docker-compose.test.yml run --rm  web_test
RET=$?
docker-compose -f docker/docker-compose.test.yml down
exit $RET
