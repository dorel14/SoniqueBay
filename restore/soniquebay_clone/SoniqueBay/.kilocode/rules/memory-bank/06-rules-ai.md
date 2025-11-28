# Règles IA et Agents – (Persona)

## Objectif
Guider les agents automatiques pour qu’ils produisent du code cohérent avec SoniqueBay.

## Ce que l’IA doit respecter
- Utiliser l’architecture existante
- Placer la logique métier dans les services
- Pas de `print`
- Gestion logs via `utils/logging.py`
- Pas de DB directe hors API

## Ce que l’IA ne doit PAS faire
- Toucher aux secrets (`.env`)
- Ajouter une dépendance au mauvais conteneur
- Bypasser API/GraphQL
- Bloquer la SSE progression
- Charger tout en mémoire (RPi4 !)

## Communication backend
- Temps réel = SSE prioritaire
- WS réservé au player / contrôle queue
- Batch = GraphQL mutations optimisées

## Interaction avec code existant
- Réutilisation avant réécriture
- Code modulaire
- Pas de duplication

## Règle clé
**L’IA ne code pas “vite” mais “maintenable”**.
