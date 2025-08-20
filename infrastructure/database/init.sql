-- AI Code Review Database Schema
-- This script runs automatically when PostgreSQL container starts

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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

-- AI Review Results
CREATE TABLE review_results (
    id SERIAL PRIMARY KEY,
    commit_id INTEGER REFERENCES commits(id) ON DELETE CASCADE,
    overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
    summary TEXT,
    model_used VARCHAR(50) NOT NULL, -- gpt-4, gpt-3.5-turbo, etc.
    tokens_used INTEGER DEFAULT 0,
    processing_time_ms INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, failed, skipped
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(commit_id)
);

-- Individual AI suggestions/issues
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

-- Notifications sent
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    review_result_id INTEGER REFERENCES review_results(id),
    notification_type VARCHAR(50) NOT NULL, -- email, slack, teams
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
    metric_unit VARCHAR(50), -- ms, count, percentage, dollars
    tags JSONB, -- Additional metadata
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User feedback on AI reviews (optional for learning)
CREATE TABLE review_feedback (
    id SERIAL PRIMARY KEY,
    review_result_id INTEGER REFERENCES review_results(id),
    user_email VARCHAR(255) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    is_helpful BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_commits_repo_date ON commits(repository_id, committed_at DESC);
CREATE INDEX idx_commits_hash ON commits(commit_hash);
CREATE INDEX idx_review_results_status ON review_results(status, created_at DESC);
CREATE INDEX idx_suggestions_severity ON review_suggestions(severity, suggestion_type);
CREATE INDEX idx_notifications_status ON notifications(status, created_at);
CREATE INDEX idx_metrics_name_time ON system_metrics(metric_name, recorded_at DESC);
CREATE INDEX idx_commit_files_commit ON commit_files(commit_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to repositories
CREATE TRIGGER update_repositories_updated_at 
    BEFORE UPDATE ON repositories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data for testing
INSERT INTO repositories (name, owner, url, platform) VALUES 
('test-repo', 'testuser', 'https://github.com/testuser/test-repo', 'github');

-- Create Kafka topics (these will be created automatically by Kafka, but good to document)
-- Topics:
-- - code-commits: New commits from webhooks
-- - review-results: AI analysis results
-- - notifications: Alert messages
-- - metrics: System monitoring data

COMMIT;