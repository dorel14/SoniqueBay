# Plan de correction — Pylance `track_audio_features_service.py`

## Informations collectées

- Fichier impacté : `backend/api/services/track_audio_features_service.py`
- Modèle SQLAlchemy cible : `backend/api/models/track_audio_features_model.py`
- Erreurs Pylance signalées :
  1. `None` non itérable (ligne ~650) — destructuration directe d'un résultat potentiellement `None` :
     - `avg_bpm, min_bpm, max_bpm = bpm_stats.first()`
  2. Attributs inconnus sur `TrackAudioFeatures` (lignes ~828, ~830, ~832) :
     - `mir_source`, `mir_version`, `confidence_score` n'existent pas dans le modèle `TrackAudioFeatures`
- Vérification modèle :
  - `TrackAudioFeatures` expose `analysis_source` (pas `mir_source`)
  - pas de colonnes `mir_version` ni `confidence_score`
- Contrainte architecture :
  - correction incrémentale côté service, sans ajout de DB access hors API
  - éviter d’introduire des champs non présents en ORM

## Plan de modification (fichier par fichier)

1. `backend/api/services/track_audio_features_service.py`
   - Corriger `get_analysis_statistics` :
     - gérer explicitement le cas `bpm_stats.first() is None` avant destructuration
   - Corriger `update_with_mir_integration` :
     - supprimer les affectations directes à des attributs non déclarés sur le modèle (`mir_source`, `mir_version`, `confidence_score`)
     - conserver le mapping métier valide :
       - `mir_source` -> `analysis_source`
     - laisser `mir_version` et `confidence_score` en métadonnées de log uniquement tant que le schéma ORM ne les porte pas
   - Ajouter un TODO ciblé pour migration future si ces champs doivent devenir persistés.

2. `docs/plans/TODO.md`
   - Ajouter la checklist d’exécution des étapes, puis la mettre à jour à l’avancement.

3. `tests/` (minimal)
   - Ajouter un test unitaire ciblé sur `get_analysis_statistics` pour le cas sans stats BPM (retour `None`) afin d’éviter la régression du `None` non itérable.
   - Ajouter un test unitaire ciblé sur `update_with_mir_integration` pour garantir qu’aucun attribut inconnu n’est accédé/écrit.

## Fichiers dépendants à éditer

- `backend/api/services/track_audio_features_service.py`
- `docs/plans/TODO.md`
- `tests/...` (nouveau test ciblé service audio features, chemin exact selon structure existante des tests backend)

## Étapes de suivi

- Exécuter les tests ciblés (commande Python/pytest compatible Windows PowerShell).
- Vérifier disparition des diagnostics Pylance reportés.
- Préparer un commit Conventional Commits (format: `fix(audio-features): ...`).
