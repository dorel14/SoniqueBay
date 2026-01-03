#!/bin/sh
# Script d'entrée point pour le conteneur Flower avec récupération complète de base de données
# Résout les problèmes KeyError: b'events' en initialisant correctement la structure
# Compatible avec /bin/sh et compatible RPi4

set -e

DB_PATH="/data/flower.db"
BACKUP_PATH="/data/flower.db.backup"
LOG_FILE="/data/flower_recovery.log"

# Fonction de logging avec gestion robuste des permissions (sans tee)
log() {
    timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"
    message="$timestamp $1"
    
    # Utiliser uniquement stderr pour éviter les problèmes de permissions
    # Cela garantit que les logs sont toujours visibles même si /data n'est pas accessible
    echo "$message" >&2
    
    # Essayer en arrière-plan d'écrire dans le fichier (non bloquant)
    echo "$message" >> "$LOG_FILE" 2>/dev/null &
    
    return 0
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

# Fonction pour configurer les permissions du répertoire de données
setup_data_permissions() {
    data_dir="/data"
    db_file="/data/flower.db"
    
    # Log simple sans tee pour éviter les erreurs
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Configuration des permissions du répertoire $data_dir" >&2
    
    # Créer le répertoire s'il n'existe pas
    if ! mkdir -p "$data_dir" 2>/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Impossible de créer le répertoire $data_dir" >&2
        return 1
    fi
    
    # Définir les permissions du répertoire
    chmod 755 "$data_dir" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Impossible de modifier les permissions de $data_dir" >&2
    
    # Tester l'écriture du fichier de log
    if echo "[$(date '+%Y-%m-%d %H:%M:%S')] Test de permissions du répertoire de données" > "$LOG_FILE" 2>/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Test d'écriture réussi dans $LOG_FILE" >&2
        LOG_AVAILABLE=1
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Impossible d'écrire dans $LOG_FILE, utilisation de stdout uniquement" >&2
        LOG_AVAILABLE=0
    fi
    
    # Tester l'accès à la base de données Flower
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Test d'accès à la base de données Flower..." >&2
    
    # Supprimer les anciens fichiers de base s'ils existent avec de mauvaises permissions
    rm -f "${db_file}" "${db_file}.dir" "${db_file}.pag" "${db_file}.bak" "${db_file}.dat" 2>/dev/null || true
    
    # Tester la création d'un fichier de base vide
    if touch "$db_file" 2>/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Création de fichier de base de données réussie" >&2
        
        # Tester l'écriture dans la base
        if echo "test" > "$db_file" 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Écriture dans la base de données réussie" >&2
            rm -f "$db_file"  # Nettoyer le fichier test
            return 0
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Impossible d'écrire dans la base de données $db_file" >&2
            rm -f "$db_file" 2>/dev/null || true
            return 1
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Impossible de créer le fichier de base de données $db_file" >&2
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Vérifiez les permissions du volume flower-data" >&2
        return 1
    fi
}

# Fonction pour démarrer Flower sans base de données persistante
start_flower_without_db() {
    log "WARNING: Démarrage de Flower sans base de données persistante"
    log "INFO: Les données ne seront pas conservées entre les redémarrages"
    
    # Modifier les arguments pour désactiver la persistance
    new_args="$@"
    
    # Remplacer --persistent=True par --persistent=False
    new_args=$(echo "$new_args" | sed 's/--persistent=True/--persistent=False/g')
    
    # Supprimer --db si présent
    new_args=$(echo "$new_args" | sed 's/--db=[^ ]*//g')
    
    log "INFO: Nouveaux arguments Flower: $new_args"
    
    # Exécuter Flower avec les nouveaux arguments
    exec $new_args
}

# Fonction principale de récupération
recover_flower_db() {
    db_file="$1"
    shift # Conserver les autres arguments pour Flower
    
    log "=== DÉBUT DE LA PROCÉDURE DE RÉCUPÉRATION FLOWER AVANCÉE ==="
    
    # Configurer les permissions du répertoire de données
    if ! setup_data_permissions; then
        log "ERROR: Impossible de configurer les permissions, démarrage sans persistance"
        start_flower_without_db "$@"
        return 0  # Ne jamais retourner ici
    fi
    
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
            log "INFO: Tentative de démarrage sans persistance..."
            start_flower_without_db "$@"
            return 0  # Ne jamais retourner ici
        fi
    else
        log "ERROR: Échec de la création de la base de données Flower"
        log "INFO: Tentative de démarrage sans persistance..."
        start_flower_without_db "$@"
        return 0  # Ne jamais retourner ici
    fi
}

# Attendre que Redis soit disponible
wait_for_redis() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Attente de la disponibilité de Redis..." >&2
    timeout=120
    counter=0
    
    while [ $counter -lt $timeout ]; do
        if command -v redis-cli >/dev/null 2>&1; then
            # Test PING Redis
            if redis-cli -h redis -p 6379 ping >/dev/null 2>&1; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Redis répond au PING" >&2
                
                # Attendre que Redis ait fini de charger (INFO command)
                loading_status=$(redis-cli -h redis -p 6379 info | grep "loading:" | cut -d: -f2 | tr -d '\r')
                if [ "$loading_status" = "0" ]; then
                    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Redis a fini de charger les données" >&2
                    return 0
                else
                    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Redis charge encore les données (loading:$loading_status)" >&2
                fi
            fi
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: redis-cli non disponible, test avec Python..." >&2
            # Test avec Python si redis-cli n'est pas disponible
            if python3 -c "
import redis
try:
    r = redis.Redis(host='redis', port=6379, socket_connect_timeout=5)
    r.ping()
    print('Redis OK')
except Exception as e:
    print(f'Redis Error: {e}')
    exit(1)
" 2>/dev/null | grep -q "Redis OK"; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Redis disponible (test Python)" >&2
                return 0
            fi
        fi
        sleep 3
        counter=$((counter + 3))
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Attente Redis... ($counter/$timeout secondes)" >&2
    done
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Timeout d'attente de Redis, continuation quand même" >&2
    return 0
}

# Script principal
main() {
    log "INFO: Démarrage du script d'entrée Flower (version avancée avec structure)"
    
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