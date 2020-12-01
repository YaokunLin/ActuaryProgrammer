-- Create databases
CREATE DATABASE peerlogic;

-- Create users
CREATE USER peerlogic WITH PASSWORD 'password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE peerlogic TO peerlogic;
GRANT ALL PRIVILEGES ON DATABASE peerlogic TO postgres;
