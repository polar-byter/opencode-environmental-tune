#!/bin/sh
# Invoke with sh: ZIP extraction does not preserve executable permissions.
exec sh "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/runtime/bootstrap.sh" "$@"
