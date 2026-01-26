-- Create litellm database and user
CREATE DATABASE litellm;
CREATE USER litellm WITH ENCRYPTED PASSWORD 'litellm';
GRANT ALL PRIVILEGES ON DATABASE litellm TO litellm;

-- Create lobechat database (used by Lobe Chat database version)
CREATE DATABASE lobechat;

-- Create casdoor database (used by Casdoor SSO)
CREATE DATABASE casdoor;

-- Switch to litellm database to grant schema permissions
\c litellm
GRANT ALL ON SCHEMA public TO litellm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO litellm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO litellm;

-- Switch to lobechat database to enable pgvector extension
\c lobechat
CREATE EXTENSION IF NOT EXISTS vector;
