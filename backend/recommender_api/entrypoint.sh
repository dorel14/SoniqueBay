#!/bin/sh
set -e

# Ensure directories exist and correct ownership (useful when host bind mounts overwrite permissions)
mkdir -p /logs /app/backend/recommender_api/data /app/data
chown -R soniquebay:soniquebay /logs /app/backend/recommender_api/data /app/data || true

# If first arg looks like an option, prepend the default command
if [ "${1#-}" != "$1" ]; then
  set -- python3 -m uvicorn "$@"
fi

# If gosu is available use it to drop privileges cleanly, otherwise fallback to su
if command -v gosu >/dev/null 2>&1; then
  exec gosu soniquebay "$@"
else
  exec su -s /bin/sh soniquebay -c "exec \"$@\""
fi
