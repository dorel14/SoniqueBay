#!/usr/bin/env python3
"""
Script de migration automatique des outils IA
Transforme les outils existants vers le nouveau système de décorateurs optimisés
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from backend.ai.utils.registry import TOOL_REGISTRY, ToolRegistry
from backend.api.utils.logging import logger

# Ajouter le path du projet
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ToolMigrationTracker:
    """Suit l'état de la migration des outils"""
    
    def __init__(self, status_file: str = "migration_status.json"):
        self.status_file = Path(status_file)
        self.status = self._load_status()
    
    def _load_status(self) -> Dict[str, Any]:
        """Charge le statut de migration depuis le fichier"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Impossible de charger le statut de migration: {e}")
        
        return {
            "migration_started": None,
            "migration_completed": None,
            "tools": {},
            "overall_progress": "0%",
            "errors": []
        }
    
    def save_status(self):
        """Sauvegarde le statut de migration"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Impossible de sauvegarder le statut de migration: {e}")
    
    def update_tool_status(self, tool_name: str, status: str, details: Dict[str, Any] = None):
        """Met à jour le statut d'un outil"""
        self.status["tools"][tool_name] = {
            "status": status,
            "migrated_at": details.get("migrated_at"),
            "performance_improvement": details.get("performance_improvement"),
            "error": details.get("error"),
            "tested": details.get("tested", False)
        }
        
        # Calculer le progrès global
        total_tools = len(self.status["tools"])
        completed_tools = sum(1 for tool in self.status["tools"].values() 
                            if tool["status"] == "completed")
        
        if total_tools > 0:
            progress = (completed_tools / total_tools) * 100
            self.status["overall_progress"] = f"{progress:.0f}%"
        
        self.save_status()
    
    def mark_error(self, tool_name: str, error: str):
        """Marque une erreur pour un outil"""
        self.status["errors"].append({
            "tool": tool_name,
            "error": error,
            "timestamp": asyncio.get_event_loop().time()
        })
        self.save_status()


class ToolMigrator:
    """Migrateur principal pour les outils IA"""
    
    def __init__(self):
        self.tracker = ToolMigrationTracker()
        self.new_registry = ToolRegistry()
        self.migration_stats = {
            "analyzed": 0,
            "migrated": 0,
            "errors": 0,
            "skipped": 0
        }
    
    async def analyze_existing_tools(self) -> Dict[str, Any]:
        """Analyse les outils existants dans l'ancien registre"""
        logger.info("🔍 Analyse des outils existants...")
        
        tools_analysis = {}
        
        for tool_name, tool_info in TOOL_REGISTRY.items():
            try:
                tool_func = tool_info.get("callable")
                if not tool_func:
                    continue
                
                # Analyser la fonction
                analysis = await self._analyze_tool_function(tool_name, tool_func, tool_info)
                tools_analysis[tool_name] = analysis
                
                self.migration_stats["analyzed"] += 1
                
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de {tool_name}: {e}")
                self.tracker.mark_error(tool_name, str(e))
                self.migration_stats["errors"] += 1
        
        return tools_analysis
    
    async def _analyze_tool_function(self, tool_name: str, tool_func, tool_info: Dict) -> Dict[str, Any]:
        """Analyse une fonction d'outil spécifique"""
        import inspect
        
        analysis = {
            "name": tool_name,
            "description": tool_info.get("description", "Aucune description"),
            "expose": tool_info.get("expose", "unknown"),
            "signature": None,
            "parameters": [],
            "return_type": None,
            "is_async": inspect.iscoroutinefunction(tool_func),
            "can_migrate": True,
            "migration_notes": []
        }
        
        try:
            # Analyser la signature
            sig = inspect.signature(tool_func)
            analysis["signature"] = str(sig)
            
            # Analyser les paramètres
            for param_name, param in sig.parameters.items():
                param_info = {
                    "name": param_name,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "default": str(param.default) if param.default != inspect.Parameter.empty else "required",
                    "has_default": param.default != inspect.Parameter.empty
                }
                analysis["parameters"].append(param_info)
            
            # Vérifier la compatibilité avec le nouveau système
            if not analysis["is_async"]:
                analysis["can_migrate"] = False
                analysis["migration_notes"].append("La fonction doit être async pour la migration")
            
            if "session" not in [p["name"] for p in analysis["parameters"]]:
                analysis["migration_notes"].append("Considérer l'ajout du paramètre 'session' pour l'injection automatique")
            
        except Exception as e:
            analysis["can_migrate"] = False
            analysis["migration_notes"].append(f"Erreur d'analyse: {e}")
        
        return analysis
    
    async def generate_migration_template(self, tool_analysis: Dict[str, Any]) -> str:
        """Génère un template de migration pour un outil"""
        tool_name = tool_analysis["name"]
        
        template = f'''# Migration pour {tool_name}
# Remplacez cette fonction par la version décorée

from backend.ai.utils.decorators import ai_tool

@ai_tool(
    name="{tool_name}",
    description="{tool_analysis["description"]}",
    allowed_agents=["search_agent", "playlist_agent"],  # Ajustez selon vos besoins
    timeout=30,
    version="2.0"
)
async def {tool_name}({self._format_parameters(tool_analysis["parameters"])}):
    """
    {tool_analysis["description"]}
    
    Args:
    {self._format_docstring_params(tool_analysis["parameters"])}
    
    Returns:
        Dict[str, Any]: Résultat de l'opération
    """
    # Votre logique métier ici
    # Utilisez self.get_db_session() pour obtenir une session DB si nécessaire
    
    return {{
        "status": "success",
        "message": "Outil {tool_name} exécuté avec succès"
    }}

# Note: N'oubliez pas d'importer ce module pour l'enregistrer automatiquement
'''
        return template
    
    def _format_parameters(self, parameters: List[Dict]) -> str:
        """Formate les paramètres pour la signature de fonction"""
        formatted = []
        for param in parameters:
            if param["name"] == "session":
                formatted.append("session: AsyncSession = None")
            else:
                type_hint = param["type"] if param["type"] != "Any" else "str"
                default = f" = {param['default']}" if param["has_default"] else ""
                formatted.append(f"{param['name']}: {type_hint}{default}")
        
        return ", ".join(formatted)
    
    def _format_docstring_params(self, parameters: List[Dict]) -> str:
        """Formate les paramètres pour la docstring"""
        lines = []
        for param in parameters:
            lines.append(f"        {param['name']} ({param['type']}): {param['description'] if 'description' in param else 'Paramètre'}.")
        
        return "\n".join(lines)
    
    async def create_migration_files(self, tools_analysis: Dict[str, Any]):
        """Crée les fichiers de migration pour tous les outils"""
        migration_dir = project_root / "tools" / "migration"
        migration_dir.mkdir(parents=True, exist_ok=True)
        
        for tool_name, analysis in tools_analysis.items():
            if analysis["can_migrate"]:
                template = await self.generate_migration_template(analysis)
                
                file_path = migration_dir / f"{tool_name}_migration.py"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(template)
                
                logger.info(f"📝 Template de migration créé: {file_path}")
    
    async def migrate_single_tool(self, tool_name: str, new_tool_func) -> bool:
        """Migre un outil individuel vers le nouveau système"""
        try:
            # Vérifier que l'outil est décoré
            if not hasattr(new_tool_func, '_ai_tool_metadata'):
                raise ValueError(f"L'outil {tool_name} n'est pas décoré avec @ai_tool")
            
            # Enregistrer dans le nouveau registre
            await self.new_registry.register_tool(new_tool_func)
            
            # Tester l'outil
            test_result = await self._test_tool(new_tool_func, tool_name)
            
            # Mettre à jour le statut
            self.tracker.update_tool_status(tool_name, "completed", {
                "migrated_at": asyncio.get_event_loop().time(),
                "performance_improvement": "TBD",  # À calculer après tests
                "tested": test_result
            })
            
            self.migration_stats["migrated"] += 1
            logger.info(f"✅ Migration réussie pour {tool_name}")
            return True
            
        except Exception as e:
            self.tracker.update_tool_status(tool_name, "error", {
                "error": str(e)
            })
            self.tracker.mark_error(tool_name, str(e))
            self.migration_stats["errors"] += 1
            logger.error(f"❌ Échec de migration pour {tool_name}: {e}")
            return False
    
    async def _test_tool(self, tool_func, tool_name: str) -> bool:
        """Test basique d'un outil migré"""
        try:
            # Test d'import et de structure
            if not hasattr(tool_func, '_ai_tool_metadata'):
                return False
            
            metadata = tool_func._ai_tool_metadata
            if metadata['name'] != tool_name:
                return False
            
            # Test de signature (sans exécution)
            import inspect
            sig = inspect.signature(tool_func)
            if not sig.parameters:
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Test échoué pour {tool_name}: {e}")
            return False
    
    async def run_full_migration(self) -> Dict[str, Any]:
        """Lance la migration complète"""
        logger.info("🚀 Début de la migration des outils IA")
        
        # Initialiser le statut
        self.tracker.status["migration_started"] = asyncio.get_event_loop().time()
        self.tracker.save_status()
        
        try:
            # 1. Analyser les outils existants
            tools_analysis = await self.analyze_existing_tools()
            
            # 2. Créer les templates de migration
            await self.create_migration_files(tools_analysis)
            
            # 3. Exemple de migration (à adapter selon vos besoins)
            # Cette partie nécessitera que vous créiez les nouveaux outils décorés
            
            # 4. Rapport final
            self.tracker.status["migration_completed"] = asyncio.get_event_loop().time()
            self.tracker.save_status()
            
            return {
                "success": True,
                "stats": self.migration_stats,
                "analysis": tools_analysis,
                "migration_templates_created": True
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la migration: {e}")
            self.tracker.mark_error("migration", str(e))
            return {
                "success": False,
                "error": str(e),
                "stats": self.migration_stats
            }


async def main():
    """Fonction principale"""
    # Configurer le logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Créer et lancer le migrateur
    migrator = ToolMigrator()
    result = await migrator.run_full_migration()
    
    # Afficher le rapport
    print("\n" + "="*50)
    print("📊 RAPPORT DE MIGRATION")
    print("="*50)
    print(f"Succès: {result.get('success', False)}")
    print(f"Outils analysés: {migrator.migration_stats['analyzed']}")
    print(f"Migrés: {migrator.migration_stats['migrated']}")
    print(f"Erreurs: {migrator.migration_stats['errors']}")
    print(f"Progrès global: {migrator.tracker.status['overall_progress']}")
    
    if migrator.tracker.status["errors"]:
        print("\n❌ ERREURS:")
        for error in migrator.tracker.status["errors"]:
            print(f"  - {error['tool']}: {error['error']}")
    
    print("\n📁 Templates de migration créés dans: tools/migration/")
    print(f"📈 Statut détaillé dans: {migrator.tracker.status_file}")
    
    return result


if __name__ == "__main__":
    # Lancer la migration
    asyncio.run(main())