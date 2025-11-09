"""
Test pour valider la correction de la fonction validate_release_year.
"""
import pytest
from backend.library_api.api.schemas.albums_schema import AlbumBase


@pytest.mark.asyncio
async def test_validate_release_year_various_formats():
    """
    Test que la fonction validate_release_year gère correctement
    tous les formats de dates mentionnés.
    """
    # Test des formats de dates complets
    test_cases = [
        # Dates complètes (format YYYY-MM-DD)
        ("2014-08-05", "2014"),
        ("2024-02-09", "2024"),
        ("2023/12/25", "2023"),
        ("2020-01-15", "2020"),
        
        # Format dd/mm/yyyy
        ("15/08/2014", "2014"),
        ("25/12/2023", "2023"),
        ("01/01/2020", "2020"),
        
        # Format dd/mm/yy (conversion vers 4 chiffres)
        ("15/08/14", "2014"),  # 14 -> 2014
        ("25/12/95", "1995"),  # 95 -> 1995
        ("01/01/05", "2005"),  # 05 -> 2005
        ("01/01/99", "1999"),  # 99 -> 1999
        
        # Années simples
        ("2014", "2014"),
        ("2024", "2024"),
        ("1995", "1995"),
        ("05", "2005"),  # Année courte
        ("95", "1995"),  # Année courte
        
        # Cas spéciaux avec entiers
        (2014, "2014"),
        (2024, "2024"),
        (1995, "1995"),
        
        # Valeurs None
        (None, None),
        
        # Valeurs vides/espaces
        ("", None),
        ("   ", None),
    ]
    
    validator = AlbumBase.validate_release_year
    
    for input_value, expected_output in test_cases:
        result = validator(input_value)
        assert result == expected_output, \
            f"Échec pour input '{input_value}' ({type(input_value).__name__}): " \
            f"attendu '{expected_output}', obtenu '{result}'"
        
        print(f"✅ '{input_value}' → '{result}'")


@pytest.mark.asyncio
async def test_validate_release_year_error_cases():
    """
    Test que la fonction gère correctement les cas d'erreur.
    """
    validator = AlbumBase.validate_release_year
    
    # Cas d'erreur
    error_cases = [
        "abc",  # Texte non numérique
        "2014-13-01",  # Mois invalide
        "13/25/2014",  # Jour/mois invalides
        "invalid-date",  # Format complètement invalide
    ]
    
    for error_input in error_cases:
        result = validator(error_input)
        assert result is None, \
            f"Échec attendu pour input '{error_input}', mais obtenu '{result}'"
        
        print(f"⚠️  '{error_input}' → None (erreur gérée)")


@pytest.mark.asyncio
async def test_real_world_scenarios():
    """
    Test avec les cas réels des logs d'erreur.
    """
    validator = AlbumBase.validate_release_year
    
    # Cas exacts des logs d'erreur
    real_cases = [
        ("2014-08-05", "2014"),  # Du log
        ("2024-02-09", "2024"),  # Du log
    ]
    
    for input_value, expected_output in real_cases:
        result = validator(input_value)
        assert result == expected_output, \
            f"Échec pour cas réel '{input_value}': attendu '{expected_output}', obtenu '{result}'"
        
        print(f"✅ Cas réel '{input_value}' → '{result}'")


if __name__ == "__main__":
    import asyncio
    
    print("🧪 Test validation release_year...")
    asyncio.run(test_validate_release_year_various_formats())
    asyncio.run(test_validate_release_year_error_cases())
    asyncio.run(test_real_world_scenarios())
    print("✅ Tous les tests de validation release_year ont réussi!")