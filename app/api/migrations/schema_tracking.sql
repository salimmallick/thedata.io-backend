-- Create schema changes tracking table
CREATE TABLE IF NOT EXISTS schema_changes_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255),
    change_type VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    details TEXT
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_schema_changes_log_table ON schema_changes_log(table_name);
CREATE INDEX IF NOT EXISTS idx_schema_changes_log_created_at ON schema_changes_log(created_at);

-- Create function to track schema changes
CREATE OR REPLACE FUNCTION track_schema_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO schema_changes_log (
        table_name,
        column_name,
        change_type,
        old_value,
        new_value,
        created_by,
        details
    ) VALUES (
        TG_TABLE_NAME,
        TG_ARGV[0],
        TG_ARGV[1],
        CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD)::jsonb ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb ELSE NULL END,
        current_user,
        TG_ARGV[2]
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create view for schema change statistics
CREATE OR REPLACE VIEW schema_change_stats AS
SELECT 
    table_name,
    change_type,
    COUNT(*) as change_count,
    MIN(created_at) as first_change,
    MAX(created_at) as last_change
FROM schema_changes_log
GROUP BY table_name, change_type; 