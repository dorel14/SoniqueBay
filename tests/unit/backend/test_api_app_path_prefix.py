"""Tests unitaires pour la suppression du préfixe /api dans le middleware handle_trailing_slashes.

Vérifie que removeprefix("/api") ne supprime que le préfixe /api et non
toutes les occurrences de /api dans le chemin (bug corrigé PR #38).

Auteur: SoniqueBay Team
Version: 1.0.0
"""


class TestRemovePrefixVsReplace:
    """
    Vérifie que removeprefix est utilisé à la place de replace dans api_app.py.
    Ce test protège contre une régression vers str.replace("/api", "").
    """

    def test_removeprefix_only_strips_leading_api(self):
        """removeprefix ne supprime que le préfixe, pas les occurrences internes."""
        path = "/api/artists/api-key"
        result = path.removeprefix("/api")
        assert result == "/artists/api-key", (
            "removeprefix doit conserver '/api-key' dans le segment final"
        )

    def test_replace_would_corrupt_path(self):
        """Démontre le bug de str.replace : toutes les occurrences de /api sont supprimées.

        /api/artists/api-key → str.replace("/api", "") → /artists-key
        Le segment 'api-key' perd son préfixe '/api', donnant '-key' collé à '/artists'.
        """
        path = "/api/artists/api-key"
        broken = path.replace("/api", "")
        # str.replace supprime '/api' dans '/api-key' → '-key', collé à '/artists'
        assert broken == "/artists-key", (
            "str.replace supprime TOUTES les occurrences de /api — comportement incorrect"
        )
        # Vérifier que removeprefix donne bien le résultat attendu
        correct = path.removeprefix("/api")
        assert correct == "/artists/api-key", (
            "removeprefix doit préserver '/api-key' dans le segment final"
        )

    def test_removeprefix_simple_path(self):
        """/api/tracks → /tracks (cas nominal)."""
        assert "/api/tracks".removeprefix("/api") == "/tracks"

    def test_removeprefix_no_prefix_unchanged(self):
        """Un chemin sans préfixe /api reste inchangé."""
        assert "/tracks".removeprefix("/api") == "/tracks"

    def test_removeprefix_api_in_middle_unchanged(self):
        """Un segment /api au milieu du chemin n'est pas supprimé."""
        path = "/v2/api/tracks"
        assert path.removeprefix("/api") == "/v2/api/tracks"

    def test_removeprefix_nested_api_segment(self):
        """/api/settings/api-tokens → /settings/api-tokens (segment final préservé)."""
        path = "/api/settings/api-tokens"
        assert path.removeprefix("/api") == "/settings/api-tokens"

    def test_api_app_uses_removeprefix(self):
        """Vérifie que le fichier api_app.py utilise removeprefix et non replace."""
        from pathlib import Path
        source = Path("backend/api/api_app.py").read_text(encoding="utf-8")

        assert 'removeprefix("/api")' in source, (
            "api_app.py doit utiliser removeprefix('/api') pour supprimer le préfixe"
        )
        # S'assurer que l'ancienne forme buggée n'est plus présente
        assert 'request.url.path.replace("/api", "")' not in source, (
            "api_app.py ne doit plus utiliser str.replace('/api', '') — "
            "cela supprime toutes les occurrences de /api dans le chemin"
        )
