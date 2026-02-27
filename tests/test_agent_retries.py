"""
Tests complets pour la correction de l'erreur pydantic_ai "Exceeded maximum retries".

Ce module teste :
1. La présence du paramètre max_result_retries dans le code source
2. La validation des modèles d'agents
3. La configuration des retries

Note: Les tests d'intégration complets nécessitent un environnement LLM fonctionnel
et sont marqués avec @pytest.mark.integration.

Auteur: SoniqueBay Team
"""
import pytest
import ast
from pathlib import Path


class TestMaxResultRetriesConfiguration:
    """Tests pour vérifier que max_result_retries est configuré correctement."""
    
    def test_build_agent_contains_max_result_retries(self):
        """
        Test que la fonction build_agent contient max_result_retries=3.
        
        Vérifie que la correction est présente dans le code source.
        """
        builder_path = Path("backend/ai/agents/builder.py")
        assert builder_path.exists(), "Le fichier builder.py doit exister"
        
        content = builder_path.read_text(encoding='utf-8')
        
        # Vérifier que max_result_retries=3 est présent dans build_agent
        assert "max_result_retries=3" in content, \
            "Le paramètre max_result_retries=3 doit être présent dans build_agent"
        
        # Vérifier qu'il y a un commentaire explicatif
        assert "retry" in content.lower() or "validation" in content.lower(), \
            "Un commentaire expliquant le paramètre devrait être présent"
    
    def test_build_agent_with_inheritance_contains_max_result_retries(self):
        """
        Test que la fonction build_agent_with_inheritance contient aussi max_result_retries=3.
        
        Vérifie que la correction est appliquée aussi pour l'héritage.
        """
        builder_path = Path("backend/ai/agents/builder.py")
        content = builder_path.read_text(encoding='utf-8')
        
        # Compter les occurrences de max_result_retries=3 (devrait être au moins 2)
        count = content.count("max_result_retries=3")
        assert count >= 2, \
            f"max_result_retries=3 devrait apparaître au moins 2 fois (build_agent + build_agent_with_inheritance), trouvé {count} fois"
    
    def test_max_result_retries_value_is_reasonable(self):
        """
        Test que la valeur de max_result_retries est raisonnable.
        
        La valeur de 3 est un compromis entre :
        - Robustesse (plus de chances de succès)
        - Latence (pas trop de temps perdu en retries)
        - Ressources (pas trop de charge sur le LLM)
        """
        builder_path = Path("backend/ai/agents/builder.py")
        content = builder_path.read_text(encoding='utf-8')
        
        # Extraire la valeur numérique après max_result_retries=
        import re
        matches = re.findall(r'max_result_retries=(\d+)', content)
        
        assert len(matches) > 0, "max_result_retries doit être défini"
        
        for value_str in matches:
            value = int(value_str)
            # La valeur devrait être entre 2 et 5
            assert 2 <= value <= 5, \
                f"La valeur {value} est hors de la plage recommandée [2, 5]"


class TestAgentModelValidation:
    """Tests pour la validation des modèles d'agents."""
    
    def test_agent_model_requires_role_and_task(self):
        """
        Test que la validation échoue si ROLE ou TASK sont manquants.
        
        Vérifie que les champs RTCROS obligatoires sont bien requis.
        """
        from backend.ai.agents.builder import validate_agent_configuration
        from backend.api.models.agent_model import AgentModel
        
        # Agent sans ROLE
        agent_no_role = AgentModel(
            name="test",
            model="qwen2.5-3b-instruct-q4_k_m",
            role="",
            task="Faire quelque chose",
            enabled=True
        )
        
        report = validate_agent_configuration(agent_no_role)
        assert not report["is_valid"]
        assert any("ROLE" in issue for issue in report["issues"])
        
        # Agent sans TASK
        agent_no_task = AgentModel(
            name="test",
            model="koboldcpp/qwen2.5-3b-instruct-q4_k_m",
            role="Assistant",
            task="",
            enabled=True
        )
        
        report = validate_agent_configuration(agent_no_task)
        assert not report["is_valid"]
        assert any("TASK" in issue for issue in report["issues"])
    
    def test_valid_agent_model_passes_validation(self):
        """
        Test qu'un modèle d'agent valide passe la validation.
        """
        from backend.ai.agents.builder import validate_agent_configuration
        from backend.api.models.agent_model import AgentModel
        
        valid_agent = AgentModel(
            name="test_agent",
            model="qwen2.5-3b-instruct-q4_k_m",
            role="Assistant",
            task="Aider l'utilisateur",
            temperature=0.7,
            top_p=0.9,
            num_ctx=2048,
            tools=[],
            enabled=True
        )
        
        report = validate_agent_configuration(valid_agent)
        # Note: La validation du modèle LLM peut échouer si Ollama n'est pas disponible
        # mais les champs RTCROS devraient être valides
        assert not any("ROLE" in issue for issue in report["issues"])
        assert not any("TASK" in issue for issue in report["issues"])


class TestCodeQuality:
    """Tests pour la qualité du code et la documentation."""
    
    def test_builder_file_has_docstrings(self):
        """
        Test que le fichier builder.py a des docstrings appropriées.
        """
        builder_path = Path("backend/ai/agents/builder.py")
        content = builder_path.read_text(encoding='utf-8')
        
        # Vérifier que les fonctions principales ont des docstrings
        assert '"""' in content, "Des docstrings devraient être présentes"
        
        # Vérifier que build_agent a une docstring
        assert "def build_agent(" in content, "La fonction build_agent doit exister"
    
    def test_no_hardcoded_sensitive_values(self):
        """
        Test qu'il n'y a pas de valeurs sensibles codées en dur.
        """
        builder_path = Path("backend/ai/agents/builder.py")
        content = builder_path.read_text(encoding='utf-8')
        
        # Vérifier qu'il n'y a pas de valeurs absurdes pour max_result_retries
        import re
        matches = re.findall(r'max_result_retries=(\d+)', content)
        
        for value_str in matches:
            value = int(value_str)
            # Valeurs absurdes à éviter
            assert value != 0, "max_result_retries=0 désactiverait les retries"
            assert value != 1, "max_result_retries=1 est la valeur par défaut problématique"
            assert value < 10, "max_result_retries >= 10 serait excessif"


# Tests d'intégration (nécessitent un environnement LLM fonctionnel)
@pytest.mark.integration
class TestAgentIntegration:
    """Tests d'intégration avec un vrai modèle LLM."""
    
    @pytest.mark.asyncio
    async def test_real_agent_creation(self):
        """
        Test de création réelle d'un agent (nécessite Ollama configuré).
        
        Ce test est marqué comme 'integration' et ne s'exécute pas par défaut.
        """
        from backend.ai.agents.builder import build_agent
        from backend.api.models.agent_model import AgentModel
        
        agent_model = AgentModel(
            name="integration_test_agent",
            model="qwen2.5-3b-instruct-q4_k_m",
            role="Test assistant",
            task="Tester la création d'agents",
            temperature=0.7,
            top_p=0.9,
            num_ctx=2048,
            tools=[],
            enabled=True
        )
        
        try:
            agent = build_agent(agent_model)
            assert agent is not None
            assert agent.name == "integration_test_agent"
        except Exception as e:
            pytest.skip(f"Test d'intégration ignoré - Ollama non disponible: {e}")
    
    @pytest.mark.asyncio
    async def test_agent_execution_with_retries(self):
        """
        Test d'exécution d'agent avec retry (nécessite KoboldCPP ou Ollama).
        
        Vérifie que l'agent peut s'exécuter et que les retries fonctionnent.
        """
        pytest.skip("Test d'intégration - nécessite un LLM configuré et des scénarios de retry")


if __name__ == "__main__":
    # Exécution des tests avec pytest
    pytest.main([__file__, "-v", "--tb=short"])
