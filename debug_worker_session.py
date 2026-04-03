#!/usr/bin/env python
import os
import sys

# Set the environment variable
os.environ['WORKER_DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

# Add current directory to path
sys.path.insert(0, '.')

from backend_worker.utils.logging import logger
import backend_worker.db.session as session_module

logger.info('Initial _engine: %s', session_module._engine)
try:
    session1 = session_module.get_worker_session()
    logger.info('After first call, _engine: %s', session_module._engine)
    logger.info('Engine created successfully: %s', session1.kw['bind'])
except Exception as e:
    logger.error('Exception during first call: %s', e)
    import traceback
    traceback.print_exc()

try:
    session2 = session_module.get_worker_session()
    logger.info('After second call, _engine: %s', session_module._engine)
    logger.info('Engine created successfully: %s', session2.kw['bind'])
except Exception as e:
    logger.error('Exception during second call: %s', e)
    import traceback
    traceback.print_exc()

logger.info('Sessions are same object: %s', session1 is session2)
logger.info('Engines are same: %s', session1.kw['bind'] is session2.kw['bind'])