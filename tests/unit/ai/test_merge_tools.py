"""Tests unitaires pour la fonction _merge_tools de backend/ai/agents/builder.py.

Vérifie que la fusion des tools parent/enfant est robuste même lorsque
le nom enregistré dans ToolRegistry diffère du __name__ de la fonction.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from types import SimpleNamespace

import pytest

from backend.ai.agents.builder import _merge_tools
from backend.ai.utils.registry import AIToolMetadata, ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_func(func_name: str):
    """Crée une fonction factice avec un __name__ contrôlé."""
    def _fn():
        pass
    _fn.__name__ = func_name
    return _fn


def _make_metadata(registered_name: str, func_name: str) -> AIToolMetadata:
    """Crée un AIToolMetadata avec registered_name != func.__name__."""
    func = _make_func(func_name)
    return AIToolMetadata(
        name=registered_name,
        description=f"Tool {registered_name}",
        func=func,
    )


def _make_agent_model(tools: list) -> SimpleNamespace:
    return SimpleNamespace(tools=tools)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registry():
    """Isole chaque test en sauvegardant/restaurant le registre."""
    original = ToolRegistry._tools.copy()
    yield
    ToolRegistry._tools = original


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMergeToolsBasic:
    """Cas de base : noms enregistrés == __name__ des fonctions."""

    def test_no_overlap_returns_all_tools(self):
        """Parent et enfant ont des tools distincts → tous conservés."""
        meta_a = _make_metadata("tool_a", "tool_a")
        meta_b = _make_metadata("tool_b", "tool_b")
        ToolRegistry._tools["tool_a"] = meta_a
        ToolRegistry._tools["tool_b"] = meta_b

        parent = _make_agent_model(["tool_a"])
        child = _make_agent_model(["tool_b"])

        result = _merge_tools(child, parent)

        assert len(result) == 2
        assert meta_a.func in result
        assert meta_b.func in result

    def test_child_replaces_parent_tool_with_same_name(self):
        """Enfant remplace le tool parent portant le même nom enregistré."""
        meta_parent = _make_metadata("shared_tool", "shared_tool_parent_fn")
        meta_child = _make_metadata("shared_tool", "shared_tool_child_fn")
        ToolRegistry._tools["shared_tool"] = meta_parent  # parent voit cette version
        parent = _make_agent_model(["shared_tool"])

        # L'enfant enregistre une version différente du même nom
        ToolRegistry._tools["shared_tool"] = meta_child
        child = _make_agent_model(["shared_tool"])

        result = _merge_tools(child, parent)

        # Seule la version enfant doit être présente
        assert len(result) == 1
        assert meta_child.func in result
        assert meta_parent.func not in result

    def test_empty_child_tools_keeps_all_parent_tools(self):
        """Enfant sans tools → tous les tools parents conservés."""
        meta_a = _make_metadata("tool_a", "tool_a")
        ToolRegistry._tools["tool_a"] = meta_a

        parent = _make_agent_model(["tool_a"])
        child = _make_agent_model([])

        result = _merge_tools(child, parent)

        assert len(result) == 1
        assert meta_a.func in result

    def test_empty_parent_tools_returns_only_child_tools(self):
        """Parent sans tools → seuls les tools enfants retournés."""
        meta_b = _make_metadata("tool_b", "tool_b")
        ToolRegistry._tools["tool_b"] = meta_b

        parent = _make_agent_model([])
        child = _make_agent_model(["tool_b"])

        result = _merge_tools(child, parent)

        assert len(result) == 1
        assert meta_b.func in result


class TestMergeToolsRegisteredNameDiffersFromFuncName:
    """
    Cas critique : le nom enregistré dans ToolRegistry diffère du __name__
    de la fonction. C'est le bug corrigé dans la PR #38.
    """

    def test_parent_tool_removed_when_registered_name_differs_from_func_name(self):
        """
        Scénario : tool parent enregistré sous 'search_music' mais la fonction
        s'appelle 'do_search'. L'enfant enregistre aussi 'search_music'.
        → Le tool parent doit être supprimé (pas de doublon).
        """
        # Parent : registered_name='search_music', func.__name__='do_search'
        meta_parent = _make_metadata("search_music", "do_search")
        ToolRegistry._tools["search_music"] = meta_parent
        parent = _make_agent_model(["search_music"])

        # Enfant : registered_name='search_music', func.__name__='search_music_v2'
        meta_child = _make_metadata("search_music", "search_music_v2")
        ToolRegistry._tools["search_music"] = meta_child
        child = _make_agent_model(["search_music"])

        result = _merge_tools(child, parent)

        # Seule la version enfant doit être présente — pas de doublon
        assert len(result) == 1, (
            "Le tool parent doit être supprimé même si func.__name__ != registered_name"
        )
        assert meta_child.func in result
        assert meta_parent.func not in result

    def test_no_attribute_error_when_func_name_not_in_registry(self):
        """
        Régression : l'ancienne implémentation faisait
        ToolRegistry.get(tool.__name__).name ce qui levait AttributeError
        si tool.__name__ n'était pas une clé du registre.
        """
        # Parent : registered_name='play_track', func.__name__='_internal_play'
        # '_internal_play' n'est PAS une clé du registre
        meta_parent = _make_metadata("play_track", "_internal_play")
        ToolRegistry._tools["play_track"] = meta_parent
        parent = _make_agent_model(["play_track"])

        # Enfant : tool différent, pas de conflit
        meta_child = _make_metadata("queue_track", "queue_track")
        ToolRegistry._tools["queue_track"] = meta_child
        child = _make_agent_model(["queue_track"])

        # Ne doit pas lever AttributeError
        result = _merge_tools(child, parent)

        assert len(result) == 2
        assert meta_parent.func in result
        assert meta_child.func in result

    def test_multiple_parent_tools_partial_override(self):
        """
        Parent a 3 tools, enfant en remplace 1 (avec registered_name != func.__name__).
        → 2 tools parents + 1 tool enfant = 3 au total.
        """
        meta_p1 = _make_metadata("tool_alpha", "_fn_alpha")
        meta_p2 = _make_metadata("tool_beta", "_fn_beta")
        meta_p3 = _make_metadata("tool_gamma", "_fn_gamma")
        ToolRegistry._tools["tool_alpha"] = meta_p1
        ToolRegistry._tools["tool_beta"] = meta_p2
        ToolRegistry._tools["tool_gamma"] = meta_p3
        parent = _make_agent_model(["tool_alpha", "tool_beta", "tool_gamma"])

        # Enfant remplace tool_beta
        meta_c_beta = _make_metadata("tool_beta", "_fn_beta_v2")
        ToolRegistry._tools["tool_beta"] = meta_c_beta
        child = _make_agent_model(["tool_beta"])

        result = _merge_tools(child, parent)

        assert len(result) == 3
        assert meta_p1.func in result       # tool_alpha conservé
        assert meta_p2.func not in result   # tool_beta parent supprimé
        assert meta_c_beta.func in result   # tool_beta enfant ajouté
        assert meta_p3.func in result       # tool_gamma conservé

    def test_unknown_tool_name_in_model_is_silently_ignored(self):
        """
        Un nom de tool inconnu dans le modèle (absent du registre) ne doit
        pas lever d'exception — il est simplement ignoré.
        """
        meta_a = _make_metadata("tool_a", "tool_a")
        ToolRegistry._tools["tool_a"] = meta_a

        parent = _make_agent_model(["tool_a", "unknown_tool"])
        child = _make_agent_model(["another_unknown"])

        # Ne doit pas lever d'exception
        result = _merge_tools(child, parent)

        assert len(result) == 1
        assert meta_a.func in result
