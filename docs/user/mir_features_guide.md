# Guide des Fonctionnalités MIR

## Introduction

Le système MIR (Music Information Retrieval) de SoniqueBay analyse automatiquement vos fichiers audio pour extraire des caractéristiques musicales avancées. Ces données enrichissent votre bibliothèque et permettent des recommandations intelligentes.

## Caractéristiques Extraites

### Descripteurs Audio

| Caractéristique | Description | Plage |
|----------------|-------------|-------|
| BPM | Tempo de la piste | 60-200 |
| Énergie | Intensité globale de la piste | 0.0 - 1.0 |
| Danceabilité | Facilité à danser sur la piste | 0.0 - 1.0 |
| Valence | Valence émotionnelle (négatif → positif) | 0.0 - 1.0 |
| Acousticness | Présence d'instruments acoustiques | 0.0 - 1.0 |
| Instrumentalness | Absence de voix | 0.0 - 1.0 |
| Speechiness | Présence de parole | 0.0 - 1.0 |
| Liveness | Présence d'ambiance live | 0.0 - 1.0 |

### Tags AcoustID

Le système utilise AcoustID pour extraire des tags de MusicBrainz:

- **Tags haut-niveau** (`ab:hi:*`): Mood, genre, instrumentation
- **Tags bas-niveau** (`ab:lo:*`): Caractéristiques techniques

## Tags Synthétiques

Les tags synthétiques sont des concepts haut-niveau générés automatiquement:

### Moods

| Tag | Description | Critères |
|-----|-------------|----------|
| **Energetic** | Piste énergique | énergie > 0.7, tempo > 120 BPM |
| **Chill** | Piste calme | énergie < 0.3, acousticness > 0.5 |
| **Dark** | Piste sombre | valence < 0.3, energy > 0.4 |
| **Bright** | Piste lumineuse | valence > 0.7, energy > 0.5 |
| **Happy** | Piste joyeuse | valence > 0.7 |
| **Sad** | Piste mélancolique | valence < 0.3 |
| **Aggressive** | Piste agressive | energy > 0.8, valence < 0.4 |
| **Relaxed** | Piste relaxante | energy < 0.4, valence > 0.5 |

### Genres

| Tag | Description | Critères |
|-----|-------------|----------|
| **Electronic** | Musique électronique | instrumentalness > 0.7 |
| **Acoustic** | Musique acoustique | acousticness > 0.7 |
| **Rock** | Musique rock | energy > 0.6, valence moyen |
| **Hip-hop** | Musique hip-hop | speechiness > 0.3, tempo 80-115 |
| **Classical** | Musique classique | instrumentalness > 0.8, complexity > 0.6 |

### Caractéristiques

| Tag | Description | Critères |
|-----|-------------|----------|
| **Vocals** | Présence de voix | instrumentalness < 0.3 |
| **Instrumental** | Absence de voix | instrumentalness > 0.8 |
| **Loopable** | Adapté aux boucles | liveness < 0.3, energy stable |
| **Club-ready** | Adapté aux clubs | danceability > 0.7, energy > 0.7 |
| **Background** | Musique de fond | energy < 0.3, instrumentalness > 0.5 |

## Utilisation

### Recherche par Caractéristiques

```graphql
# Rechercher des pistes énergétiques et danceables
query {
  tracks(
    filters: {
      energy_min: 0.7,
      danceability_min: 0.6
    }
    limit: 20
  ) {
    title
    artist_name
    bpm
    energy_score
    dance_score
    synthetic_tags
  }
}
```

### Création de Playlists Automatiques

```python
# Créer une playlist "Soirée Energétique"
playlist_prompt = """
Crée une playlist de 30 pistes pour une soirée:
- Énergie: haute (> 0.7)
- Danceabilité: haute (> 0.6)
- BPM: 120-140
- Tags: energetic, danceable, club-ready
"""
```

### Recommandations Intelligentes

Le système utilise les données MIR pour générer des recommandations:

```
" Recommande des pistes similaires à 'Blinding Lights' de The Weeknd
en me basant sur:
- BPM similaire (85-95)
- Énergie élevée (> 0.7)
- Genre: Synthwave, Pop
- Mood: Energetic, Happy
"
```

## Interface Utilisateur

### Filtres dans l'Interface

L'interface NiceGUI propose des filtres MIR:

```
🎵 Filtrer par caractéristique:
├── Énergie: [===|======|===] (slider 0-1)
├── Valence: [==|=======|==] (slider 0-1)
├── Danceabilité: [====|====|] (slider 0-1)
├── BPM: [80 __________ 200] (input range)
└── Tags: [🎸] [🎹] [🎤] [🎧] (select multiple)
```

### Affichage des Caractéristiques

Chaque piste affiche ses caractéristiques MIR:

```
┌─────────────────────────────────────────┐
│ 🎵 Piste: Midnight City                 │
│ 👤 Artiste: M83                         │
│ ⏱️ 4:03  │  📊 105 BPM  │  🔊 128kbps  │
├─────────────────────────────────────────┤
│ Caractéristiques MIR:                    │
│ ⚡ Énergie: ████████░░ 0.82            │
│ 💃 Dance: ████████░░ 0.78              │
│ 😊 Valence: ███████░░░ 0.71             │
│ 🎸 Acoustique: ██░░░░░░░ 0.15          │
├─────────────────────────────────────────┤
│ 🏷️ Tags: Energetic, Electronic, Synth   │
└─────────────────────────────────────────┘
```

## API et Intégration

### Endpoints REST

```bash
# Récupérer les données MIR d'une piste
GET /api/v1/mir/{track_id}

# Récupérer les scores MIR
GET /api/v1/mir/{track_id}/scores

# Récupérer les tags synthétiques
GET /api/v1/mir/{track_id}/tags

# Lancer le traitement MIR
POST /api/v1/mir/process
{
  "track_id": 123,
  "file_path": "/music/track.mp3"
}
```

### Exemple de Réponse

```json
{
  "track_id": 123,
  "normalized": {
    "energy": 0.82,
    "valence": 0.71,
    "danceability": 0.78,
    "acousticness": 0.15,
    "tempo": 0.38
  },
  "scores": {
    "energy_score": 0.85,
    "mood_valence": 0.71,
    "dance_score": 0.78,
    "emotional_intensity": 0.75
  },
  "synthetic_tags": [
    {"name": "energetic", "category": "mood", "confidence": 0.9},
    {"name": "electronic", "category": "genre", "confidence": 0.85},
    {"name": "bright", "category": "mood", "confidence": 0.78}
  ]
}
```

## Dépannage

### Données MIR Manquantes

Si une piste n'a pas de données MIR:

1. **Vérifier que le fichier est analysé**:
   ```bash
   curl http://localhost:8000/api/v1/tracks/123/mir_status
   ```

2. **Lancer manuellement l'analyse**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/mir/process \
     -H "Content-Type: application/json" \
     -d '{"track_id": 123, "file_path": "/path/to/file.mp3"}'
   ```

3. **Vérifier les logs**:
   ```bash
   docker-compose logs backend_worker | grep MIR
   ```

### Qualité des Données

Les scores de confiance indiquent la fiabilité:

| Confiance | Signification |
|-----------|---------------|
| 0.9 - 1.0 | Données très fiables |
| 0.7 - 0.9 | Données fiables |
| 0.5 - 0.7 | Données modérément fiables |
| < 0.5 | Données incertaines - re-analyse recommandée |

## Optimisation

### Performance sur Raspberry Pi 4

Le traitement MIR est optimisé pour le RPi4:

- **Traitement asynchrone**: Ne bloque pas l'interface
- **Cache Redis**: Évite les re-calculs
- **Traitement par lots**: Efficace pour les grandes bibliothèques

### Configuration

```yaml
# docker-compose.yml
environment:
  - MIR_BATCH_SIZE=50
  - MIR_CACHE_TTL=7200
  - MIR_WORKERS=2
```

## Foire Aux Questions

**Q: Pourquoi certaines pistes n'ont pas de données MIR?**
R: Le traitement MIR est asynchrome. Les pistes récentes seront analysées en arrière-plan.

**Q: Puis-je forcer une ré-analyse?**
R: Oui, utilisez l'endpoint `POST /api/v1/mir/reprocess/{track_id}`

**Q: Les données MIR sont-elles exactes?**
R: Les algorithmes MIR ont une précision d'environ 80-90% pour les caractéristiques principales.

**Q: Comment les tags synthétiques sont-ils générés?**
R: Ils utilisent un modèle de règles basé sur les caractéristiques normalisées, avec une fusion taxonomique pour la cohérence.
