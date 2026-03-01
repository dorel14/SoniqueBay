-- Initialisation Supabase pour SoniqueBay
-- Extensions nécessaires et configuration initiale

-- Activer les extensions essentielles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Créer le schéma auth si non existant (pour GoTrue)
CREATE SCHEMA IF NOT EXISTS auth;

-- Créer le schéma realtime si non existant
CREATE SCHEMA IF NOT EXISTS realtime;

-- Configuration pour Realtime
-- Activer la publication pour realtime sur toutes les tables
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        CREATE PUBLICATION supabase_realtime;
    END IF;
END $$;

-- Fonction pour ajouter automatiquement les tables à la publication realtime
CREATE OR REPLACE FUNCTION realtime.add_table_to_publication(table_name text)
RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER PUBLICATION supabase_realtime ADD TABLE %I', table_name);
EXCEPTION
    WHEN duplicate_object THEN
        -- Table déjà dans la publication, ignorer
        NULL;
END;
$$ LANGUAGE plpgsql;

-- Configuration des paramètres pour pgvector
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements, pg_trgm, vector';
ALTER SYSTEM SET pg_trgm.similarity_threshold = 0.3;

-- Créer les rôles Supabase si non existants
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN;
    END IF;
END $$;

-- Accorder les privilèges de base
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;

-- Note : Les tables seront créées par les migrations SQLAlchemy/Alembic existantes
-- ou par les scripts de migration dédiés

-- Configuration pour les recherches textuelles (à activer sur les tables concernées)
-- Exemple : CREATE INDEX idx_tracks_search ON tracks USING gin(to_tsvector('french', title || ' ' || artist));

-- Commentaire : Les politiques RLS (Row Level Security) seront configurées
-- dans les scripts de migration spécifiques à chaque table

-- Fonction utilitaire pour la mise à jour automatique de updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Note : Les triggers seront créés sur chaque table lors de la migration
