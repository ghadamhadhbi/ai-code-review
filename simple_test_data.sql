-- fixed_test_data.sql
-- Clear any existing test data
DELETE FROM review_suggestions;
DELETE FROM review_results;
DELETE FROM upload_files;
DELETE FROM uploads;

-- Insert test uploads
INSERT INTO uploads (id, author_email, description, language, file_count, total_size_bytes, status, created_at, updated_at) 
VALUES 
('test-upload-1', 'alice@example.com', 'Python web application', 'python', 3, 3072, 'completed', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),
('test-upload-2', 'bob@example.com', 'React component library', 'javascript', 5, 5120, 'completed', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day');

-- Insert review results and get their IDs
INSERT INTO review_results (upload_id, overall_score, summary, model_used, tokens_used, processing_time_ms, status, created_at, completed_at) 
VALUES 
('test-upload-1', 88, 'Well-structured Python application with good separation of concerns', 'llama-3.1-70b-versatile', 3200, 15000, 'completed', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),
('test-upload-2', 92, 'Excellent React components with proper TypeScript support', 'llama-3.1-70b-versatile', 2800, 12000, 'completed', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day');

-- Insert suggestions using the actual review result IDs
INSERT INTO review_suggestions (review_result_id, file_path, line_number, suggestion_type, severity, title, description) 
SELECT id, 'app.py', 5, 'security', 'medium', 'Add CORS middleware', 'Missing CORS configuration for web application'
FROM review_results WHERE upload_id = 'test-upload-1';

INSERT INTO review_suggestions (review_result_id, file_path, line_number, suggestion_type, severity, title, description) 
SELECT id, 'models.py', 8, 'best_practice', 'low', 'Add type hints', 'Python classes should have type annotations'
FROM review_results WHERE upload_id = 'test-upload-1';

INSERT INTO review_suggestions (review_result_id, file_path, line_number, suggestion_type, severity, title, description) 
SELECT id, 'Button.jsx', 15, 'accessibility', 'high', 'Add aria-label', 'Buttons should have proper accessibility labels'
FROM review_results WHERE upload_id = 'test-upload-2';

SELECT 'Test data inserted successfully!' as result;