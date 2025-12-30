#!/bin/sh
# Script d'entrée point pour le conteneur Flower avec récupération complète de base de données
# Résout les problèmes KeyError: b'events' en initialisant correctement la structure
# Compatible avec /bin/sh et compatible RPi4

set -e

DB_PATH="/data/flower.db"
BACKUP_PATH="/data/flower.db.backup"
LOG_FILE="/data/flower_recovery.log"

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Fonction pour tester l'intégrité de la base de données
test_db_integrity() {
    db_file="$1"
    
    if [ ! -f "$db_file" ]; then
        log "INFO: Base de données '$db_file' n'existe pas"
        return 1
    fi
    
    # Test complet avec Python pour vérifier que la base n'est pas corrompue
    if python3 -c "
import shelve
import sys
try:
    with shelve.open('$db_file', 'r') as db:
        keys = list(db.keys())
        # Vérifier les clés essentielles attendues par Flower
        required_keys = ['events']
        missing_keys = [k for k in required_keys if k not in keys and k.encode() not in keys]
        if missing_keys:
            print(f'MISSING_KEYS: {missing_keys}')
            sys.exit(1)
        else:
            print('DB_OK_STRUCTURE')
            sys.exit(0)
except KeyError as e:
    if b'events' in str(e):
        print('MISSING_EVENTS_KEY')
        sys.exit(1)
    else:
        print(f'KEY_ERROR: {e}')
        sys.exit(1)
except Exception as e:
    print(f'DB_ERROR: {e}')
    sys.exit(1)
" 2>/dev/null | grep -q "DB_OK_STRUCTURE"; then
        return 0
    else
        return 1
    fi
}

# Fonction pour créer une base de données avec la structure complète Flower
create_flower_db() {
    db_file="$1"
    
    log "INFO: Création d'une nouvelle base de données avec structure Flower complète"
    
    # Supprimer tous les fichiers liés à la base de données
    rm -f "$db_file" "${db_file}.dir" "${db_file}.pag" "${db_file}.bak" "${db_file}.dat"
    
    # Créer une nouvelle base de données avec Python et structure Flower
    if python3 -c "
import shelve
import sys
from datetime import datetime

try:
    # Créer la nouvelle base avec structure complète
    with shelve.open('$db_file', 'c') as db:
        # Structure attendue par Flower basée sur l'analyse du code source
        db['events'] = {}  # Dictionnaire des événements
        db['celerymon.task-meta'] = {}  # Métadonnées des tâches
        db['celerymon.task-state'] = {}  # État des tâches
        db['monitor'] = {}  # Données de monitoring
        db['flower_state'] = {}  # État Flower
        
        # Métadonnées de la base
        db['initialized'] = 'true'
        db['created_at'] = '$(date -Iseconds)'
        db['version'] = '2.0'
        db['flower_compatible'] = 'true'
        
        # Index pour la performance
        db['task_index'] = {}
        db['worker_index'] = {}
        
    print('Base de données Flower créée avec succès')
    sys.exit(0)
except Exception as e:
    print(f'Erreur création base: {e}')
    sys.exit(1)
"; then
        log "INFO: Nouvelle base de données Flower créée avec succès"
        return 0
    else
        log "ERROR: Échec de la création de la nouvelle base"
        return 1
    fi
}

# Fonction pour vérifier la structure après création
verify_flower_structure() {
    db_file="$1"
    
    log "INFO: Vérification de la structure Flower créée"
    
    if python3 -c "
import shelve
import sys
try:
    with shelve.open('$db_file', 'r') as db:
        keys = list(db.keys())
        expected_keys = ['events', 'celerymon.task-meta', 'celerymon.task-state', 'monitor', 'flower_state']
        
        print(f'Clés créées: {keys}')
        
        # Vérifier que toutes les clés attendues sont présentes
        missing = []
        for key in expected_keys:
            if key not in keys and key.encode() not in keys:
                missing.append(key)
        
        if missing:
            print(f'Clés manquantes: {missing}')
            sys.exit(1)
        else:
            print('Structure Flower complète')
            sys.exit(0)
except Exception as e:
    print(f'Erreur vérification: {e}')
    sys.exit(1)
"; then
        log "INFO: Structure Flower vérifiée avec succès"
        return 0
    else
        log "ERROR: Échec de la vérification de structure"
        return 1
    fi
}

# Fonction principale de récupération
recover_flower_db() {
    db_file="$1"
    
    log "=== DÉBUT DE LA PROCÉDURE DE RÉCUPÉRATION FLOWER AVANCÉE ==="
    
    # Créer le répertoire de données si nécessaire
    mkdir -p "$(dirname "$db_file")"
    
    # Test d'intégrité initial
    if test_db_integrity "$db_file"; then
        log "INFO: Base de données valide avec structure complète, démarrage normal de Flower"
        return 0
    fi
    
    log "WARNING: Base de données corrompue, incomplète ou inaccessible"
    
    # Sauvegarder l'ancienne base si elle existe
    if [ -f "$db_file" ]; then
        log "INFO: Sauvegarde de l'ancienne base de données"
        if cp "$db_file" "$BACKUP_PATH" 2>/dev/null; then
            log "INFO: Sauvegarde créée: $BACKUP_PATH"
        else
            log "WARNING: Impossible de créer la sauvegarde"
        fi
    fi
    
    # Créer une nouvelle base avec structure Flower complète
    log "INFO: Création d'une nouvelle base de données avec structure Flower complète"
    if create_flower_db "$db_file"; then
        log "INFO: Base de données créée, vérification de la structure..."
        
        if verify_flower_structure "$db_file"; then
            log "INFO: Récupération réussie avec structure complète, démarrage de Flower"
            return 0
        else
            log "ERROR: Échec de la vérification de structure Flower"
            return 1
        fi
    else
        log "ERROR: Échec de la création de la base de données Flower"
        return 1
    fi
}

# Attendre que Redis soit disponible
wait_for_redis() {
    log "INFO: Attente de la disponibilité de Redis..."
    timeout=60
    counter=0
    
    while [ $counter -lt $timeout ]; do
        if command -v redis-cli >/dev/null 2>&1; then
            if redis-cli -h redis -p 6379 ping >/dev/null 2>&1; then
                log "INFO: Redis est disponible"
                return 0
            fi
        else
            log "INFO: redis-cli non disponible, assumption que Redis est prêt"
            return 0
        fi
        sleep 2
        counter=$((counter + 2))
        log "INFO: Attente Redis... ($counter/$timeout secondes)"
    done
    
    log "WARNING: Timeout d'attente de Redis, continuation quand même"
    return 0
}

# Script principal
main() {
    log "INFO: Démarrage du script d'entrée Flower (version avancée avec structure)"
    
    # Créer le répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    
    # Récupération de la base de données
    if ! recover_flower_db "$DB_PATH"; then
        log "ERROR: Échec de la récupération de la base de données Flower"
        exit 1
    fi
    
    # Attendre Redis (optionnel)
    wait_for_redis
    
    log "INFO: Démarrage de Flower avec les arguments: $*"
    log "INFO: Configuration Flower optimisée pour SoniqueBay"
    
    # Lancer Flower avec les arguments passés au script
    exec "$@"
}

# Exécution du script principal
main "$@"