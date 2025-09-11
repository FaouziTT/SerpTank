-- Database initialization script for Voltex SEO Decision Superiority Engine
-- This script sets up the initial database structure

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create crawls table for storing crawl data
CREATE TABLE IF NOT EXISTS crawls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    crawl_javascript BOOLEAN DEFAULT TRUE,
    max_pages INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create crawl_urls table for storing individual crawled URLs
CREATE TABLE IF NOT EXISTS crawl_urls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawl_id UUID REFERENCES crawls(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    status_code INTEGER,
    response_time FLOAT,
    content_length INTEGER,
    title VARCHAR(500),
    meta_description TEXT,
    h1_tags TEXT[],
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_crawls_user_id ON crawls(user_id);
CREATE INDEX IF NOT EXISTS idx_crawls_status ON crawls(status);
CREATE INDEX IF NOT EXISTS idx_crawl_urls_crawl_id ON crawl_urls(crawl_id);
CREATE INDEX IF NOT EXISTS idx_crawl_urls_status_code ON crawl_urls(status_code);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_crawls_updated_at ON crawls;
CREATE TRIGGER update_crawls_updated_at BEFORE UPDATE ON crawls FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
