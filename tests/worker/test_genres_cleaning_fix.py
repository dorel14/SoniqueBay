"""
Test pour valider la correction du nettoyage des genres complexes.
"""
from backend_worker.background_tasks.worker_metadata import _clean_and_split_genres


def test_clean_and_split_genres():
    """Test du nettoyage et découpage des genres complexes."""
    
    # Test cas complexe du log d'erreur
    complex_genre = "Dance, Soul, American, Interlude, Jacksons, New Soul - Hip Hop - Rap, Jam And Lewis, Pop, 00S, Rnb, Female Vocalist"
    cleaned = _clean_and_split_genres(complex_genre)
    
    print(f"Genre original: {complex_genre}")
    print(f"Genres nettoyés: {cleaned}")
    
    # Vérifications
    assert len(cleaned) > 0, "Devrait retourner au moins un genre"
    assert "Dance" in cleaned, "Devrait contenir 'Dance'"
    assert "Soul" in cleaned, "Devrait contenir 'Soul'"
    assert "New Soul Hip Hop Rap" in cleaned, "Devrait contenir 'New Soul Hip Hop Rap'"
    assert "Pop" in cleaned, "Devrait contenir 'Pop'"
    assert "00S" not in cleaned, "Ne devrait PAS contenir '00S' (code année)"
    
    # Vérifier que les genres sont nettoyés
    for genre in cleaned:
        assert len(genre) <= 50, f"Genre trop long: {genre}"
        assert not genre.isdigit(), f"Genre ne devrait pas être numérique: {genre}"
        
    print(f"✅ Test réussi: {len(cleaned)} genres extraits et nettoyés")


def test_clean_single_genre():
    """Test avec un genre simple."""
    
    simple_genre = "Rock"
    cleaned = _clean_and_split_genres(simple_genre)
    
    assert cleaned == ["Rock"], f"Attendu ['Rock'], obtenu {cleaned}"
    print(f"✅ Genre simple: '{simple_genre}' → {cleaned}")


def test_clean_genre_with_special_chars():
    """Test avec des caractères spéciaux."""
    
    special_genre = "Hip-Hop/R&B"
    cleaned = _clean_and_split_genres(special_genre)
    
    print(f"Genre avec caractères spéciaux: '{special_genre}' → {cleaned}")
    
    # Devrait être nettoyé en "Hip Hop R&B" ou "Hip Hop R and B"
    assert len(cleaned) > 0, "Devrait traiter les caractères spéciaux"
    
    print(f"✅ Caractères spéciaux traités: {cleaned}")


def test_clean_empty_and_invalid():
    """Test avec des valeurs vides ou invalides."""
    
    assert _clean_and_split_genres("") == [], "Devrait retourner une liste vide pour chaîne vide"
    assert _clean_and_split_genres(None) == [], "Devrait retourner une liste vide pour None"
    assert _clean_and_split_genres("   ") == [], "Devrait retourner une liste vide pour espaces uniquement"
    assert _clean_and_split_genres("00S") == [], "Devrait ignorer les codes années seuls"
    assert _clean_and_split_genres("123") == [], "Devrait ignorer les nombres seuls"
    
    print("✅ Valeurs vides/invalides traitées correctement")


if __name__ == "__main__":
    test_clean_and_split_genres()
    test_clean_single_genre()
    test_clean_genre_with_special_chars()
    test_clean_empty_and_invalid()
    print("\n🎉 Tous les tests de nettoyage des genres ont réussi!")