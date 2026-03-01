# Plan de Nettoyage de la Documentation SoniqueBay

## Résumé Exécutif

Ce document présente le plan de nettoyage de la documentation du projet SoniqueBay. L'analyse a révélé plusieurs catégories de problèmes nécessitant une attention particulière.

---

## 1. Doublons Identifiés (À Supprimer)

### 1.1 Doublons Exacts

| Fichier à supprimer | Raison | Fichier à conserver |
|---------------------|--------|---------------------|
| `troubleshooting/FLOWER_DB_CORRUPTION_FIX.md` | Version courte incomplète | `troubleshooting/SOLUTION_FLOWER_DB_CORRUPTION.md` |
| `troubleshooting/SOLUTION_PERMISSION` (sans extension) | Incomplet, sans extension | `troubleshooting/SOLUTION_PERMISSION_DENIED_DATA.md` |

### 1.2 Doublons Thématiques

| Fichiers concernés | Problème | Action recommandée |
|--------------------|----------|-------------------|
| `implementation_plan.md` + `workers/backend_worker_fix_plan.md` | Contenu très similaire (plan d'implémentation pour les problèmes de tracks) | Conserver uniquement `implementation_plan.md` (plus complet) |

---

## 2. Documentation Obsolète (À Mettre à Jour ou Archiver)

### 2.1 Références à sqlite-vec (Technologie Supprimée)

| Fichier | Problème | Action |
|---------|----------|--------|
| `workers/workers_architecture.md` (ligne 216) | Mentionne "sqlite-vec" pour le stockage vectoriel | Mettre à jour vers "pgvector/PostgreSQL" |
| `monitoring/README_VECTORIZATION.md` (lignes 125, 154, 267, 296) | Références multiples à sqlite-vec | Réécrire pour pgvector |
| `plans/gmm_worker_service_plan.md` (ligne 35) | Diagramme mentionnant sqlite-vec | Mettre à jour le diagramme |

### 2.2 Références à Whoosh (Technologie Supprimée)

| Fichier | Problème | Action |
|---------|----------|--------|
| `architecture/architecture.md` (ligne 160) | Diagramme mentionne "Indexation Whoosh" | Mettre à jour vers "PostgreSQL FTS" |
| `architecture/03-features.md` (ligne 7) | Mentionne "Index Whoosh" | Mettre à jour vers "PostgreSQL FTS" |
| `architecture/07-rpi-constraints.md` (ligne 20) | Mentionne "SQLite, Whoosh" | Mettre à jour vers "PostgreSQL" |
| `workers/feature.md` (ligne 38) | Mentionne "Indexation Whoosh" | Mettre à jour vers "PostgreSQL FTS" |
| `architecture/refactor.md` (ligne 114) | Propose Whoosh comme option | Marquer comme historique ou supprimer |

### 2.3 Documentation à Vérifier/Archiver

| Fichier | Problème | Action |
|---------|----------|--------|
| `architecture/refactor.md` | Plan de refactorisation ancien (structure proposée vs réalité) | Vérifier si encore pertinent ou archiver |
| `architecture/scan_optimization_plan.md` | Très détaillé mais peut être obsolète | Vérifier vs code actuel |

---

## 3. Fichiers TODO - Statut et Actions

### 3.1 TODO Complétés (À Archiver/Supprimer)

Ces fichiers ont toutes leurs tâches cochées et peuvent être supprimés ou convertis en notes:

- `docs/plans/TODO_llm_service_lazy_init.md` - Complété
- `docs/plans/TODO_llm_service_client_optimization.md` - Complété
- `docs/plans/TODO_kobold_model.md` - Complété
- `docs/plans/TODO_fix_streaming_async.md` - Complété
- `docs/plans/TODO_fix_pydantic_ai_retries.md` - Complété
- `docs/plans/TODO_fix_kobold_finish_reason.md` - Complété
- `docs/plans/TODO_fix_chatml_injection.md` - Complété

### 3.2 TODO Partiellement Complétés (À Mettre à Jour)

| Fichier | Statut | Action |
|---------|--------|--------|
| `TODO_fix_streaming_runtime.md` | 2 tâches non cochées | Mettre à jour ou archiver |
| `TODO_fix_llm_connection.md` | Validation non faite | Mettre à jour le statut |
| `TODO_fix_frontend_memory.md` | En attente action utilisateur | Mettre à jour le statut |
| `TODO_fix_entity_manager_api_calls.md` | 2 tâches restantes | Mettre à jour ou archiver |

### 3.3 TODO Non Commencés (À Évaluer)

| Fichier | Évaluation |
|---------|------------|
| `TODO_fix_streaming_sse.md` | Presque terminé (1 tâche restante) |
| `fix_frontend_memory_issue.md` | Similar to TODO_fix_frontend_memory - possible doublon |
| `fix_orchestrator_init_async.md` | À évaluer |

---

## 4. Actions de Nettoyage Recommandées

### 4.1 Suppressions Immédiates (Sans Risque)

```bash
# Supprimer les doublons exacts
docs/troubleshooting/FLOWER_DB_CORRUPTION_FIX.md
docs/troubleshooting/SOLUTION_PERMISSION

# Supprimer les TODO complétés
docs/plans/TODO_llm_service_lazy_init.md
docs/plans/TODO_llm_service_client_optimization.md
docs/plans/TODO_kobold_model.md
docs/plans/TODO_fix_streaming_async.md
docs/plans/TODO_fix_pydantic_ai_retries.md
docs/plans/TODO_fix_kobold_finish_reason.md
docs/plans/TODO_fix_chatml_injection.md
```

### 4.2 Mise à Jour des Références Obsolètes

| Action | Fichiers concernés |
|--------|-------------------|
| Remplacer "sqlite-vec" par "pgvector/PostgreSQL" | 4 fichiers |
| Remplacer "Whoosh" par "PostgreSQL FTS" | 5 fichiers |
| Mettre à jour les diagrammes Mermaid | 3 fichiers |

### 4.3 Révision Manuelle Requise

| Action | Détail |
|--------|--------|
| Archiver `implementation_plan.md` vs `workers/backend_worker_fix_plan.md` | Décider lequel conserver |
| Vérifier `architecture/refactor.md` | Valider si encore pertinent |
| Mettre à jour les TODO partiellement complétés | 4 fichiers à évaluer |

---

## 5. Plan d'Exécution

### Phase 1: Nettoyage Automatique (Sans Risque)
- [ ] Supprimer les doublons exacts identifiés
- [ ] Supprimer les TODO complétés
- [ ] Mettre à jour les références sqlite-vec dans les fichiers identifiés

### Phase 2: Mise à Jour des Références
- [ ] Mettre à jour les références Whoosh
- [ ] Corriger les diagrammes Mermaid
- [ ] Mettre à jour le README principal

### Phase 3: Révision et Validation
- [ ] Évaluer les fichiers restants à archiver
- [ ] Mettre à jour les TODO partiellement complétés
- [ ] Valider la cohérence avec le code actuel

---

## 6. Statistiques

| Catégorie | Nombre |
|-----------|--------|
| Fichiers totaux dans docs/ | ~70 |
| Doublons identifiés | 3 |
| Fichiers avec références obsolètes | 8 |
| TODO complétés (à archiver) | 7 |
| TODO partiellement complétés | 4 |

---

## 7. Recommandations

1. **Créer un dossier `archive/`** pour stocker la documentation historique qui pourrait encore avoir une valeur de référence
2. **Mettre à jour le README.md principal** pour refléter les changements d'architecture (PostgreSQL au lieu de SQLite/TinyDB)
3. **Automatiser la vérification** des références obsolètes avec un script de linting
4. **Établir une politique de documentation** pour éviter l'accumulation de fichiers TODO

---

*Plan créé le 27 février 2026*
*Analyse basée sur la comparaison entre la documentation et le code backend actuel*