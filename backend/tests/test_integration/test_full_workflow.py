# backend/tests/test_integration/test_full_workflow.py

def test_full_music_workflow(client, db_session):
    """Test d'intégration: flux de travail complet de gestion de musique."""
    # 1. Créer un artiste
    artist_data = {"name": "Workflow Test Artist"}
    artist_response = client.post("/api/artists/", json=artist_data)
    assert artist_response.status_code == 200
    artist_id = artist_response.json()["id"]

    # 2. Créer un album pour cet artiste
    album_data = {
        "title": "Workflow Test Album",
        "artist_id": artist_id,
        "year": "2023"
    }
    album_response = client.post("/api/albums/", json=album_data)
    assert album_response.status_code == 200
    album_id = album_response.json()["id"]

    # 3. Créer plusieurs pistes pour cet album
    tracks_data = [
        {
            "title": "Workflow Track 1",
            "path": "/path/to/workflow1.mp3",
            "track_artist_id": artist_id,
            "album_id": album_id,
            "track_number": "1",
            "duration": 180
        },
        {
            "title": "Workflow Track 2",
            "path": "/path/to/workflow2.mp3",
            "track_artist_id": artist_id,
            "album_id": album_id,
            "track_number": "2",
            "duration": 210
        },
        {
            "title": "Workflow Track 3",
            "path": "/path/to/workflow3.mp3",
            "track_artist_id": artist_id,
            "album_id": album_id,
            "track_number": "3",
            "duration": 240
        }
    ]

    track_ids = []
    for track_data in tracks_data:
        track_response = client.post("/api/tracks/", json=track_data)
        assert track_response.status_code == 200
        track_ids.append(track_response.json()["id"])

    # 4. Récupérer les pistes de l'album
    album_tracks_response = client.get(f"/api/tracks/artists/{artist_id}/albums/{album_id}")
    assert album_tracks_response.status_code == 200
    album_tracks = album_tracks_response.json()
    assert len(album_tracks) == 3

    # 5. Mettre à jour une piste
    update_data = {
        "title": "Updated Workflow Track",
        "genre": "Rock",
        "genre_tags": ["rock", "indie"]
    }
    update_response = client.put(f"/api/tracks/{track_ids[0]}", json=update_data)
    assert update_response.status_code == 200
    updated_track = update_response.json()
    assert updated_track["title"] == "Updated Workflow Track"
    assert updated_track["genre"] == "Rock"
    assert "rock" in updated_track["genre_tags"]

    # 6. Rechercher des pistes par genre
    search_response = client.get("/api/tracks/search?genre=Rock")
    assert search_response.status_code == 200
    search_results = search_response.json()
    assert len(search_results) > 0
    assert any(track["id"] == track_ids[0] for track in search_results)

    # 7. Supprimer une piste
    delete_response = client.delete(f"/api/tracks/{track_ids[2]}")
    assert delete_response.status_code == 204

    # Vérifier que la piste a bien été supprimée
    get_response = client.get(f"/api/tracks/{track_ids[2]}")
    assert get_response.status_code == 404

    # 8. Vérifier que l'album n'a plus que 2 pistes
    album_tracks_response = client.get(f"/api/tracks/artists/{artist_id}/albums/{album_id}")
    assert album_tracks_response.status_code == 200
    album_tracks = album_tracks_response.json()
    assert len(album_tracks) == 2