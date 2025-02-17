#!/bin/bash

# Exit on error
set -e

echo "Deploying to staging environment..."

# Build directory
BUILD_DIR="build"

# Staging server details
STAGING_SERVER="staging.thedata.io"
STAGING_USER="deploy"
STAGING_PATH="/var/www/staging.thedata.io"

# Ensure build directory exists
if [ ! -d "$BUILD_DIR" ]; then
    echo "Error: Build directory not found!"
    exit 1
fi

# Compress build
echo "Compressing build files..."
tar -czf build.tar.gz -C $BUILD_DIR .

# Upload to staging server
echo "Uploading to staging server..."
scp build.tar.gz $STAGING_USER@$STAGING_SERVER:/tmp/

# Deploy on staging server
echo "Deploying on staging server..."
ssh $STAGING_USER@$STAGING_SERVER << 'EOF'
    # Create backup of current deployment
    if [ -d "$STAGING_PATH" ]; then
        timestamp=$(date +%Y%m%d_%H%M%S)
        mv $STAGING_PATH $STAGING_PATH_$timestamp.bak
    fi

    # Create new deployment directory
    mkdir -p $STAGING_PATH

    # Extract new build
    tar -xzf /tmp/build.tar.gz -C $STAGING_PATH

    # Clean up
    rm /tmp/build.tar.gz

    # Update permissions
    chown -R www-data:www-data $STAGING_PATH
EOF

# Clean up local files
rm build.tar.gz

echo "Deployment to staging completed successfully!"

# Run smoke tests
echo "Running smoke tests..."
./scripts/smoke-tests.sh staging

# If smoke tests pass, notify team
if [ $? -eq 0 ]; then
    echo "Smoke tests passed. Notifying team..."
    # Add notification logic here (e.g., Slack webhook)
else
    echo "Smoke tests failed! Rolling back deployment..."
    # Add rollback logic here
    exit 1
fi 