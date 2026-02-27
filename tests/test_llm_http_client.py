"""
Tests pour le client HTTPX partagé LLM.

Vérifie que le singleton fonctionne correctement et que
les connexions sont réutilisées entre les appels.
"""
import pytest
import httpx
from backend.api.services.llm_http_client import (
    get_llm_http_client,
    close_llm_http_client,
    reset_llm_http_client,
)


@pytest.mark.asyncio
async def test_llm_http_client_singleton():
    """Test que le client est bien un singleton."""
    client1 = get_llm_http_client()
    client2 = get_llm_http_client()
    
    # Même instance
    assert client1 is client2
    # Type correct
    assert isinstance(client1, httpx.AsyncClient)


@pytest.mark.asyncio
async def test_llm_http_client_configuration():
    """Test que le client est correctement configuré."""
    client = get_llm_http_client()
    
    # Vérifier les timeouts
    assert client.timeout.connect == 10.0
    assert client.timeout.read is None  # Pas de timeout de lecture
    assert client.timeout.write == 30.0
    assert client.timeout.pool == 10.0
    
    # Vérifier les limites
    assert client.limits.max_connections == 10
    assert client.limits.max_keepalive_connections == 5
    assert client.limits.keepalive_expiry == 300.0
    
    # Vérifier les headers
    assert client.headers["Connection"] == "keep-alive"


@pytest.mark.asyncio
async def test_reset_llm_http_client():
    """Test que reset crée un nouveau client."""
    client1 = get_llm_http_client()
    client2 = reset_llm_http_client()
    
    # Nouvelle instance
    assert client1 is not client2
    # L'ancien client est fermé, le nouveau est retourné par get
    assert get_llm_http_client() is client2


@pytest.mark.asyncio
async def test_close_llm_http_client():
    """Test que close ferme proprement le client."""
    client = get_llm_http_client()
    assert client is not None
    
    await close_llm_http_client()
    
    # Après fermeture, get crée un nouveau client
    new_client = get_llm_http_client()
    assert new_client is not None
    assert isinstance(new_client, httpx.AsyncClient)
    
    # Nettoyage
    await close_llm_http_client()
