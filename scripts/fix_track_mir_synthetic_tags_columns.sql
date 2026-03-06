-- Script SQL pour ajouter les colonnes manquantes à track_mir_synthetic_tags
-- Exécuter avec: docker-compose exec db psql -U soniquebay -d soniquebay -f /tmp/fix_columns.sql

-- Ajout de la colonne date_added si elle n'existe pas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'track_mir_synthetic_tags' 
        AND column_name = 'date_added'
    ) THEN
        ALTER TABLE track_mir_synthetic_tags ADD COLUMN date_added TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        RAISE NOTICE 'Colonne date_added ajoutée';
    ELSE
        RAISE NOTICE 'Colonne date_added existe déjà';
    END IF;
END $$;

-- Ajout de la colonne date_modified si elle n'existe pas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'track_mir_synthetic_tags' 
        AND column_name = 'date_modified'
    ) THEN
        ALTER TABLE track_mir_synthetic_tags ADD COLUMN date_modified TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        RAISE NOTICE 'Colonne date_modified ajoutée';
    ELSE
        RAISE NOTICE 'Colonne date_modified existe déjà';
    END IF;
END $$;

-- Vérification finale
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'track_mir_synthetic_tags' 
AND column_name IN ('date_added', 'date_modified');
