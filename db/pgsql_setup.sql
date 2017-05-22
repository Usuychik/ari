CREATE DATABASE ari;
CREATE USER ari_admin WITH PASSWORD 'xxxxx';
GRANT ALL privileges ON DATABASE ari TO ari_admin;
\c ari
CREATE SEQUENCE ids;
CREATE TYPE TASK_STATUS AS ENUM ('queued','completed','processed');
ALTER TYPE TASK_STATUS ADD VALUE 'failed';

CREATE TABLE tasks (id INTEGER PRIMARY KEY DEFAULT NEXTVAL('ids'),service_task_id CHAR(256) NOT NULL, service CHAR(256) NOT NULL,
  phone CHAR(256) NOT NULL, script JSON NOT NULL, formated_script JSON, task_date TIMESTAMP DEFAULT current_timestamp, record_uri TEXT,
  log_uri TEXT, call_log JSON, script_log JSON, status TASK_STATUS DEFAULT 'queued');
ALTER TABLE tasks ADD COLUMN record_name TEXT;

CREATE TABLE services (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL );
CREATE TABLE keys(service INTEGER REFERENCES services (id) UNIQUE NOT NULL,speechkit_key TEXT);
CREATE TABLE sounds(task INTEGER REFERENCES tasks(id),step INTEGER,file_name TEXT NOT NULL );

CREATE INDEX date_inversed ON tasks (task_date DESC);
CREATE INDEX service_task_id ON tasks (service_task_id, service);
CREATE INDEX task_sound ON sounds (task, step);

CREATE INDEX date_inversed ON tasks (task_date DESC);
CREATE INDEX service_task_id ON tasks (service_task_id, service);
GRANT ALL PRIVILEGES ON TABLE tasks TO ari_admin;
GRANT ALL PRIVILEGES ON TABLE services TO ari_admin;
GRANT ALL PRIVILEGES ON TABLE keys TO ari_admin;
GRANT ALL PRIVILEGES ON TABLE sounds TO ari_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public to ari_admin;


--truncate tables
TRUNCATE services, keys  RESTART IDENTITY CASCADE ;
