#!/usr/bin/env python
import os
import sys
import asyncio
# Set the environment variable
os.environ['WORKER_DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

# Add current directory to path
sys.path.insert(0, '.')

from backend_worker.utils.logging import logger
from backend_worker.db.session import get_worker_session, _engine

logger.info('Initial _engine: %s', _engine)
session1 = get_worker_session()
logger.info('After first call, _engine: %s', _engine)
session2 = get_worker_session()
logger.info('After second call, _engine: %s', _engine)
logger.info('Sessions are same object: %s', session1 is session2)
logger.info('Engines are same: %s', session1.kw['bind'] is session2.kw['bind'])

# Test that we can actually create sessions
async_session1 = session1()
async_session2 = session2()
logger.info('Created async sessions successfully')

# Cleanup

asyncio.run(async_session1.close())
asyncio.run(async_session2.close())
logger.info('Closed sessions successfully')