# Supabase pour SoniqueBay

Ce dossier contient la configuration et les scripts pour l'infrastructure Supabase de SoniqueBay.

## Structure

```
supabase/
├── Dockerfile              # Image PostgreSQL personnalisée avec extensions
├── db_init/                # Scripts d'initialisation SQL
│   └── init_supabase.sql   # Extensions et configuration initiale
├── scripts/                # Scripts de gestion
│   ├── start.sh           # Démarrer les services Supabase
│   ├── stop.sh            # Arrêter les services Supabase
│   └── logs.sh            # Afficher les logs
├── config/                 # Fichiers de configuration
└── volumes/                # Données persistantes (montées via docker-compose)
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| supabase-db | 54322 | PostgreSQL avec extensions (vector, pg_trgm, etc.) |
| supabase-realtime | 54323 | WebSocket temps réel |
| supabase-auth | 54324 | Authentification JWT (GoTrue) |
| supabase-meta | - | API métadonnées pour Studio |
| supabase-dashboard | 54325 | Interface d'administration (Studio) |

## Démarrage rapide

```bash
# Démarrer tous les services Supabase
./supabase/scripts/start.sh

# Vérifier l'état
docker-compose ps

# Afficher les logs
./supabase/scripts/logs.sh

# Arrêter les services
./supabase/scripts/stop.sh
```

## Accès

- **Dashboard**: http://localhost:54325
- **Database**: `postgresql://supabase:supabase@localhost:54322/postgres`
- **Auth API**: http://localhost:54324

## Extensions installées

- `uuid-ossp` : Génération d'UUID
- `pg_trgm` : Recherche textuelle approximative
- `pgcrypto` : Fonctions cryptographiques
- `vector` : Recherche vectorielle (pgvector)

## Variables d'environnement

Voir `.env.example` à la racine du projet pour les variables Supabase requises.
