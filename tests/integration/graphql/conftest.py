from typing import Dict, Any, Optional

import asyncio
import pytest
from strawberry.types import ExecutionResult

from backend.api.graphql.queries.schema import schema


class TestContext:
    """Context for Strawberry execution with DB session."""
    def __init__(self, session):
        self.session = session

    @property
    def db(self):
        return self.session

    @property
    def async_db(self):
        return self.session

    def __getitem__(self, key):
        if key in {"db", "async_db", "session"}:
            return self.session
        raise KeyError(f"Key '{key}' not found")


@pytest.fixture
def graphql_context(db_session):
    """Fixture providing GraphQL context with test DB session."""
    return TestContext(db_session)


@pytest.fixture
def execute_graphql(graphql_context):
    """
    Fixture to execute GraphQL queries or mutations en mode async
    tout en conservant une API synchrone pour les tests existants.
    """
    def _execute(query: str, variables: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        return asyncio.run(
            schema.execute(
                query,
                variable_values=variables,
                context_value=graphql_context,
            )
        )

    return _execute
