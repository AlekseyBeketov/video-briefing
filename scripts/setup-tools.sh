#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

BUN_VERSION=1.4.2

npm install --prefix .tools/bun --no-save --no-audit --no-fund "bun@${BUN_VERSION}"

"$ROOT/.tools/bun/node_modules/.bin/bun" --version
