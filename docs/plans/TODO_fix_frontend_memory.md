# TODO - Correction du problème de mémoire frontend

## Étapes complétées
- [x] Analyser l'erreur et identifier la cause (hot reload surveillant trop de fichiers)
- [x] Modifier `frontend/start_ui.py` pour limiter `uvicorn_reload_dirs` à `/app/frontend`
- [x] Mettre à jour `docker-compose.yml` avec optimisations Python (`PYTHONUNBUFFERED`, `PYTHONDONTWRITEBYTECODE`)
- [x] Créer la documentation du plan de correction

## Étapes restantes (à exécuter par l'utilisateur)
- [ ] Reconstruire le conteneur frontend : `docker-compose build frontend`
- [ ] Redémarrer le service : `docker-compose up -d frontend`
- [ ] Vérifier les logs : `docker-compose logs -f frontend`
- [ ] Tester l'accès au frontend : `curl http://localhost:8080`
- [ ] Vérifier la stabilité sur plusieurs heures

## Commandes PowerShell pour tester

```powershell
# Reconstruire et redémarrer
docker-compose build frontend
docker-compose up -d frontend

# Vérifier les logs
docker-compose logs -f frontend

# Tester l'accès
curl http://localhost:8080

# Vérifier la consommation mémoire
docker stats soniquebay-frontend --no-stream
