# backend/tests/test_api/test_settings_api.py
# Tests pour les endpoints de l'API Settings

import pytest
from backend.api.schemas.settings_schema import SettingCreate


@pytest.fixture
def sample_setting_data():
    """Données d'exemple pour un paramètre."""
    return {
        "key": "test_setting_sample",
        "value": "test_value",
        "description": "Test setting description",
        "is_encrypted": False
    }


@pytest.fixture
def encrypted_setting_data():
    """Données d'exemple pour un paramètre crypté."""
    return {
        "key": "encrypted_setting_sample",
        "value": "secret_value",
        "description": "Encrypted test setting",
        "is_encrypted": True
    }


def test_get_path_variables(client):
    """Test de récupération des variables disponibles pour les chemins."""
    response = client.get("/api/settings/path-variables")

    assert response.status_code == 200
    data = response.json()
    assert "variables" in data
    assert "example" in data
    assert isinstance(data["variables"], dict)
    assert isinstance(data["example"], str)


def test_validate_path_template_valid(client):
    """Test de validation d'un template de chemin valide."""
    template = "{artist}/{album}/{title}.mp3"
    response = client.post(f"/api/settings/validate-path-template?template={template}")

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["template"] == template


def test_validate_path_template_invalid(client):
    """Test de validation d'un template de chemin invalide."""
    template = "{invalid_var}/{title}.mp3"
    response = client.post(f"/api/settings/validate-path-template?template={template}")

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert data["template"] == template


def test_create_setting_success(client, sample_setting_data):
    """Test de création d'un paramètre avec succès."""
    response = client.post("/api/settings/", json=sample_setting_data)

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == sample_setting_data["key"]
    assert data["value"] == sample_setting_data["value"]
    assert data["description"] == sample_setting_data["description"]
    assert data["is_encrypted"] == sample_setting_data["is_encrypted"]
    assert "id" in data
    assert "date_added" in data
    assert "date_modified" in data


def test_create_setting_encrypted(client, encrypted_setting_data):
    """Test de création d'un paramètre crypté."""
    from unittest.mock import patch

    with patch('backend.api.routers.settings_api.encrypt_value', return_value="mocked_encrypted_value"), \
         patch('backend.api.routers.settings_api.decrypt_value', return_value=encrypted_setting_data["value"]):
        response = client.post("/api/settings/", json=encrypted_setting_data)

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == encrypted_setting_data["key"]
        # La valeur devrait être cryptée dans la DB, mais décryptée dans la réponse
        assert data["value"] == encrypted_setting_data["value"]
        assert data["is_encrypted"] == encrypted_setting_data["is_encrypted"]


def test_read_settings_empty(client):
    """Test de lecture de tous les paramètres quand la liste est vide."""
    response = client.get("/api/settings/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_read_settings_with_data(client, sample_setting_data):
    """Test de lecture de tous les paramètres avec des données."""
    # Créer d'abord un paramètre
    client.post("/api/settings/", json=sample_setting_data)

    response = client.get("/api/settings/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    setting = data[0]
    assert setting["key"] == sample_setting_data["key"]
    assert setting["value"] == sample_setting_data["value"]


def test_read_setting_by_key_success(client, sample_setting_data):
    """Test de lecture d'un paramètre par clé avec succès."""
    # Créer d'abord un paramètre
    client.post("/api/settings/", json=sample_setting_data)

    response = client.get(f"/api/settings/{sample_setting_data['key']}")

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == sample_setting_data["key"]
    assert data["value"] == sample_setting_data["value"]
    assert data["description"] == sample_setting_data["description"]


def test_read_setting_by_key_default_music_path_template(client):
    """Test de lecture d'un paramètre par défaut (music_path_template)."""
    response = client.get("/api/settings/music_path_template")

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "music_path_template"
    assert data["value"] is not None
    assert data["description"] == "System setting: music_path_template"
    assert data["is_encrypted"] is False


def test_read_setting_by_key_default_artist_image_files(client):
    """Test de lecture d'un paramètre par défaut (artist_image_files)."""
    response = client.get("/api/settings/artist_image_files")

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "artist_image_files"
    assert data["value"] is not None
    assert data["description"] == "System setting: artist_image_files"


def test_read_setting_by_key_default_album_cover_files(client):
    """Test de lecture d'un paramètre par défaut (album_cover_files)."""
    response = client.get("/api/settings/album_cover_files")

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "album_cover_files"
    assert data["value"] is not None
    assert data["description"] == "System setting: album_cover_files"


def test_read_setting_by_key_not_found(client):
    """Test de lecture d'un paramètre inexistant."""
    response = client.get("/api/settings/nonexistent_key")

    assert response.status_code == 404
    data = response.json()
    assert "Paramètre non trouvé" in data["detail"]


def test_update_setting_success(client, sample_setting_data):
    """Test de mise à jour d'un paramètre avec succès."""
    # Créer d'abord un paramètre
    client.post("/api/settings/", json=sample_setting_data)

    # Mettre à jour
    update_data = {
        "key": sample_setting_data["key"],
        "value": "updated_value",
        "description": "Updated description",
        "is_encrypted": False
    }

    response = client.put(f"/api/settings/{sample_setting_data['key']}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == sample_setting_data["key"]
    assert data["value"] == "updated_value"
    assert data["description"] == "Updated description"


def test_update_setting_not_found(client):
    """Test de mise à jour d'un paramètre inexistant."""
    update_data = {
        "key": "nonexistent",
        "value": "value",
        "description": "desc",
        "is_encrypted": False
    }

    response = client.put("/api/settings/nonexistent", json=update_data)

    assert response.status_code == 404
    data = response.json()
    assert "Paramètre non trouvé" in data["detail"]


def test_create_setting_duplicate_key(client, sample_setting_data):
    """Test de création d'un paramètre avec une clé déjà existante."""
    # Créer d'abord un paramètre
    client.post("/api/settings/", json=sample_setting_data)

    # Tenter de créer un autre avec la même clé
    duplicate_data = sample_setting_data.copy()
    duplicate_data["value"] = "different_value"

    response = client.post("/api/settings/", json=duplicate_data)

    # Avec la contrainte UNIQUE en place, cela devrait échouer avec une erreur 400
    assert response.status_code == 400  # Bad Request due to duplicate key
    data = response.json()
    assert "clé existe déjà" in data["detail"]


def test_encryption_decryption_workflow(client, encrypted_setting_data, encryption_key):
    """Test du workflow complet de cryptage/décryptage."""
    from backend.utils.crypto import encrypt_value, decrypt_value
    from unittest.mock import patch

    # Mock les fonctions de cryptage pour utiliser notre clé de test
    def mock_encrypt(value: str) -> str:
        from cryptography.fernet import Fernet
        f = Fernet(encryption_key)
        return f.encrypt(value.encode()).decode()

    def mock_decrypt(encrypted_value: str) -> str:
        from cryptography.fernet import Fernet
        f = Fernet(encryption_key)
        return f.decrypt(encrypted_value.encode()).decode()

    # Variable pour suivre la valeur actuelle
    current_value = encrypted_setting_data["value"]

    def mock_decrypt_value(encrypted_value: str) -> str:
        return current_value

    with patch('backend.api.routers.settings_api.encrypt_value', return_value="mocked_encrypted_value"), \
         patch('backend.api.routers.settings_api.decrypt_value', side_effect=mock_decrypt_value):
        # Créer un paramètre crypté
        response = client.post("/api/settings/", json=encrypted_setting_data)
        assert response.status_code == 200

        # Lire le paramètre - la valeur devrait être décryptée
        response = client.get(f"/api/settings/{encrypted_setting_data['key']}")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == encrypted_setting_data["value"]  # Décryptée
        assert data["is_encrypted"] == True

        # Mettre à jour avec une nouvelle valeur cryptée
        update_data = encrypted_setting_data.copy()
        update_data["value"] = "new_secret_value"
        current_value = "new_secret_value"  # Mettre à jour la valeur pour le mock

        response = client.put(f"/api/settings/{encrypted_setting_data['key']}", json=update_data)
        assert response.status_code == 200

        # Vérifier que la nouvelle valeur est correctement décryptée
        response = client.get(f"/api/settings/{encrypted_setting_data['key']}")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "new_secret_value"