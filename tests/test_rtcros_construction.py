import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.agent_model import AgentModel
from backend.ai.agents.builder import (
    build_rtcros_prompt,
    build_agent,
    build_agent_with_inheritance,
    validate_agent_configuration,
    _build_specialized_prompt,
    _merge_tools
)
from backend.ai.utils.registry import ToolRegistry


class TestRTCROSPrompt:
    """Tests pour la construction du prompt RTCROS."""

    def test_build_rtcros_prompt_basic(self):
        """Test de la construction d'un prompt RTCROS basique."""
        
        agent_model = Mock(spec=AgentModel)
        agent_model.role = "Agent de recherche musicale"
        agent_model.task = "Rechercher des pistes selon critères"
        agent_model.constraints = None
        agent_model.rules = None
        agent_model.output_schema = None
        agent_model.state_strategy = None
        
        prompt = build_rtcros_prompt(agent_model)
        
        assert "ROLE:" in prompt
        assert "Agent de recherche musicale" in prompt
        assert "TASK:" in prompt
        assert "Rechercher des pistes selon critères" in prompt
        assert "INSTRUCTIONS:" in prompt

    def test_build_rtcros_prompt_complete(self):
        """Test de la construction d'un prompt RTCROS complet."""
        
        agent_model = Mock(spec=AgentModel)
        agent_model.role = "Agent spécialisé"
        agent_model.task = "Tâche spécifique"
        agent_model.constraints = "Contraintes importantes"
        agent_model.rules = "Règles strictes"
        agent_model.output_schema = '{"result": "string"}'
        agent_model.state_strategy = "Stratégie d'état"
        
        prompt = build_rtcros_prompt(agent_model)
        
        assert "ROLE:" in prompt
        assert "Agent spécialisé" in prompt
        assert "TASK:" in prompt
        assert "Tâche spécifique" in prompt
        assert "CONSTRAINTS:" in prompt
        assert "Contraintes importantes" in prompt
        assert "RULES:" in prompt
        assert "Règles strictes" in prompt
        assert "OUTPUT_SCHEMA:" in prompt
        assert '{"result": "string"}' in prompt
        assert "STATE_STRATEGY:" in prompt
        assert "Stratégie d'état" in prompt

    def test_build_rtcros_prompt_empty_fields(self):
        """Test de la construction avec certains champs vides."""
        
        agent_model = Mock(spec=AgentModel)
        agent_model.role = "Role"
        agent_model.task = "Task"
        agent_model.constraints = ""
        agent_model.rules = None
        agent_model.output_schema = ""
        agent_model.state_strategy = None
        
        prompt = build_rtcros_prompt(agent_model)
        
        assert "ROLE:" in prompt
        assert "Role" in prompt
        assert "TASK:" in prompt
        assert "Task" in prompt
        # Les champs vides ne doivent pas apparaître
        assert "CONSTRAINTS:" not in prompt
        assert "RULES:" not in prompt
        assert "OUTPUT_SCHEMA:" not in prompt
        assert "STATE_STRATEGY:" not in prompt


class TestAgentBuilder:
    """Tests pour le builder d'agents."""

    @patch('backend.ai.agents.builder.get_ollama_model')
    @patch('backend.ai.agents.builder.ToolRegistry')
    def test_build_agent_basic(self, mock_registry, mock_get_model):
        """Test de la construction d'un agent basique."""
        
        # Mock du modèle LLM
        mock_model = Mock()
        mock_get_model.return_value = mock_model
        
        # Mock des tools
        mock_tool = Mock()
        mock_registry.get.return_value = mock_tool
        
        # Création du modèle d'agent
        agent_model = Mock(spec=AgentModel)
        agent_model.name = "test_agent"
        agent_model.model = "phi3:mini"
        agent_model.role = "Test role"
        agent_model.task = "Test task"
        agent_model.constraints = None
        agent_model.rules = None
        agent_model.output_schema = None
        agent_model.state_strategy = None
        agent_model.tools = ["test_tool"]
        agent_model.temperature = 0.2
        agent_model.top_p = 0.9
        agent_model.num_ctx = 2048
        
        # Construction de l'agent
        agent = build_agent(agent_model)
        
        # Vérifications
        assert agent.name == "test_agent"
        assert agent.model == mock_model
        assert "ROLE:" in agent.system_prompt
        assert "Test role" in agent.system_prompt
        assert "TASK:" in agent.system_prompt
        assert "Test task" in agent.system_prompt
        assert len(agent.tools) == 1

    @patch('backend.ai.agents.builder.get_ollama_model')
    def test_build_agent_validation_errors(self, mock_get_model):
        """Test des validations lors de la construction d'agent."""
        
        # Test sans nom
        agent_model = Mock(spec=AgentModel)
        agent_model.name = ""
        agent_model.model = "phi3:mini"
        agent_model.role = "Test role"
        agent_model.task = "Test task"
        
        with pytest.raises(ValueError, match="Le nom de l'agent est requis"):
            build_agent(agent_model)
        
        # Test sans modèle
        agent_model.name = "test_agent"
        agent_model.model = ""
        
        with pytest.raises(ValueError, match="Le modèle LLM est requis"):
            build_agent(agent_model)
        
        # Test sans ROLE
        agent_model.model = "phi3:mini"
        agent_model.role = ""
        
        with pytest.raises(ValueError, match="Les champs ROLE et TASK sont requis"):
            build_agent(agent_model)
        
        # Test sans TASK
        agent_model.role = "Test role"
        agent_model.task = ""
        
        with pytest.raises(ValueError, match="Les champs ROLE et TASK sont requis"):
            build_agent(agent_model)

    @patch('backend.ai.agents.builder.get_ollama_model')
    @patch('backend.ai.agents.builder.ToolRegistry')
    def test_build_agent_missing_tools(self, mock_registry, mock_get_model):
        """Test de la gestion des tools manquants."""
        
        # Mock du modèle LLM
        mock_model = Mock()
        mock_get_model.return_value = mock_model
        
        # Mock ToolRegistry pour retourner None (tool manquant)
        mock_registry.get.return_value = None
        
        # Création du modèle d'agent avec tools
        agent_model = Mock(spec=AgentModel)
        agent_model.name = "test_agent"
        agent_model.model = "phi3:mini"
        agent_model.role = "Test role"
        agent_model.task = "Test task"
        agent_model.tools = ["missing_tool", "another_missing_tool"]
        agent_model.temperature = 0.2
        agent_model.top_p = 0.9
        agent_model.num_ctx = 2048
        
        # Construction de l'agent (doit réussir malgré les tools manquants)
        agent = build_agent(agent_model)
        
        # Vérification que l'agent est construit mais sans tools
        assert agent.name == "test_agent"
        assert len(agent.tools) == 0

    @patch('backend.ai.agents.builder.get_ollama_model')
    def test_build_agent_model_error(self, mock_get_model):
        """Test de la gestion des erreurs de configuration du modèle LLM."""
        
        # Mock du modèle LLM qui lève une exception
        mock_get_model.side_effect = Exception("Model configuration error")
        
        # Création du modèle d'agent
        agent_model = Mock(spec=AgentModel)
        agent_model.name = "test_agent"
        agent_model.model = "invalid_model"
        agent_model.role = "Test role"
        agent_model.task = "Test task"
        agent_model.tools = []
        agent_model.temperature = 0.2
        agent_model.top_p = 0.9
        agent_model.num_ctx = 2048
        
        # Construction de l'agent (doit lever une exception)
        with pytest.raises(ValueError, match="Impossible de configurer le modèle LLM"):
            build_agent(agent_model)


class TestAgentInheritance:
    """Tests pour l'héritage d'agents."""

    @patch('backend.ai.agents.builder.build_agent')
    @patch('backend.ai.agents.builder._build_specialized_prompt')
    @patch('backend.ai.agents.builder._merge_tools')
    @patch('backend.ai.agents.builder.get_ollama_model')
    def test_build_agent_with_inheritance(
        self, 
        mock_get_model, 
        mock_merge_tools, 
        mock_build_prompt, 
        mock_build_agent
    ):
        """Test de la construction d'un agent avec héritage."""
        
        # Mock du modèle LLM
        mock_model = Mock()
        mock_get_model.return_value = mock_model
        
        # Mock du parent agent
        mock_parent_agent = Mock()
        mock_parent_agent.model = mock_model
        mock_build_agent.return_value = mock_parent_agent
        
        # Mock des fonctions d'héritage
        mock_build_prompt.return_value = "Specialized prompt"
        mock_merge_tools.return_value = ["merged_tool1", "merged_tool2"]
        
        # Création des modèles d'agent
        parent_model = Mock(spec=AgentModel)
        parent_model.name = "parent_agent"
        parent_model.model = "phi3:mini"
        parent_model.role = "Parent role"
        parent_model.task = "Parent task"
        parent_model.tools = ["parent_tool"]
        
        child_model = Mock(spec=AgentModel)
        child_model.name = "child_agent"
        child_model.model = "phi3:mini"
        child_model.role = "Child role"
        child_model.task = "Child task"
        child_model.base_agent = "parent_agent"
        child_model.tools = ["child_tool"]
        
        base_agents = {"parent_agent": parent_model}
        
        # Construction de l'agent avec héritage
        agent = build_agent_with_inheritance(child_model, base_agents)
        
        # Vérifications
        assert agent.name == "child_agent"
        assert agent.model == mock_model
        assert agent.system_prompt == "Specialized prompt"
        assert agent.tools == ["merged_tool1", "merged_tool2"]
        
        # Vérification des appels
        mock_build_agent.assert_called_once_with(parent_model)
        mock_build_prompt.assert_called_once_with(child_model, parent_model)
        mock_merge_tools.assert_called_once_with(child_model, parent_model)

    def test_build_agent_without_inheritance(self):
        """Test de la construction d'un agent sans héritage."""
        
        with patch('backend.ai.agents.builder.build_agent') as mock_build_agent:
            # Création du modèle d'agent sans héritage
            agent_model = Mock(spec=AgentModel)
            agent_model.base_agent = None
            
            mock_agent = Mock()
            mock_build_agent.return_value = mock_agent
            
            # Construction de l'agent
            agent = build_agent_with_inheritance(agent_model, {})
            
            # Vérification que build_agent est appelé directement
            mock_build_agent.assert_called_once_with(agent_model)
            assert agent == mock_agent

    def test_build_agent_inheritance_missing_parent(self):
        """Test de la construction avec héritage mais parent manquant."""
        
        with patch('backend.ai.agents.builder.build_agent') as mock_build_agent:
            # Création du modèle d'agent avec héritage mais parent manquant
            agent_model = Mock(spec=AgentModel)
            agent_model.name = "child_agent"
            agent_model.base_agent = "missing_parent"
            
            mock_agent = Mock()
            mock_build_agent.return_value = mock_agent
            
            # Construction de l'agent
            agent = build_agent_with_inheritance(agent_model, {})
            
            # Vérification que build_agent est appelé directement (sans héritage)
            mock_build_agent.assert_called_once_with(agent_model)
            assert agent == mock_agent


class TestAgentValidation:
    """Tests pour la validation des agents."""

    def test_validate_agent_configuration_valid(self):
        """Test de validation d'un agent valide."""
        
        agent_model = Mock(spec=AgentModel)
        agent_model.name = "valid_agent"
        agent_model.model = "phi3:mini"
        agent_model.role = "Valid role"
        agent_model.task = "Valid task"
        agent_model.constraints = "Valid constraints"
        agent_model.rules = "Valid rules"
        agent_model.output_schema = '{"result": "string"}'
        agent_model.state_strategy = "Valid strategy"
        agent_model.tools = ["valid_tool"]
        agent_model.temperature = 0.2
        agent_model.top_p = 0.9
        agent_model.num_ctx = 2048
        
        with patch('backend.ai.agents.builder.ToolRegistry') as mock_registry:
            mock_registry.get.return_value = Mock()  # Tool exists
            
            with patch('backend.ai.agents.builder.get_ollama_model') as mock_get_model:
                mock_get_model.return_value = Mock()  # Model valid
                
                report = validate_agent_configuration(agent_model)
        
        assert report["agent_name"] == "valid_agent"
        assert report["is_valid"] == True
        assert len(report["issues"]) == 0
        assert len(report["warnings"]) == 0
        assert report["details"]["model"] == "phi3:mini"
        assert report["details"]["tools_count"] == 1

    def test_validate_agent_configuration_missing_required_fields(self):
        """Test de validation avec champs requis manquants."""
        
        agent_model = Mock(spec=AgentModel)
        agent_model.name = "invalid_agent"
        agent_model.model = "phi3:mini"
        agent_model.role = ""  # Manquant
        agent_model.task = None  # Manquant
        agent_model.tools = []
        
        report = validate_agent_configuration(agent_model)
        
        assert report["agent_name"] == "invalid_agent"
        assert report["is_valid"] == False
        assert len(report["issues"]) == 2
        assert any("ROLE" in issue for issue in report["issues"])
        assert any("TASK" in issue for issue in report["issues"])

    def test_validate_agent_configuration_missing_tools(self):
        """Test de validation avec tools manquants."""
        
        agent_model = Mock(spec=AgentModel)
        agent_model.name = "agent_with_missing_tools"
        agent_model.model = "phi3:mini"
        agent_model.role = "Valid role"
        agent_model.task = "Valid task"
        agent_model.tools = ["missing_tool1", "missing_tool2"]
        
        with patch('backend.ai.agents.builder.ToolRegistry') as mock_registry:
            mock_registry.get.return_value = None  # Tools manquants
            
            report = validate_agent_configuration(agent_model)
        
        assert report["agent_name"] == "agent_with_missing_tools"
        assert report["is_valid"] == True  # Les tools manquants sont des warnings, pas des erreurs
        assert len(report["warnings"]) == 1
        assert "Tools manquants" in report["warnings"][0]

    def test_validate_agent_configuration_model_error(self):
        """Test de validation avec erreur de modèle LLM."""
        
        agent_model = Mock(spec=AgentModel)
        agent_model.name = "agent_with_model_error"
        agent_model.model = "invalid_model"
        agent_model.role = "Valid role"
        agent_model.task = "Valid task"
        agent_model.tools = []
        
        with patch('backend.ai.agents.builder.get_ollama_model') as mock_get_model:
            mock_get_model.side_effect = Exception("Model error")
            
            report = validate_agent_configuration(agent_model)
        
        assert report["agent_name"] == "agent_with_model_error"
        assert report["is_valid"] == False
        assert len(report["issues"]) == 1
        assert "Modèle LLM invalide" in report["issues"][0]


class TestInheritanceHelpers:
    """Tests pour les fonctions d'aide à l'héritage."""

    def test_build_specialized_prompt(self):
        """Test de la construction d'un prompt spécialisé."""
        
        parent_model = Mock(spec=AgentModel)
        parent_model.role = "Parent role"
        parent_model.task = "Parent task"
        parent_model.constraints = "Parent constraints"
        
        child_model = Mock(spec=AgentModel)
        child_model.role = "Child role"
        child_model.task = "Child task"
        child_model.constraints = "Child constraints"
        
        with patch('backend.ai.agents.builder.build_rtcros_prompt') as mock_build_prompt:
            mock_build_prompt.side_effect = [
                "Parent prompt",  # Pour le parent
                "Child prompt"    # Pour l'enfant
            ]
            
            prompt = _build_specialized_prompt(child_model, parent_model)
        
        assert "Parent prompt" in prompt
        assert "Child prompt" in prompt
        assert "--- SPÉCIALISATION ENFANT ---" in prompt
        assert "--- FIN SPÉCIALISATION ---" in prompt
        
        # Vérification des appels
        assert mock_build_prompt.call_count == 2

    @patch('backend.ai.agents.builder.ToolRegistry')
    def test_merge_tools(self, mock_registry):
        """Test de la fusion des tools parent/enfant."""
        
        # Mock des tools
        parent_tool = Mock()
        parent_tool.__name__ = "parent_tool"
        
        child_tool = Mock()
        child_tool.__name__ = "child_tool"
        
        # Mock du registry
        mock_registry.get.side_effect = [
            Mock(name="parent_tool", func=parent_tool),  # parent_tool
            Mock(name="child_tool", func=child_tool),    # child_tool
        ]
        
        parent_model = Mock(spec=AgentModel)
        parent_model.tools = ["parent_tool"]
        
        child_model = Mock(spec=AgentModel)
        child_model.tools = ["child_tool"]
        
        tools = _merge_tools(child_model, parent_model)
        
        # Vérification que les tools sont fusionnés
        assert len(tools) == 2
        assert parent_tool in tools
        assert child_tool in tools
        
        # Vérification des appels au registry
        assert mock_registry.get.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])