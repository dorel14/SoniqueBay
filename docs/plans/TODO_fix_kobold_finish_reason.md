# TODO - Correction du bug finish_reason dans kobold_model.py

## Étapes à compléter

- [x] Analyser le fichier et comprendre le bug
- [x] Créer le plan de correction
- [x] Obtenir confirmation de l'utilisateur
- [x] Créer le fichier TODO (ce fichier)
- [x] Modifier la condition dans `_get_event_iterator`
- [x] Ajouter un commentaire explicatif
- [x] Vérifier la correction

## Détails de la correction

**Fichier :** `backend/ai/models/kobold_model.py`

**Ligne concernée :** ~107 dans la méthode `_get_event_iterator`

**Changement :**
```python
# AVANT (bug)
if finish_reason and finish_reason != "null":

# APRÈS (corrigé)
if finish_reason:  # None (JSON null) → continue, toute valeur non-nulle → arrêt
```

**Raison :** JSON `null` est parsé comme Python `None`, pas la chaîne `"null"`. La condition `!= "null"` était donc toujours vraie et inutile.
