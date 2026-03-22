## Summary

This PR adds the minimal TaskIQ base for migration from Celery as part of Phase 1 of the TaskIQ migration plan.

## Changes

- Added TaskIQ dependencies to `backend_worker/requirements.txt`
- Created `backend_worker/taskiq_app.py` with basic broker and result backend configuration
- Created `backend_worker/taskiq_worker.py` for running TaskIQ workers
- Added TaskIQ service to `docker-compose.yml`
- Added environment variables to `.env.example`
- Created unit tests in `tests/unit/worker/test_taskiq_app.py`
- Added utility functions in `backend_worker/taskiq_utils.py`
- Created initial task modules in `backend_worker/taskiq_tasks/`
- Added feature flags in `backend_worker/feature_flags.py`

## Test Procedure

1. Run TaskIQ unit tests: `python -m pytest tests/unit/worker/test_taskiq_app.py -v` (3/3 passed)
2. Verify no regression in Celery tests: `python -m pytest tests/unit/worker/test_celery_simple.py::test_celery_app_import -v` (1/1 passed)
3. All tests complete in under 1 second each
4. No external dependencies required for unit tests

## Type of Change

- [x] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Refactor
- [ ] Documentation
- [ ] Other

## Pre-flight Checklist

- [x] Code follows PEP8 and project conventions
- [x] No sensitive data committed (.env, keys, etc.)
- [x] Tests pass for new functionality
- [x] No regression in existing functionality (Celery tests)
- [x] Documentation updated (briefing files)
- [x] Docker configuration updated
- [ ] Needs manual testing (to be done in Phase 2)

## Related Issues

N/A - This is part of the planned TaskIQ migration documented in the docs/plans/Taskiq_migrations/ directory