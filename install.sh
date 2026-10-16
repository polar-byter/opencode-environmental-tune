#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$root/kit/runtime/desktop.sh" "$root/install.py" "$@"
