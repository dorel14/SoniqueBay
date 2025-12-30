# Guide de Référence Rapide - Système de Décorateurs AI

## 🚀 Démarrage Rapide

### Créer un Nouvel Outil

```python
from backend.ai.utils.decorators import ai_tool

@ai_tool(
    name="mon_nouvel_outil",
    description="Description de l'outil",
    allowed_agents=["agent1", "agent2"],
    timeout=30,
    version="1.0",
    priority="normal",
    cache_strategy="redis"
)
async def mon_nouvel_outil(param1: str, param2: int = 10, session=None):
    """Docstring avec description des paramètres et retour"""
    # Logique métier ici
    return {"result": "success"}
```

### Valider les Paramètres

```python
from backend.ai.utils.decorators import validate_tool_config

def validator_func(param1: str, param2: int) -> bool:
    if not param1:
        raise ValueError("param1 ne peut pas être vide")
    if param2 < 0:
        raise ValueError("param2 doit être positif")
    return True

# Appliquer la validation
mon_nouvel_outil = validate_tool_config(validator_func)(mon_nouvel_outil)
```

## 📁 Structure des Fichiers

```
backend/ai/
├── utils/
│   ├── decorators.py          # Décorateurs et fonctions utilitaires
│   └── registry.py            # Registre des outils
├── tools/                     # Outils du système (auto-enregistrés)
│   ├── __init__.py
│   ├── search_tools.py
│   ├── playlist_tools.py
│   └── system_tools.py
└── examples/                  # Exemples et modèles
    ├── decorator_examples.py
    └── migrated_tools_example.py
```

## 🔧 Configuration des Outils

### Paramètres du Décorateur `@ai_tool`

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `name` | str | ✅ | Nom unique de l'outil |
| `description` | str | ✅ | Description pour les agents |
| `allowed_agents` | list[str] | ✅ | Liste des agents autorisés |
| `timeout` | int | ❌ | Timeout en secondes (défaut: 30) |
| `version` | str | ❌ | Version de l'outil (défaut: "1.0") |
| `priority` | str | ❌ | "low", "normal", "high" (défaut: "normal") |
| `cache_strategy` | str | ❌ | "none", "memory", "redis" (défaut: "memory") |

### Stratégies de Cache

- **`none`** : Pas de cache
- **`memory`** : Cache en mémoire (défaut)
- **`redis`** : Cache Redis avec TTL

### Niveaux de Priorité

- **`low`** : Tâches en arrière-plan
- **`normal`** : Tâches standard
- **`high`** : Tâches urgentes

## 🔍 Utilisation dans les Agents

### Appeler un Outil depuis un Agent

```python
# Dans un agent, utiliser tool_call pour exécuter un outil
result = await tool_call("search_tracks", {
    "query": "rock 90s",
    "genre": "rock",
    "limit": 20
})
```

### Structure de Réponse Recommandée

```python
{
    "success": True,
    "data": { ... },          # Données principales
    "metadata": {             # Métadonnées d'exécution
        "execution_time": "0.123s",
        "cache_hit": False,
        "version": "1.0"
    }
}
```

## 🛠️ Outils Migrés Disponibles

### Outils de Recherche
- `search_tracks` : Recherche de pistes musicales
- `search_artists` : Recherche d'artistes
- `search_albums` : Recherche d'albums

### Outils de Playlist
- `generate_playlist` : Génération de playlists
- `add_to_playlist` : Ajout de pistes à une playlist
- `remove_from_playlist` : Suppression de pistes

### Outils Système
- `scan_library` : Scan de la bibliothèque
- `analyze_mood` : Analyse d'humeur
- `get_system_status` : Statut du système

## 📊 Monitoring et Logs

### Logs Structurés

Tous les outils utilisent des logs structurés :

```python
# Logs automatiques inclus
logger.info(f"Outil {tool_name} exécuté par {agent_name}")
logger.error(f"Erreur dans {tool_name}: {error}")
logger.warning(f"Timeout approaching for {tool_name}")
```

### Métriques Disponibles

- Temps d'exécution
- Taux de succès/échec
- Utilisation du cache
- Fréquence d'utilisation par agent

## 🔄 Migration depuis l'Ancien Système

### Étapes de Migration

1. **Identifier les outils existants** dans `_old_archived/`
2. **Créer la nouvelle version** avec `@ai_tool`
3. **Tester la compatibilité** avec les agents
4. **Mettre à jour les agents** pour utiliser `tool_call`
5. **Archiver l'ancienne version**

### Outils Déjà Migrés

- ✅ `search_tracks`
- ✅ `generate_playlist`
- ✅ `scan_library`
- ✅ `analyze_mood`

## 🚨 Bonnes Pratiques

### Performance
- Utiliser le cache approprié pour les outils fréquemment utilisés
- Définir des timeouts réalistes
- Optimiser les requêtes de base de données

### Sécurité
- Toujours définir `allowed_agents`
- Valider les paramètres d'entrée
- Logger les actions sensibles

### Maintenance
- Versionner les outils
- Documenter les paramètres
- Tester avec différents agents

## 🆘 Dépannage

### Erreurs Communes

**ToolNotFoundError** : L'outil n'est pas enregistré
- Vérifier l'import du module
- S'assurer que le décorateur est appliqué

**AgentNotAuthorizedError** : Agent non autorisé
- Ajouter l'agent à `allowed_agents`
- Vérifier le nom de l'agent

**TimeoutError** : Outil trop lent
- Optimiser la logique de l'outil
- Augmenter le timeout si nécessaire

### Debug

```python
# Activer les logs détaillés
import logging
logging.getLogger('backend.ai.tools').setLevel(logging.DEBUG)
```

## 📚 Exemples Complets

Voir les fichiers d'exemple :
- `backend/ai/examples/decorator_examples.py`
- `backend/ai/examples/migrated_tools_example.py`

## 🔗 Liens Utiles

- [Guide de Migration](docs/migration/tool_migration_guide.md)
- [Documentation Complète](docs/architecture/agent_complement.md)
- [API Reference](backend/ai/utils/decorators.py)