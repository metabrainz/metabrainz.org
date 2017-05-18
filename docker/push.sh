#!/bin/bash
#
# Build image from the currently checked out version of the MetaBrainz website
# and push it to the Docker Hub, with an optional tag (by default "latest").
#
# Usage:
#   $ ./push.sh [tag]

cd "$(dirname "${BASH_SOURCE[0]}")/../"

TAG_PART=${1:-latest}
docker build -t metabrainz/metabrainz:$TAG_PART .
docker push metabrainz/metabrainz:$TAG_PART
