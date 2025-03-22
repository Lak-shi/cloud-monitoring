#!/bin/bash
# Script to initialize directory structure for the cloud monitoring system

# Create main directories
mkdir -p data
mkdir -p models
mkdir -p static

# Create service-specific model directories
mkdir -p models/api-gateway
mkdir -p models/auth-service
mkdir -p models/database
mkdir -p models/storage-service
mkdir -p models/compute-engine

# Create README files
cat > data/README.md << EOL
# Data Directory

This directory stores metrics data, anomalies, and remediation history.

## File Types

- \`metrics_*.csv\`: CSV files containing historical metrics data
- \`anomalies_*.json\`: JSON files containing detected anomalies
- \`remediation_*.json\`: JSON files containing remediation actions
- \`export_*.csv\`: Exported data for analysis

Data files are automatically generated and managed by the system.
EOL

cat > models/README.md << EOL
# Models Directory

This directory stores trained machine learning models.

## Structure

- \`<service_name>/\`: Subdirectory for each service
  - \`<metric_name>_model.pkl\`: Trained model for specific metric

Models are automatically generated and versioned by the system.
EOL

cat > static/README.md << EOL
# Static Assets Directory

This directory stores static assets for the dashboard.

## Contents

- \`*.png\`: Visualization images
- \`*.css\`: Style sheets
- \`*.js\`: JavaScript files

These files are automatically generated and updated by the system.
EOL

# Create placeholder files in each directory
touch data/.gitkeep
touch models/.gitkeep
touch static/.gitkeep

for service in api-gateway auth-service database storage-service compute-engine; do
  echo "This directory will store trained models for ${service}." > models/${service}/placeholder.txt
  echo "Actual model files will be generated when the system runs." >> models/${service}/placeholder.txt
done

echo "Directory structure initialized successfully!"