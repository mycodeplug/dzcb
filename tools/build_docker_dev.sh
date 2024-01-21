#!/bin/bash
set -e -o pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker buildx build --progress=plain -t dzcb:dev -f Dockerfile.dev .
