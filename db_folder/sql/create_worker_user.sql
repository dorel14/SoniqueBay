DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'taskiq_worker') THEN
        CREATE ROLE taskiq_worker WITH LOGIN PASSWORD 'worker_password';
    END IF;
END
$$;