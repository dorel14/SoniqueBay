# Correction du problème de mémoire du frontend

## Problème
Le conteneur frontend crashait avec une erreur de mémoire :
```
_rust_notify.WatchfilesRustInternalError: error in underlying watcher: IO error for operation on /app/frontend/pages/api_docs.py: Cannot allocate memory (os error 12)
```

## Cause
Le hot reload de NiceGUI/uvicorn surveillait trop de fichiers, ce qui épuisait la mémoire disponible sur le Raspberry Pi 4 (512MB alloués au conteneur).

## Solution appliquée

### 1. Limitation du répertoire de surveillance (frontend/start_ui.py)
```python
ui.run(
    root,
    host='0.0.0.0',
    title=f'SoniqueBay v{version}',
    favicon='./static/favicon.ico',
    show=False,
    storage_secret=storage_secret,
    uvicorn_reload_excludes='*.log',
    uvicorn_reload_dirs=['/app/frontend'],  # Limite la surveillance au répertoire frontend
)
```

### 2. Optimisations Python (docker-compose.yml)
Ajout de variables d'environnement pour réduire l'empreinte mémoire :
- `PYTHONUNBUFFERED=1` : Désactive le buffering des logs
- `PYTHONDONTWRITEBYTECODE=1` : Empêche la création de fichiers .pyc

## Étapes de test

1. Reconstruire le conteneur frontend :
   ```powershell
   docker-compose build frontend
   ```

2. Redémarrer le service :
   ```powershell
   docker-compose up -d frontend
   ```

3. Vérifier les logs :
   ```powershell
   docker-compose logs -f frontend
   ```

4. S'assurer qu'il n'y a plus d'erreur mémoire et que le frontend répond :
   ```powershell
   curl http://localhost:8080
   ```

## Résultat attendu
- Le frontend démarre sans erreur `Cannot allocate memory`
- Le hot reload fonctionne uniquement pour les fichiers dans `/app/frontend`
- La consommation mémoire reste sous les 512MB alloués

## TODO
- [x] Modifier frontend/start_ui.py pour limiter uvicorn_reload_dirs
- [x] Ajouter optimisations Python dans docker-compose.yml
- [ ] Tester le redémarrage du conteneur
- [ ] Vérifier la stabilité sur plusieurs heures
