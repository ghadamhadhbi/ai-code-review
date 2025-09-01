-- AI Code Review Database Schema - Phase 1 (Manual Upload MVP)
-- This script runs automatically when PostgreSQL container starts

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- PHASE 1 TABLES - Manual Upload MVP
-- =====================================================

-- Manual file uploads (replaces commits table for Phase 1)
CREATE TABLE uploads (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    author_email VARCHAR(255),
    description TEXT,
    language VARCHAR(50), -- Primary programming language
    file_count INTEGER NOT NULL DEFAULT 0,
    total_size_bytes BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded', -- uploaded, processing, completed, failed, cancelled
    progress INTEGER DEFAULT 0, -- 0-100 processing progress
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Files in manual uploads
CREATE TABLE upload_files (
    id SERIAL PRIMARY KEY,
    upload_id VARCHAR(36) REFERENCES uploads(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(1000) NOT NULL, -- Temporary file path
    file_type VARCHAR(50), -- .py, .js, .java, etc.
    size_bytes INTEGER NOT NULL,
    content_type VARCHAR(100),
    detected_language VARCHAR(50), -- Auto-detected programming language
    content_preview TEXT, -- First few lines for display
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Review Results (same structure, but references uploads instead of commits)
CREATE TABLE review_results (
    id SERIAL PRIMARY KEY,
    upload_id VARCHAR(36) REFERENCES uploads(id) ON DELETE CASCADE,
    overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
    summary TEXT,
    model_used VARCHAR(50) NOT NULL, -- gpt-4o-mini, gpt-4, etc.
    tokens_used INTEGER DEFAULT 0,
    processing_time_ms INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, failed, skipped
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(upload_id)
);

-- Individual AI suggestions/issues (same structure)
CREATE TABLE review_suggestions (
    id SERIAL PRIMARY KEY,
    review_result_id INTEGER REFERENCES review_results(id) ON DELETE CASCADE,
    file_path VARCHAR(1000) NOT NULL,
    line_number INTEGER,
    suggestion_type VARCHAR(50) NOT NULL, -- bug, performance, style, security, best_practice
    severity VARCHAR(20) NOT NULL, -- low, medium, high, critical
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    suggested_fix TEXT,
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications sent (simplified for email-only)
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    review_result_id INTEGER REFERENCES review_results(id),
    notification_type VARCHAR(50) NOT NULL DEFAULT 'email', -- email only for Phase 1
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed
    sent_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System metrics for monitoring
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,2) NOT NULL,
    metric_unit VARCHAR(50), -- ms, count, percentage, tokens
    tags JSONB, -- Additional metadata
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User feedback on AI reviews (for improving prompts)
CREATE TABLE review_feedback (
    id SERIAL PRIMARY KEY,
    review_result_id INTEGER REFERENCES review_results(id),
    user_email VARCHAR(255) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    is_helpful BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PHASE 2 TABLES - Future Git Integration (Commented Out)
-- =====================================================

-- Uncomment these tables when implementing Phase 2
/*
-- Repositories table
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    webhook_secret VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(owner, name, platform)
);

-- Commits table
CREATE TABLE commits (
    id SERIAL PRIMARY KEY,
    commit_hash VARCHAR(40) NOT NULL UNIQUE,
    repository_id INTEGER REFERENCES repositories(id),
    author_name VARCHAR(255) NOT NULL,
    author_email VARCHAR(255) NOT NULL,
    commit_message TEXT NOT NULL,
    branch_name VARCHAR(255) NOT NULL,
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    commit_url VARCHAR(500),
    committed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Files changed in commits
CREATE TABLE commit_files (
    id SERIAL PRIMARY KEY,
    commit_id INTEGER REFERENCES commits(id) ON DELETE CASCADE,
    file_path VARCHAR(1000) NOT NULL,
    file_type VARCHAR(50), -- .py, .js, .java, etc.
    status VARCHAR(20) NOT NULL, -- added, modified, deleted, renamed
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    diff_content TEXT, -- Store the actual diff
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
*/

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Phase 1 indexes
CREATE INDEX idx_uploads_status_date ON uploads(status, created_at DESC);
CREATE INDEX idx_uploads_author ON uploads(author_email, created_at DESC);
CREATE INDEX idx_upload_files_upload ON upload_files(upload_id);
CREATE INDEX idx_review_results_status ON review_results(status, created_at DESC);
CREATE INDEX idx_review_results_upload ON review_results(upload_id);
CREATE INDEX idx_suggestions_severity ON review_suggestions(severity, suggestion_type);
CREATE INDEX idx_suggestions_review ON review_suggestions(review_result_id);
CREATE INDEX idx_notifications_status ON notifications(status, created_at);
CREATE INDEX idx_metrics_name_time ON system_metrics(metric_name, recorded_at DESC);

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to uploads
CREATE TRIGGER update_uploads_updated_at 
    BEFORE UPDATE ON uploads 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE DATA FOR TESTING
-- =====================================================

-- Sample upload for testing
INSERT INTO uploads (id, author_email, description, language, file_count, total_size_bytes, status) 
VALUES 
    ('test-upload-123', 'developer@example.com', 'Test code review', 'python', 2, 1024, 'completed');

-- Sample upload files
INSERT INTO upload_files (upload_id, filename, filepath, file_type, size_bytes, detected_language)
VALUES 
    ('test-upload-123', 'main.py', '/tmp/uploads/test-upload-123/main.py', '.py', 512, 'python'),
    ('test-upload-123', 'utils.py', '/tmp/uploads/test-upload-123/utils.py', '.py', 512, 'python');

-- Sample review result
INSERT INTO review_results (upload_id, overall_score, summary, model_used, tokens_used, status)
VALUES 
    ('test-upload-123', 85, 'Good code quality with minor style improvements needed', 'gpt-4o-mini', 150, 'completed');

-- =====================================================
-- KAFKA TOPICS DOCUMENTATION
-- =====================================================

-- These topics will be auto-created by Kafka:
-- - code-uploads: Manual file upload events (Phase 1)
-- - review-results: AI analysis results  
-- - notifications: Email alert messages
-- - metrics: System monitoring data

-- Future topics (Phase 2):
-- - code-commits: Git webhook events
-- - git-events: Repository events

COMMIT;