#!/bin/sh
set -e

# Ensure directories exist and correct ownership (useful when host bind mounts overwrite permissions)
mkdir -p /app/backend_worker/logs /app/backend_worker/data /app/data /logs
chown -R soniquebay:soniquebay /app/backend_worker/logs /app/backend_worker/data /app/data /logs || true

# If first arg looks like an option, prepend the default command
if [ "${1#-}" != "$1" ]; then
  set -- celery "$@"
fi

# If gosu is available use it to drop privileges cleanly, otherwise fallback to su
if command -v gosu >/dev/null 2>&1; then
  exec gosu soniquebay "$@"
else
  exec su -s /bin/sh soniquebay -c "exec \"$@\""
fi
