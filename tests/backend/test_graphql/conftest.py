from typing import Dict, Any

import pytest
from strawberry.types import ExecutionResult

from backend.library_api.api.graphql.queries.schema import schema


class TestContext:
    """Context for Strawberry execution with DB session."""
    def __init__(self, session):
        self.session = session

    @property
    def db(self):
        return self.session

    def __getitem__(self, key):
        if key == "db":
            return self.session
        raise KeyError(f"Key '{key}' not found")


@pytest.fixture
def graphql_context(db_session):
    """Fixture providing GraphQL context with test DB session."""
    return TestContext(db_session)


@pytest.fixture
def execute_graphql(graphql_context):
    """
    Fixture to execute GraphQL queries or mutations synchronously.
    
    Args:
        query: GraphQL query or mutation string.
        variables: Optional dictionary of variables.
    
    Returns:
        ExecutionResult from Strawberry.
    """
    def _execute(query: str, variables: Dict[str, Any] = None) -> ExecutionResult:
        return schema.execute_sync(
            query,
            variable_values=variables,
            context_value=graphql_context
        )
    return _execute