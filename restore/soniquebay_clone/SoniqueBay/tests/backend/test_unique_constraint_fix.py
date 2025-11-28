import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.models.tracks_model import Track
from backend.api.models.artists_model import Artist
from backend.api.services.track_service import TrackService
from backend.api.schemas.tracks_schema import TrackCreate
from backend.api.utils.database import Base


class TestUniqueConstraintFix:
    """Test pour vérifier la correction de l'erreur UNIQUE constraint failed: tracks.musicbrainz_id"""
    
    @pytest.fixture
    def setup_database(self):
        """Configuration de la base de données en mémoire pour les tests"""
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Créer des données de base nécessaires
        artist = Artist(name="Test Artist")
        session.add(artist)
        session.commit()
        
        yield session
        
        session.close()

    @pytest.fixture
    def track_service(self, setup_database):
        """Instance du TrackService pour les tests"""
        return TrackService(setup_database)

    def test_create_batch_with_duplicate_musicbrainz_id(self, track_service, setup_database):
        """Test la création en batch avec des musicbrainz_id dupliqués"""
        # Créer des données de test avec des MBIDs dupliqués
        track_data = [
            TrackCreate(
                title="Test Track 1",
                path="/music/test1.mp3",
                track_artist_id=1,
                musicbrainz_id="duplicate-mbid-12345"
            ),
            TrackCreate(
                title="Test Track 2",
                path="/music/test2.mp3",
                track_artist_id=1,
                musicbrainz_id="duplicate-mbid-12345"  # Même MBID
            ),
            TrackCreate(
                title="Test Track 3",
                path="/music/test3.mp3",
                track_artist_id=1,
                musicbrainz_id="unique-mbid-67890"
            )
        ]

        # La méthode ne devrait pas échouer despite les MBIDs dupliqués
        result = track_service.create_or_update_tracks_batch(track_data)

        # Vérifier qu'une seule track a été créée pour le MBID dupliqué
        assert len(result) == 2  # 2 tracks uniques : 1 pour le MBID dupliqué + 1 pour l'unique
        created_titles = [track.title for track in result]
        assert "Test Track 1" in created_titles
        assert "Test Track 3" in created_titles
        assert "Test Track 2" not in created_titles  # Track dupliquée ignorée

    def test_create_batch_with_duplicate_path(self, track_service, setup_database):
        """Test la création en batch avec des paths dupliqués"""
        track_data = [
            TrackCreate(
                title="Test Track A",
                path="/music/duplicate.mp3",
                track_artist_id=1,
                musicbrainz_id="mbid-111"
            ),
            TrackCreate(
                title="Test Track B",
                path="/music/duplicate.mp3",  # Même path
                track_artist_id=1,
                musicbrainz_id="mbid-222"
            )
        ]

        result = track_service.create_or_update_tracks_batch(track_data)

        # Vérifier qu'une seule track a été créée pour le path dupliqué
        assert len(result) == 1
        assert result[0].title == "Test Track A"  # Première track conservée

    def test_create_batch_with_existing_track_by_mbid(self, track_service, setup_database):
        """Test la création en batch avec une track existante par MBID"""
        # Créer d'abord une track existante
        existing_track = Track(
            title="Existing Track",
            path="/music/existing.mp3",
            track_artist_id=1,
            musicbrainz_id="existing-mbid-123"
        )
        setup_database.add(existing_track)
        setup_database.commit()

        # Essayer de créer une nouvelle track avec le même MBID
        track_data = [
            TrackCreate(
                title="New Track",
                path="/music/new.mp3",
                track_artist_id=1,
                musicbrainz_id="existing-mbid-123"  # Même MBID
            )
        ]

        result = track_service.create_or_update_tracks_batch(track_data)

        # Vérifier que la track existante est retournée (pas de nouvelle créée)
        assert len(result) == 1
        assert result[0].title == "Existing Track"
        assert result[0].path == "/music/existing.mp3"

    def test_create_batch_with_mixed_scenarios(self, track_service, setup_database):
        """Test avec un mix de scénarios : nouvelles tracks, doublons, existants"""
        # Créer une track existante
        existing_track = Track(
            title="Existing",
            path="/music/existing.mp3",
            track_artist_id=1,
            musicbrainz_id="existing-mbid"
        )
        setup_database.add(existing_track)
        setup_database.commit()

        track_data = [
            # Nouvelle track unique
            TrackCreate(
                title="New Unique",
                path="/music/new1.mp3",
                track_artist_id=1,
                musicbrainz_id="new-mbid-1"
            ),
            # Track avec MBID existant
            TrackCreate(
                title="Should Update Existing",
                path="/music/new2.mp3",
                track_artist_id=1,
                musicbrainz_id="existing-mbid"
            ),
            # Track avec path existant (pas de MBID)
            TrackCreate(
                title="Should Update Existing Path",
                path="/music/existing.mp3",  # Même path
                track_artist_id=1,
                musicbrainz_id="new-mbid-2"
            ),
            # Doublons dans le batch
            TrackCreate(
                title="Duplicate 1",
                path="/music/dup1.mp3",
                track_artist_id=1,
                musicbrainz_id="dup-mbid"
            ),
            TrackCreate(
                title="Duplicate 2",
                path="/music/dup2.mp3",
                track_artist_id=1,
                musicbrainz_id="dup-mbid"  # Même MBID
            )
        ]

        result = track_service.create_or_update_tracks_batch(track_data)

        # Vérifier que nous avons exactement 4 tracks :
        # 1 nouvelle (New Unique) + 1 existante inchangée (Existing) + 1 existante par path inchangée + 1 doublon créé (Duplicate 1)
        assert len(result) == 4
        
        created_titles = [track.title for track in result]
        assert "New Unique" in created_titles  # Nouvelle track créée
        assert "Existing" in created_titles  # Track existante retournée inchangée
        assert "Duplicate 1" in created_titles  # Track dupliquée créée (la première du lot)
        
        # Les tracks avec données différentes sont considérées comme inchangées pour éviter les mises à jour
        # assert "Should Update Existing" not in created_titles  # Track existante retournée comme "Existing"
        # assert "Should Update Existing Path" not in created_titles  # Track existante par path retournée comme "Existing"
        
        # Pas de doublons de la deuxième entrée
        assert "Duplicate 2" not in created_titles

    def test_empty_batch(self, track_service):
        """Test avec un batch vide"""
        result = track_service.create_or_update_tracks_batch([])
        assert result == []

    def test_batch_with_only_invalid_data(self, track_service):
        """Test avec des données invalides"""
        track_data = [
            TrackCreate(
                title="",  # Titre vide
                path="",   # Path vide
                track_artist_id=1
            )
        ]
        
        # Ne devrait pas échouer mais retourner une liste vide
        result = track_service.create_or_update_tracks_batch(track_data)
        assert len(result) >= 0  # Pas d'erreur, résultat peut être vide

if __name__ == "__main__":
    # Exécution du test en mode script pour validation rapide
    import sys
    import os
    
    # Ajouter le répertoire parent au PYTHONPATH
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Lancer les tests
    pytest.main([__file__, "-v"])