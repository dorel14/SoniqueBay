# Workflow Git – (Persona)

## Branches
- `main` = stable et toujours déployable
- feature : `feat/xxx`
- fix : `fix/xxx`
- refactor : `refactor/xxx`

## Format commits
`<type>(scope): message court`

Types autorisés :
- feat / fix / refactor / style / docs / test / chore

Exemples :
- `feat(playqueue): ajout webradios`
- `fix(db): doublons dans Artist`
- `docs(agents): ajout règles contribution`

## Règles
- Commits atomiques
- Messages impératifs
- Pas de feature + refactor mélangé
- Squash & merge recommandé

## Validation avant PR
- `docker-compose up` sans erreur
- lint & format ok
- tests passent
- aucun fichier sensible (`.env`, DB locale…)

## Objectif IA
Quand l’IA génère une PR ou propose du code :
1. Elle doit proposer un message de commit propre
2. Elle ne touche pas aux secrets
3. Elle respecte la structure Git
