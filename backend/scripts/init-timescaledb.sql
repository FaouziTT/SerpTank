-- TimescaleDB initialization script for Voltex SEO Decision Superiority Engine
-- This script sets up time-series tables for performance monitoring

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create performance metrics table for time-series data
CREATE TABLE IF NOT EXISTS performance_metrics (
    time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    site_id UUID NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value FLOAT NOT NULL,
    page_url VARCHAR(500),
    user_agent VARCHAR(200),
    device_type VARCHAR(50),
    location VARCHAR(100)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('performance_metrics', 'time', if_not_exists => TRUE);

-- Create Core Web Vitals metrics table
CREATE TABLE IF NOT EXISTS core_web_vitals (
    time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    site_id UUID NOT NULL,
    page_url VARCHAR(500) NOT NULL,
    lcp FLOAT, -- Largest Contentful Paint
    fid FLOAT, -- First Input Delay
    cls FLOAT, -- Cumulative Layout Shift
    fcp FLOAT, -- First Contentful Paint
    ttfb FLOAT, -- Time to First Byte
    device_type VARCHAR(50),
    connection_type VARCHAR(50)
);

-- Convert to hypertable
SELECT create_hypertable('core_web_vitals', 'time', if_not_exists => TRUE);

-- Create SEO metrics table
CREATE TABLE IF NOT EXISTS seo_metrics (
    time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    site_id UUID NOT NULL,
    page_url VARCHAR(500) NOT NULL,
    organic_traffic INTEGER,
    keyword_rankings JSONB,
    backlinks_count INTEGER,
    domain_authority FLOAT,
    page_authority FLOAT,
    crawl_errors INTEGER
);

-- Convert to hypertable
SELECT create_hypertable('seo_metrics', 'time', if_not_exists => TRUE);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_performance_metrics_site_id_time ON performance_metrics (site_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_metric_type ON performance_metrics (metric_type);
CREATE INDEX IF NOT EXISTS idx_core_web_vitals_site_id_time ON core_web_vitals (site_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_seo_metrics_site_id_time ON seo_metrics (site_id, time DESC);

-- Create retention policies (optional - keeps data for 1 year)
SELECT add_retention_policy('performance_metrics', INTERVAL '1 year');
SELECT add_retention_policy('core_web_vitals', INTERVAL '1 year');
SELECT add_retention_policy('seo_metrics', INTERVAL '1 year');
