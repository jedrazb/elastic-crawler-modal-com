#!/bin/bash
set -e

echo "🚀 Deploying Elastic Crawler to Modal..."
echo

# Check if modal is installed
if ! command -v modal &> /dev/null; then
    echo "❌ Modal CLI is not installed."
    echo "Install it with: pip install modal"
    exit 1
fi

# Check if user is authenticated
if ! modal token verify &> /dev/null; then
    echo "❌ Not authenticated with Modal."
    echo "Run: modal token set --token-id <your-token-id> --token-secret <your-token-secret>"
    echo "Or: modal setup"
    exit 1
fi

echo "✅ Modal CLI is ready"
echo

# Check if elasticsearch-config secret exists
echo "🔍 Checking for Elasticsearch secrets..."
if ! modal secret list | grep -q "elasticsearch-config"; then
    echo
    echo "⚠️  Secret 'elasticsearch-config' not found!"
    echo
    echo "Please create it with:"
    echo "  modal secret create elasticsearch-config \\"
    echo "    ELASTICSEARCH_HOST=your-host \\"
    echo "    ELASTICSEARCH_API_KEY=your-api-key"
    echo
    echo "Example:"
    echo "  modal secret create elasticsearch-config \\"
    echo "    ELASTICSEARCH_HOST=https://your-deployment.es.region.cloud.elastic.cloud:443 \\"
    echo "    ELASTICSEARCH_API_KEY=your_base64_encoded_key"
    exit 1
fi

echo "✅ Elasticsearch secrets found"
echo

# Deploy the app
echo "📦 Deploying app to Modal..."
modal deploy app.py

echo
echo "✅ Deployment complete!"
echo
echo "🔗 View your app:"
echo "   modal app show elastic-crawler"
echo
echo "🧪 Test your endpoints:"
echo "   Get endpoint URL: modal app show elastic-crawler"
echo "   Health check: curl https://your-username--elastic-crawler-health.modal.run"
echo
