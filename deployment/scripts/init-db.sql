-- Yellowstone Database Initialization Script
-- Creates schemas, tables, and security policies

-- Create schemas
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS metrics;
CREATE SCHEMA IF NOT EXISTS queries;
CREATE SCHEMA IF NOT EXISTS security;

-- Audit logging table
CREATE TABLE IF NOT EXISTS audit.audit_logs (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  user_id VARCHAR(255),
  action VARCHAR(50) NOT NULL,
  resource_type VARCHAR(50) NOT NULL,
  resource_id VARCHAR(255),
  details JSONB,
  source_ip INET,
  status VARCHAR(20),
  error_message TEXT,
  duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp
  ON audit.audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user_id
  ON audit.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action
  ON audit.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_status
  ON audit.audit_logs(status);

-- Query execution history table
CREATE TABLE IF NOT EXISTS queries.query_history (
  id BIGSERIAL PRIMARY KEY,
  query_hash VARCHAR(64) NOT NULL UNIQUE,
  original_query TEXT NOT NULL,
  translated_query TEXT,
  execution_time_ms INTEGER,
  result_count INTEGER,
  status VARCHAR(20),
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by VARCHAR(255),
  cache_hit BOOLEAN DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_query_hash
  ON queries.query_history(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_created_at
  ON queries.query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_status
  ON queries.query_history(status);

-- Query performance metrics table
CREATE TABLE IF NOT EXISTS metrics.query_performance (
  id BIGSERIAL PRIMARY KEY,
  query_hash VARCHAR(64) NOT NULL,
  execution_time_ms INTEGER NOT NULL,
  memory_used_mb DECIMAL(10, 2),
  cpu_usage_percent DECIMAL(5, 2),
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_query_hash FOREIGN KEY (query_hash)
    REFERENCES queries.query_history(query_hash)
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_performance_query_hash
  ON metrics.query_performance(query_hash);
CREATE INDEX IF NOT EXISTS idx_performance_timestamp
  ON metrics.query_performance(timestamp DESC);

-- Query cache table
CREATE TABLE IF NOT EXISTS queries.query_cache (
  query_hash VARCHAR(64) PRIMARY KEY,
  cached_result JSONB NOT NULL,
  result_checksum VARCHAR(64),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  last_accessed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  ttl_seconds INTEGER DEFAULT 3600,
  hit_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cache_last_accessed
  ON queries.query_cache(last_accessed DESC);

-- Alert rules table
CREATE TABLE IF NOT EXISTS metrics.alert_rules (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  metric_type VARCHAR(50) NOT NULL,
  threshold DECIMAL(10, 4) NOT NULL,
  comparison_operator VARCHAR(2),
  enabled BOOLEAN DEFAULT true,
  notification_emails TEXT[] DEFAULT ARRAY[]::TEXT[],
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_enabled
  ON metrics.alert_rules(enabled);

-- Security events table
CREATE TABLE IF NOT EXISTS security.security_events (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  event_type VARCHAR(50) NOT NULL,
  severity VARCHAR(20),
  user_id VARCHAR(255),
  ip_address INET,
  description TEXT,
  threat_level VARCHAR(20),
  remediation_action VARCHAR(255),
  resolved BOOLEAN DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_security_timestamp
  ON security.security_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_severity
  ON security.security_events(severity);
CREATE INDEX IF NOT EXISTS idx_security_resolved
  ON security.security_events(resolved);

-- API usage statistics
CREATE TABLE IF NOT EXISTS metrics.api_usage (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  user_id VARCHAR(255),
  endpoint VARCHAR(255),
  method VARCHAR(10),
  status_code INTEGER,
  response_time_ms INTEGER,
  request_size_bytes INTEGER,
  response_size_bytes INTEGER
);

CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp
  ON metrics.api_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_user
  ON metrics.api_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint
  ON metrics.api_usage(endpoint);

-- Data integrity constraints
CREATE TABLE IF NOT EXISTS queries.query_validation (
  id BIGSERIAL PRIMARY KEY,
  query_hash VARCHAR(64) NOT NULL UNIQUE,
  is_valid BOOLEAN NOT NULL,
  validation_errors TEXT,
  validation_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_query_validation FOREIGN KEY (query_hash)
    REFERENCES queries.query_history(query_hash)
    ON DELETE CASCADE
);

-- Views for common queries
CREATE OR REPLACE VIEW audit.recent_actions AS
  SELECT
    timestamp,
    user_id,
    action,
    resource_type,
    status,
    duration_ms
  FROM audit.audit_logs
  ORDER BY timestamp DESC
  LIMIT 1000;

CREATE OR REPLACE VIEW metrics.slow_queries AS
  SELECT
    qh.query_hash,
    qh.original_query,
    COUNT(*) as execution_count,
    AVG(qp.execution_time_ms) as avg_time_ms,
    MAX(qp.execution_time_ms) as max_time_ms,
    MIN(qp.execution_time_ms) as min_time_ms
  FROM queries.query_history qh
  JOIN metrics.query_performance qp ON qh.query_hash = qp.query_hash
  WHERE qp.timestamp > NOW() - INTERVAL '24 hours'
  GROUP BY qh.query_hash, qh.original_query
  HAVING AVG(qp.execution_time_ms) > 1000
  ORDER BY avg_time_ms DESC;

CREATE OR REPLACE VIEW metrics.error_summary AS
  SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    action,
    COUNT(*) as error_count,
    array_agg(DISTINCT error_message) as error_types
  FROM audit.audit_logs
  WHERE status = 'Error'
  GROUP BY DATE_TRUNC('hour', timestamp), action
  ORDER BY hour DESC;

-- Enable Row Level Security (for future implementation)
ALTER TABLE audit.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE queries.query_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE security.security_events ENABLE ROW LEVEL SECURITY;

-- Grant privileges
GRANT USAGE ON SCHEMA audit TO yellowstone;
GRANT USAGE ON SCHEMA metrics TO yellowstone;
GRANT USAGE ON SCHEMA queries TO yellowstone;
GRANT USAGE ON SCHEMA security TO yellowstone;

GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit TO yellowstone;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA metrics TO yellowstone;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA queries TO yellowstone;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA security TO yellowstone;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO yellowstone;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA metrics TO yellowstone;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA queries TO yellowstone;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA security TO yellowstone;

-- Log creation
COMMENT ON SCHEMA audit IS 'Audit logging for compliance and troubleshooting';
COMMENT ON SCHEMA metrics IS 'Performance and usage metrics';
COMMENT ON SCHEMA queries IS 'Query execution history and caching';
COMMENT ON SCHEMA security IS 'Security events and threat tracking';

-- Analyze to update statistics
ANALYZE;

-- Show completion
SELECT 'Database initialization completed successfully' as status;
