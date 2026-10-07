#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

BUN_VERSION=1.4.2
SUMMARIZE_VERSION=0.25.1
SUMMARIZE_ARCHIVE="summarize-macos-arm64-v${SUMMARIZE_VERSION}.tar.gz"
SUMMARIZE_SHA256=6d361feb48e77accb20ae0cd9eb1ae1e69298e26079200e57a98df7e6e720571

mkdir -p .tools/summarize
npm install --prefix .tools/bun --no-save --no-audit --no-fund "bun@${BUN_VERSION}"

curl -fsSL "https://github.com/steipete/summarize/releases/download/v${SUMMARIZE_VERSION}/SHA256SUMS" \
  -o .tools/summarize/SHA256SUMS
curl -fL --retry 2 \
  "https://github.com/steipete/summarize/releases/download/v${SUMMARIZE_VERSION}/${SUMMARIZE_ARCHIVE}" \
  -o ".tools/summarize/${SUMMARIZE_ARCHIVE}"
printf '%s  %s\n' "$SUMMARIZE_SHA256" ".tools/summarize/${SUMMARIZE_ARCHIVE}" | shasum -a 256 -c -
tar -xzf ".tools/summarize/${SUMMARIZE_ARCHIVE}" -C .tools/summarize

"$ROOT/.tools/bun/node_modules/.bin/bun" --version
"$ROOT/.tools/summarize/summarize" --version
