# 07 - Contraintes Raspberry Pi

Cette section détaille les contraintes spécifiques liées à l'utilisation d'un Raspberry Pi pour Memory Bank Kilocode.

## 1. Limites matérielles

- **RAM :** 2 à 8 Go selon le modèle. Impact direct sur le nombre de processus simultanés et la taille des caches.
- **CPU :** Quad-core ARM, fréquence modérée. Les tâches lourdes de ML/IA doivent être optimisées ou déportées.
- **Stockage :** Carte microSD (souvent 32 à 128 Go) → privilégier un usage minimal et optimiser les lectures/écritures.
- **Connectivité :** Ethernet/Wi-Fi, USB 2.0/3.0. Gestion efficace des flux audio/streaming nécessaire.

## 2. Contraintes logicielles

- **Systèmes supportés :** Raspberry Pi OS (32/64 bits), Ubuntu Server ARM.
- **Gestion des processus :** Limiter les threads simultanés pour éviter les blocages.
- **Swap :** À utiliser avec prudence (carte SD fragile).
- **Optimisation Python :**
  - Utilisation de `asyncio` pour I/O non bloquant.
  - Traitement audio et flux en streaming sans surcharge CPU.
  - Indexation locale de la bibliothèque musicale légère (SQLite, Whoosh).

## 3. Bonnes pratiques

- **Démarrage automatique :** Services critiques via `systemd`.
- **Monitoring :** Surveiller RAM, CPU et espace disque.
- **Logs légers :** Rotation des fichiers de logs pour éviter de saturer la SD.
- **Docker léger :** Conteneuriser uniquement ce qui est nécessaire, éviter images trop lourdes.

