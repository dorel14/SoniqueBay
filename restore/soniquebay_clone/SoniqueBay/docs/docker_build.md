# Docker build guide

This document shows recommended commands to build and test images locally and how to use buildx cache.

Build the base image (one-time):

```powershell
docker buildx build --progress=plain -f Dockerfile.base -t soniquebay/base:optim .
```

Build a service image using the base (example: recommender):

```powershell
docker buildx build --progress=plain -f backend/recommender_api/Dockerfile -t soniquebay/recommender:optim .
```

Tips:
- Use `--load` to load the built image into the local Docker engine when using buildx.
- Use cache-from/cache-to with a registry to speed up CI builds.
- Ensure `.dockerignore` excludes large folders (data, logs, .venv, node_modules) to reduce build context.

Example: build with cache and load locally:

```powershell
docker buildx build --progress=plain --cache-from=type=local,src=/tmp/.buildcache --cache-to=type=local,dest=/tmp/.buildcache-new --load -f Dockerfile.base -t soniquebay/base:optim .
```

Healthcheck and smoke tests:
- After building, run a container and run `python3 -c "import fastapi, uvicorn"` or the healthcheck script to ensure dependencies are present.

If you want, I can run these builds for the remaining Dockerfiles now and report the times and sizes.
