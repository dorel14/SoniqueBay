"""Tests unitaires pour le module genre_yaml_loader.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from backend_worker.utils.genre_yaml_loader import (
    GenreYamlLoader,
    load_genre_yaml,
    flatten_genre_hierarchy,
    generate_genre_normalization,
    generate_compatible_groups,
    get_all_genres_flat,
    set_genre_yaml_path,
    get_genre_yaml_path,
)


# Sample YAML data for testing
SAMPLE_YAML_DATA = [
    {
        "electronic": {
            "house": ["deep house", "progressive house"],
            "techno": ["minimal techno", "detroit techno"]
        },
        "jazz": ["bebop", "swing"]
    },
    {
        "rock": {
            "alternative": ["grunge", "indie rock"],
            "classic": ["hard rock", "rock and roll"]
        }
    }
]


class TestLoadGenreYaml:
    """Tests pour la fonction load_genre_yaml."""
    
    def test_load_valid_yaml(self) -> None:
        """Test le chargement d'un fichier YAML valide."""
        yaml_content = """
- electronic:
    - house
    - techno
- jazz:
    - bebop
    - swing
"""
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = load_genre_yaml()
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_load_yaml_file_not_found(self) -> None:
        """Test le comportement quand le fichier YAML n'existe pas."""
        with patch.object(Path, 'exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                load_genre_yaml()


class TestFlattenGenreHierarchy:
    """Tests pour la fonction flatten_genre_hierarchy."""
    
    def test_flatten_simple_hierarchy(self) -> None:
        """Test l'aplatissement d'une hiérarchie simple."""
        result = flatten_genre_hierarchy(SAMPLE_YAML_DATA)
        
        # Vérifier que tous les genres sont extraits
        assert "electronic.house.deep house" in result
        assert "electronic.house.progressive house" in result
        assert "electronic.techno.minimal techno" in result
        assert "electronic.techno.detroit techno" in result
        assert "jazz.bebop" in result
        assert "jazz.swing" in result
        assert "rock.alternative.grunge" in result
        assert "rock.alternative.indie rock" in result
    
    def test_flatten_with_parents(self) -> None:
        """Test que les parents sont correctement stockés."""
        result = flatten_genre_hierarchy(SAMPLE_YAML_DATA)
        
        # Vérifier les parents
        assert "electronic" in result["electronic.house.deep house"]
        assert "house" in result["electronic.house.deep house"]
        assert "jazz" in result["jazz.bebop"]
    
    def test_flatten_empty_data(self) -> None:
        """Test avec des données vides."""
        result = flatten_genre_hierarchy([])
        assert result == {}
    
    def test_flatten_nested_hierarchy(self) -> None:
        """Test avec une hiérarchie profondément imbriquée."""
        data = [
            {
                "electronic": {
                    "house": {
                        "deep house": ["late night"]
                    }
                }
            }
        ]
        result = flatten_genre_hierarchy(data)
        
        assert "electronic.house.deep house.late night" in result
        assert "electronic" in result["electronic.house.deep house.late night"]
        assert "house" in result["electronic.house.deep house.late night"]


class TestGenerateGenreNormalization:
    """Tests pour la fonction generate_genre_normalization."""
    
    def test_generate_basic_normalization(self) -> None:
        """Test la génération de la normalisation basique."""
        genres_parents = {
            "electronic.house": ["electronic", "house"],
            "electronic.techno": ["electronic", "techno"],
            "rock": []
        }
        
        result = generate_genre_normalization(genres_parents)
        
        # Vérifier que les genres sont normalisés
        assert result["house"] == "House"
        assert result["techno"] == "Techno"
    
    def test_generate_variants(self) -> None:
        """Test la génération des variantes (underscore, hyphen)."""
        genres_parents = {
            "hip-hop": [],
            "rock_n_roll": []
        }
        
        result = generate_genre_normalization(genres_parents)
        
        # Vérifier les variantes
        assert result["hip-hop"] == "Hip-Hop"
        assert result["hip_hop"] == "Hip-Hop"
        assert result["rock_n_roll"] == "Rock_N_Roll"
    
    def test_generate_with_additional_aliases(self) -> None:
        """Test avec des aliases supplémentaires."""
        genres_parents = {
            "rock": []
        }
        additional = {
            "rocknroll": "Rock",
            "rock-and-roll": "Rock"
        }
        
        result = generate_genre_normalization(genres_parents, additional)
        
        assert result["rocknroll"] == "Rock"
        assert result["rock-and-roll"] == "Rock"


class TestGenerateCompatibleGroups:
    """Tests pour la fonction generate_compatible_groups."""
    
    def test_generate_transitive_groups(self) -> None:
        """Test la génération de groupes transitifs."""
        genres_parents = {
            "electronic.house": ["electronic", "house"],
            "electronic.techno": ["electronic", "techno"],
            "jazz.bebop": ["jazz"],
            "jazz.swing": ["jazz"]
        }
        
        result = generate_compatible_groups(genres_parents, include_transitive=True)
        
        # Vérifier que les genres du même parent sont groupés
        all_genres = set()
        for group in result:
            all_genres.update(group)
        
        # House et techno doivent être dans le même groupe (même branche electronic)
        house_group = None
        for group in result:
            if "house" in group:
                house_group = group
                break
        
        assert house_group is not None
        assert "techno" in house_group
    
    def test_generate_sibling_only_groups(self) -> None:
        """Test avec groupes limités aux siblings."""
        genres_parents = {
            "electronic.house": ["electronic", "house"],
            "electronic.techno": ["electronic", "techno"],
            "jazz": []
        }
        
        result = generate_compatible_groups(genres_parents, include_transitive=False)
        
        # Vérifier que les groupes ne contiennent que les siblings
        for group in result:
            if len(group) > 1:
                # Les genres doivent partager le même parent immédiat
                for genre in group:
                    genre_parents = genres_parents.get(f"electronic.{genre}", [])
                    assert "electronic" in genre_parents


class TestGetAllGenresFlat:
    """Tests pour la fonction get_all_genres_flat."""
    
    def test_get_flat_genres(self) -> None:
        """Test la récupération de la liste plate des genres."""
        genres_parents = {
            "electronic.house": ["electronic"],
            "electronic.techno": ["electronic"],
            "rock": []
        }
        
        result = get_all_genres_flat(genres_parents)
        
        assert "house" in result
        assert "techno" in result
        assert "rock" in result
        assert len(result) == 3
    
    def test_get_flat_genres_sorted(self) -> None:
        """Test que la liste est triée."""
        genres_parents = {
            "jazz": [],
            "electronic": [],
            "rock": []
        }
        
        result = get_all_genres_flat(genres_parents)
        
        assert result == ["electronic", "jazz", "rock"]


class TestGenreYamlLoader:
    """Tests pour la classe GenreYamlLoader."""
    
    def test_singleton_pattern(self) -> None:
        """Test que le loader utilise le pattern singleton."""
        # Reset singleton
        GenreYamlLoader._instance = None
        GenreYamlLoader._genre_data = None
        GenreYamlLoader._genres_parents = None
        GenreYamlLoader._normalization = None
        GenreYamlLoader._compatible_groups = None
        
        with patch.object(GenreYamlLoader, '_load') as mock_load:
            mock_load.side_effect = None
            loader1 = GenreYamlLoader()
            loader2 = GenreYamlLoader()
            
            assert loader1 is loader2
    
    def test_normalize_method(self) -> None:
        """Test la méthode normalize."""
        # Reset singleton
        GenreYamlLoader._instance = None
        
        with patch.object(GenreYamlLoader, '_load') as mock_load:
            mock_load.side_effect = None
            loader = GenreYamlLoader()
            
            # Configurer le mock pour la normalisation
            loader._normalization = {
                "hip-hop": "Hip-Hop",
                "rock": "Rock"
            }
            
            assert loader.normalize("HIP-HOP") == "Hip-Hop"
            assert loader.normalize("rock") == "Rock"
    
    def test_are_compatible_method(self) -> None:
        """Test la méthode are_compatible."""
        # Reset singleton
        GenreYamlLoader._instance = None
        
        with patch.object(GenreYamlLoader, '_load') as mock_load:
            mock_load.side_effect = None
            loader = GenreYamlLoader()
            
            loader._compatible_groups = [
                {"rock", "metal", "alternative"},
                {"jazz", "blues"}
            ]
            
            assert loader.are_compatible("rock", "metal") is True
            assert loader.are_compatible("jazz", "blues") is True
            assert loader.are_compatible("rock", "jazz") is False
    
    def test_get_genre_path(self) -> None:
        """Test la méthode get_genre_path."""
        # Reset singleton
        GenreYamlLoader._instance = None
        
        with patch.object(GenreYamlLoader, '_load') as mock_load:
            mock_load.side_effect = None
            loader = GenreYamlLoader()
            
            loader._genres_parents = {
                "electronic.house": ["electronic"],
                "rock.alternative": ["rock"]
            }
            
            assert loader.get_genre_path("house") == "electronic.house"
            assert loader.get_genre_path("alternative") == "rock.alternative"
            assert loader.get_genre_path("unknown") is None
    
    def test_get_parents(self) -> None:
        """Test la méthode get_parents."""
        # Reset singleton
        GenreYamlLoader._instance = None
        
        with patch.object(GenreYamlLoader, '_load') as mock_load:
            mock_load.side_effect = None
            loader = GenreYamlLoader()
            
            loader._genres_parents = {
                "electronic.house": ["electronic"]
            }
            
            assert loader.get_parents("house") == ["electronic"]


class TestGenreYamlPath:
    """Tests pour la gestion du chemin du fichier YAML."""
    
    def test_default_path(self) -> None:
        """Test le chemin par défaut."""
        # Reset global
        import backend_worker.utils.genre_yaml_loader as module
        module._GENRE_YAML_PATH = None
        
        path = get_genre_yaml_path()
        
        assert path.name == "genre-tree.yaml"
        assert path.parent.name == "utils"
    
    def test_custom_path(self) -> None:
        """Test le chemin personnalisé."""
        import backend_worker.utils.genre_yaml_loader as module
        module._GENRE_YAML_PATH = None
        
        custom_path = Path("/custom/path/genre-tree.yaml")
        set_genre_yaml_path(custom_path)
        
        assert get_genre_yaml_path() == custom_path
        
        # Cleanup
        module._GENRE_YAML_PATH = None


class TestIntegrationWithRealYaml:
    """Tests d'intégration avec le fichier YAML réel."""
    
    def setup_method(self) -> None:
        """Reset avant chaque test pour éviter les problèmes de singleton."""
        import backend_worker.utils.genre_yaml_loader as module
        module._genre_loader = None
        GenreYamlLoader._instance = None
        GenreYamlLoader._genre_data = None
        GenreYamlLoader._genres_parents = None
        GenreYamlLoader._normalization = None
        GenreYamlLoader._compatible_groups = None
    
    def test_load_real_yaml(self) -> None:
        """Test le chargement du fichier YAML réel."""
        # Ce test vérifie que le fichier YAML existant est valide
        self.setup_method()
        loader = GenreYamlLoader()
        
        # Vérifier que des données sont chargées
        assert loader.genre_data is not None
        assert len(loader.genre_data) > 0
        
        # Vérifier que des genres sont extraits
        assert len(loader.genres_parents) > 0
    
    def test_normalization_with_real_data(self) -> None:
        """Test la normalisation avec les données réelles."""
        self.setup_method()
        loader = GenreYamlLoader()
        
        # Vérifier que la normalisation fonctionne
        assert "rock" in loader.normalization
        assert "electronic" in loader.normalization
        assert "jazz" in loader.normalization
    
    def test_compatible_groups_with_real_data(self) -> None:
        """Test les groupes de compatibilité avec les données réelles."""
        self.setup_method()
        loader = GenreYamlLoader()
        
        # Vérifier que des groupes existent
        assert len(loader.compatible_groups) > 0
        
        # Vérifier que des genres sont dans des groupes
        # Grunge et alternative rock partagent le même parent "rock", donc devraient être compatibles
        grunge_in_group = False
        for group in loader.compatible_groups:
            if "grunge" in group:
                grunge_in_group = True
                # Vérifier que d'autres genres de rock sont dans le même groupe
                assert any(g in group for g in ["alternative", "indie rock", "punk"])
                break
        
        assert grunge_in_group, "Grunge should be in a compatible group with other rock subgenres"
    
    def test_all_genres_property(self) -> None:
        """Test la propriété all_genres."""
        self.setup_method()
        loader = GenreYamlLoader()
        
        # Vérifier que des genres sont retournés
        all_genres = loader.all_genres
        assert len(all_genres) > 0
        
        # Vérifier que la liste est triée
        assert all_genres == sorted(all_genres)
