#!/usr/bin/env bash
# /docker-before-entrypoint.sh


# Source original entrypoint script
. /usr/local/bin/docker-entrypoint.sh

if ! _is_sourced; then
  # Source all sh files in /docker-entrypoint-init.d/ directory
  while read -r file; do
    echo "[INFO] Source file: '$file'"

    set -e
    . "$file"
  done < <(ls /docker-entrypoint-init.d/*.sh 2>/dev/null || true)

  # Execute original entrypoint
  _main "$@"
fi