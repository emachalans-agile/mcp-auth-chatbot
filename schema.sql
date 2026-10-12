CREATE DATABASE chatbot_db;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO users (email, name, role) VALUES
('alice@example.com', 'Alice', 'admin'),
('bob@example.com', 'Bob', 'user');


-- psql -U postgres -d chatbot_db -f schema.sql

-- python -m http.server 5500

-- uvicorn main:app --reload --port 8000