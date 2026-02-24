# Analyse : Compatibilité Raspberry Pi 4 - Embeddings 768 dimensions

## Problématique

Le modèle `all-mpnet-base-v2` (768 dimensions) pose des défis sur Raspberry Pi 4 :

### Consommation Ressources

| Modèle | Dimensions | Taille | RAM requise | Temps inférence |
|--------|-----------|--------|-------------|-----------------|
| `all-MiniLM-L6-v2` | 384 | ~80MB | ~150MB | ~50ms |
| `all-mpnet-base-v2` | 768 | ~420MB | ~600MB | ~120ms |
| `paraphrase-MiniLM-L3-v2` | 384 | ~40MB | ~80MB | ~30ms |

### Contraintes Raspberry Pi 4

- **RAM totale** : 2GB, 4GB ou 8GB
- **RAM disponible** pour l'app : ~1-2GB (système + autres services)
- **CPU** : 4 cœurs ARM Cortex-A72 @ 1.5GHz
- **Pas de GPU** accélération pour les inférences

## Options disponibles

### Option 1 : Garder 768D avec `all-mpnet-base-v2` (Actuel)

**Avantages :**

- Qualité sémantique supérieure
- Compatible avec le schéma DB existant (Vector(768))

**Inconvénients :**

- ~420MB de RAM juste pour le modèle
- Risque d'OOM (Out Of Memory) sur RPi4 2GB
- Temps de chargement lent au démarrage

**Mitigations possibles :**

```python
# Dans ollama_embedding_service.py
# Charger le modèle une seule fois au démarrage du worker
# et le garder en mémoire partagée

# TODO: Implémenter un singleton thread-safe pour le modèle
# TODO: Surveiller la mémoire avec psutil et logger des warnings
# TODO: Fallback vers 384D si OOM détecté
```

### Option 2 : Réduire à 384D avec `all-MiniLM-L6-v2`

**Avantages :**

- ~80MB de RAM (5x moins)
- 2-3x plus rapide sur CPU
- Très stable sur RPi4

**Inconvénients :**

- Nécessite une migration DB : `Vector(768)` → `Vector(384)`
- Perte de précision sémantique (légère)

**Migration requise :**

```sql
-- Alembic migration nécessaire
ALTER TABLE mir_synonyms ALTER COLUMN embedding TYPE vector(384);
-- Re-générer tous les embeddings existants
```

### Option 3 : Modèle hybride selon la charge

**Stratégie :**

- Utiliser `all-mpnet-base-v2` (768D) sur les machines avec ≥4GB RAM
- Utiliser `all-MiniLM-L6-v2` (384D) sur les machines avec 2GB RAM

**Implémentation :**

```python
# Détection automatique de la mémoire disponible
import psutil

def select_model_by_memory():
    available_mb = psutil.virtual_memory().available / (1024 * 1024)
    if available_mb > 3000:  # >3GB disponible
        return "all-mpnet-base-v2", 768
    else:
        return "all-MiniLM-L6-v2", 384
```

### Option 4 : Service d'embeddings externe (Ollama/KoboldCpp)

**Stratégie :**

- Ne pas charger sentence-transformers dans le worker
- Appeler le service LLM (Ollama) pour les embeddings
- Utiliser `nomic-embed-text` via API HTTP

**Avantages :**

- Zero RAM utilisée dans le worker pour les embeddings
- Modèle peut être sur une autre machine
- Mise à jour du modèle sans redéployer le worker

**Inconvénients :**

- Latence réseau (~10-50ms)
- Dépendance au service LLM
- Nécessite que le service LLM soit up

## Recommandation

### Pour le développement actuel (768D avec `all-mpnet-base-v2`)

**OK si :**

- RPi4 4GB ou 8GB
- Peu d'embeddings générés simultanément
- Worker dédié aux embeddings (pas d'autres tâches lourdes)

**À surveiller :**

```python
# Dans ollama_embedding_service.py
import psutil

def check_memory_before_embedding():
    mem = psutil.virtual_memory()
    if mem.percent > 85:
        logger.warning("[EMBEDDING] Mémoire critique, risque d'OOM")
        # Option: attendre ou utiliser un modèle plus léger
```

### Pour la production sur RPi4 2GB

**Recommandé : Option 2 (384D) ou Option 4 (Ollama externe)**

La migration DB est nécessaire mais le gain en stabilité est significatif.

## Décision à prendre

1. **Garder 768D** : Accepter la consommation mémoire et surveiller
2. **Migrer vers 384D** : Nécessite migration DB mais plus stable sur RPi4
3. **Implémenter Option 3** : Logique conditionnelle selon la mémoire

## TODO pour l'implémentation actuelle

```python
# backend_worker/services/ollama_embedding_service.py

# TODO: Ajouter monitoring mémoire avant chaque inférence
# TODO: Implémenter un cache LRU pour éviter de re-générer les mêmes embeddings
# TODO: Fallback vers modèle léger si OOM détecté
# TODO: Batch processing pour optimiser les inférences multiples
# TODO: Option de désactiver les embeddings si mémoire insuffisante
```

## Conclusion

La dimension 768D est **techniquement compatible** avec RPi4 4GB+ mais :

- Nécessite une surveillance mémoire stricte
- Peut causer des ralentissements lors du chargement initial
- Risque d'instabilité sur RPi4 2GB

Pour une solution robuste sur toutes les configurations RPi4, la migration vers 384D est recommandée.
