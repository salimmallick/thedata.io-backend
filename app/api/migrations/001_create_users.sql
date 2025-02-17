-- Create user roles enum
CREATE TYPE user_role AS ENUM ('admin', 'operator', 'analyst', 'viewer');

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create user permissions table
CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(255) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, permission, resource)
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create index on user_id and permission for faster permission checks
CREATE INDEX IF NOT EXISTS idx_user_permissions ON user_permissions(user_id, permission);

-- Insert default admin user
-- Password will need to be set via environment variable or changed after creation
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'admin@thedata.io',
    'System Administrator',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYpwBAHHKQS.pmS' -- Default: changeme123
) ON CONFLICT (email) DO NOTHING;

-- Insert basic permissions for admin
INSERT INTO user_permissions (user_id, permission, resource)
VALUES 
    (1, 'admin', '*'),
    (1, 'manage_users', 'users'),
    (1, 'manage_data', 'data'),
    (1, 'view_analytics', 'analytics')
ON CONFLICT DO NOTHING; 