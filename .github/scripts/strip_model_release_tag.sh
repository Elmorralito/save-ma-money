#!/usr/bin/env bash
# Strip PPT-066 / legacy model release tag prefixes → bare semver.
# Accepts: py-model-vX.Y.Z (canonical) | model-vX.Y.Z (legacy dual-trigger).
# Usage: strip_model_release_tag.sh <tag-name>
set -euo pipefail

TAG="${1:-}"
if [[ -z "${TAG}" ]]; then
  echo "usage: $0 <tag-name>" >&2
  exit 2
fi

case "${TAG}" in
  py-model-v*)
    echo "${TAG#py-model-v}"
    ;;
  model-v*)
    echo "${TAG#model-v}"
    ;;
  *)
    echo "unexpected model release tag: ${TAG}" >&2
    exit 1
    ;;
esac
