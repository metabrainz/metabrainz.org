#!/bin/bash

docker-compose -f docker/docker-compose.test.yml up --build --remove-orphans
