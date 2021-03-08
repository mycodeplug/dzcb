#!/usr/bin/env bash

# execute all generate.sh files in subdirectories of this
# scripts directory (posix-like only)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if find --version 2>/dev/null | grep "GNU findutils" > /dev/null; then
    FIND_OPTS="-executable"
else
    FIND_OPTS="-perm +111"
fi

find $DIR \
    -name "generate.sh" \
    $FIND_OPTS -print0 | \
xargs -0 -n 1 bash
