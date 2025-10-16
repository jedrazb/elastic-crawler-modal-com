# Quick Start Guide

Get your Elastic Crawler API running on Modal.com in 5 minutes.

## Prerequisites

- Python 3.11+
- Modal.com account (sign up at https://modal.com)
- Elasticsearch instance with API key

## Step-by-Step Setup

### 1. Install Modal

```bash
pip install modal
```

### 2. Authenticate

```bash
modal setup
```

Follow the prompts to authenticate with your Modal account.

### 3. Create Elasticsearch API Key

In your Elasticsearch cluster (Dev Tools Console):

```json
POST /_security/api_key
{
  "name": "crawler-modal-key",
  "role_descriptors": {
    "crawler-role": {
      "cluster": ["monitor"],
      "indices": [
        {
          "names": ["web-crawl-*", "*-crawler-*"],
          "privileges": ["write", "create_index", "monitor"]
        }
      ]
    }
  }
}
```

Copy the `encoded` value from the response.

### 4. Configure Secrets

Replace the values below with your actual credentials:

```bash
modal secret create elasticsearch-config \
  ELASTICSEARCH_HOST=https://your-deployment.es.us-central1.gcp.elastic.cloud:443 \
  ELASTICSEARCH_API_KEY=your_base64_encoded_key_here
```

### 5. Deploy

```bash
modal deploy app.py
```

### 6. Get Your Endpoints

```bash
modal app show elastic-crawler
```

You'll see URLs like:
- Health: `https://username--elastic-crawler-health.modal.run`
- Crawl: `https://username--elastic-crawler-crawl-endpoint.modal.run`

### 7. Test Your API

Health check:
```bash
curl https://username--elastic-crawler-health.modal.run
```

Trigger a crawl:
```bash
curl -X POST https://username--elastic-crawler-crawl-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{"url": "https://example.com"}],
    "output_index": "test-crawler"
  }'
```

## Your First Real Crawl

Using your querybox example:

```bash
curl -X POST https://username--elastic-crawler-crawl-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [
      {
        "url": "https://querybox-app.vercel.app",
        "seed_urls": ["https://querybox-app.vercel.app"]
      }
    ],
    "output_index": "querybox-crawler-querybox-app_vercel_app"
  }'
```

## View Results in Elasticsearch

```bash
# Using curl with your API key
curl -X GET "https://your-deployment.es.region.cloud.elastic.cloud:443/querybox-crawler-querybox-app_vercel_app/_search" \
  -H "Authorization: ApiKey your_api_key" \
  -H "Content-Type: application/json"

# Or in Dev Tools Console
GET /querybox-crawler-querybox-app_vercel_app/_search
```

## Troubleshooting

**"Secret not found"**
```bash
modal secret list  # Check if elasticsearch-config exists
```

**"Connection refused"**
- Verify your ELASTICSEARCH_HOST includes `https://` and port `:443`
- Check your API key has correct permissions

**"Timeout"**
- Large sites may take longer than expected
- Add `"max_duration_seconds": 600` to your config

## Next Steps

- Read the full [README.md](./README.md) for advanced features
- Check [example-config.yml](./example-config.yml) for configuration options
- Explore the [Elastic Crawler docs](https://github.com/elastic/crawler/tree/main/docs)
