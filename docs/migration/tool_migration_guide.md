# Guide de Migration - Système d'Outils IA Optimisé

## Vue d'ensemble

Ce guide explique comment migrer les outils IA existants vers le nouveau système de décorateurs optimisés (`@ai_tool`, `@search_tool`, `@playlist_tool`, `@music_tool`).

## Avantages du nouveau système

- **Performances améliorées** : Cache intelligent, monitoring, optimisations RPi4
- **Maintenance simplifiée** : Décorateurs au lieu de registres manuels
- **Sécurité renforcée** : Validation stricte des paramètres et gestion des erreurs
- **Observabilité** : Métriques détaillées et logs structurés
- **Flexibilité** : Support des anciens registres et migration progressive

## Étapes de migration

### 1. Analyse des outils existants

Identifiez tous les outils actuellement enregistrés dans le système :

```python
# Ancien système - Vérifier le registre existant
from backend.ai.utils.registry import TOOL_REGISTRY

print("Outils existants:")
for name, tool in TOOL_REGISTRY.items():
    print(f"- {name}: {tool.get('description', 'Aucune description')}")
```

### 2. Préparation de la migration

Créez un fichier de migration pour chaque outil :

```python
# tools/migration_tracker.py
MIGRATION_STATUS = {
    "search_tracks": "pending",  # pending, in_progress, completed
    "generate_playlist": "pending",
    "get_artist_info": "pending",
    # ... autres outils
}
```

### 3. Migration progressive - Exemple concret

#### Avant (ancien système)

```python
# tools/music_tools.py
def search_tracks(query, artist=None, genre=None, limit=25):
    """Ancienne implémentation"""
    # Logique de recherche directe
    return {"tracks": [], "count": 0}

# Enregistrement manuel
TOOL_REGISTRY["search_tracks"] = {
    "callable": search_tracks,
    "description": "Recherche des pistes musicales",
    "expose": "service"
}
```

#### Après (nouveau décorateur)

```python
# tools/music_tools.py
from backend.ai.utils.decorators import search_tool

@search_tool(
    name="search_tracks",
    description="Recherche des pistes musicales par titre, artiste ou album",
    allowed_agents=["search_agent", "playlist_agent"],
    timeout=30,
    version="2.0"  # Nouveau système
)
async def search_tracks(
    query: str,
    artist: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = 25,
    session: AsyncSession = None
) -> Dict[str, Any]:
    """Nouvelle implémentation avec le décorateur optimisé"""
    # Logique de recherche améliorée
    return {"tracks": [], "count": 0}
```

### 4. Script de migration automatique

```python
# scripts/migrate_tools.py
import asyncio
from backend.ai.utils.decorators import ai_tool
from backend.ai.utils.registry import TOOL_REGISTRY, ToolRegistry
from backend.api.utils.logging import logger

async def migrate_single_tool(tool_name: str, new_tool_func):
    """Migre un outil individuel"""
    try:
        # 1. Récupérer les infos de l'ancien outil
        old_tool = TOOL_REGISTRY.get(tool_name)
        if not old_tool:
            logger.warning(f"Outil {tool_name} introuvable dans l'ancien registre")
            return False
        
        # 2. Vérifier que le nouveau tool est décoré
        if not hasattr(new_tool_func, '_ai_tool_metadata'):
            logger.error(f"L'outil {tool_name} n'est pas décoré avec @ai_tool")
            return False
        
        # 3. Migrer vers le nouveau registre
        new_registry = ToolRegistry()
        await new_registry.register_tool(new_tool_func)
        
        logger.info(f"✅ Migration réussie pour {tool_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Échec de migration pour {tool_name}: {e}")
        return False

async def migrate_all_tools():
    """Migre tous les outils existants"""
    logger.info("🚀 Début de la migration des outils IA")
    
    # Import des nouveaux outils décorés
    from tools.music_tools import search_tracks, generate_playlist, get_artist_info
    
    tools_to_migrate = {
        "search_tracks": search_tracks,
        "generate_playlist": generate_playlist,
        "get_artist_info": get_artist_info,
    }
    
    results = {}
    for tool_name, tool_func in tools_to_migrate.items():
        success = await migrate_single_tool(tool_name, tool_func)
        results[tool_name] = success
    
    # Rapport de migration
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    logger.info(f"📊 Migration terminée: {successful}/{total} outils migrés")
    
    return results

if __name__ == "__main__":
    asyncio.run(migrate_all_tools())
```

### 5. Tests de validation

```python
# tests/test_tool_migration.py
import pytest
from backend.ai.utils.decorators import ai_tool
from backend.ai.utils.registry import ToolRegistry

def test_tool_decoration():
    """Test que l'outil est correctement décoré"""
    @ai_tool(name="test_tool", description="Test tool")
    async def test_func():
        return {"status": "ok"}
    
    # Vérifier la présence des métadonnées
    assert hasattr(test_func, '_ai_tool_metadata')
    metadata = test_func._ai_tool_metadata
    assert metadata['name'] == "test_tool"
    assert metadata['description'] == "Test tool"

def test_registry_integration():
    """Test l'intégration avec le registre"""
    registry = ToolRegistry()
    
    @ai_tool(name="integration_test", description="Test integration")
    async def test_tool():
        return {"test": True}
    
    # Le tool doit être automatiquement enregistré
    # (grâce au processus d'import automatique)
    registered_tools = registry.list_tools()
    assert "integration_test" in registered_tools

@pytest.mark.asyncio
async def test_tool_execution():
    """Test l'exécution d'un outil migré"""
    from tools.music_tools import search_tracks
    
    # Test d'exécution basique
    result = await search_tracks(
        query="test",
        session=None  # Sera injecté automatiquement
    )
    
    assert isinstance(result, dict)
    assert "tracks" in result
```

## Stratégie de migration progressive

### Phase 1: Préparation
1. Analyser les outils existants
2. Créer les nouveaux outils décorés en parallèle
3. Configurer le système de double registre

### Phase 2: Migration sélective
1. Migrer les outils les moins critiques en premier
2. Tester chaque outil migré
3. Maintenir les anciens outils en parallèle

### Phase 3: Migration complète
1. Migrer tous les outils restants
2. Vérifier que tous les tests passent
3. Supprimer l'ancien système

## Commandes utiles

```bash
# Vérifier l'état de la migration
python scripts/check_migration_status.py

# Lancer la migration
python scripts/migrate_tools.py

# Tester un outil spécifique
python -m pytest tests/test_tool_migration.py::test_tool_execution -v

# Valider la configuration
python -c "from backend.ai.utils.decorators import validate_tool_config; validate_tool_config()"
```

## Points d'attention

### 1. Compatibilité ascendante
- Maintenir les anciens outils fonctionnels pendant la transition
- Utiliser des alias pour les outils migrés
- Documenter les changements de signature

### 2. Performance
- Tester la performance avant/après migration
- Vérifier que le cache fonctionne correctement
- Surveiller l'utilisation mémoire sur RPi4

### 3. Sécurité
- Valider que les nouveaux outils respectent les permissions
- Vérifier la gestion des sessions DB
- Tester les cas d'erreur

### 4. Observabilité
- Configurer les métriques avant la migration
- Surveiller les logs d'exécution
- Vérifier les alertes de performance

## Rollback en cas de problème

Si des problèmes surviennent après la migration :

```python
# scripts/rollback_migration.py
from backend.ai.utils.registry import TOOL_REGISTRY, ToolRegistry

async def rollback_to_old_system():
    """Revenir à l'ancien système en cas de problème"""
    logger.warning("🔄 Rollback vers l'ancien système d'outils")
    
    # Désactiver le nouveau registre
    new_registry = ToolRegistry()
    new_registry.disable()
    
    # Réactiver l'ancien registre
    TOOL_REGISTRY.enable_fallback_mode()
    
    logger.info("✅ Rollback terminé")
```

## Suivi de la migration

Utilisez le fichier de suivi pour monitorer l'avancement :

```python
# migration_status.json
{
  "migration_started": "2025-12-29T17:00:00Z",
  "tools": {
    "search_tracks": {
      "status": "completed",
      "migrated_at": "2025-12-29T17:05:00Z",
      "performance_improvement": "15%"
    },
    "generate_playlist": {
      "status": "in_progress",
      "migrated_at": null,
      "performance_improvement": null
    }
  },
  "overall_progress": "33%"
}
```

Ce guide vous permettra de migrer en toute sécurité vers le nouveau système d'outils optimisé tout en maintenant la stabilité de l'application.