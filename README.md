# Elastic Open Crawler on Modal.com

A serverless API wrapper for the [Elastic Open Crawler](https://github.com/elastic/crawler), deployed on [Modal.com](https://modal.com). Trigger web crawls via HTTP POST requests with results automatically indexed into Elasticsearch.

## Overview

This service provides a stateless, serverless API for running web crawls using Elastic's official open-source crawler. Elasticsearch credentials are securely managed through Modal Secrets, while crawl configurations (target URLs, rules, extraction settings) are provided dynamically per request.

## Key Features

- **Serverless Architecture** - Automatic scaling, zero infrastructure management
- **API-First Design** - RESTful endpoints for triggering crawls and health checks
- **Secure by Default** - Elasticsearch credentials managed via Modal Secrets
- **Dynamic Configuration** - Different crawl configs per request (URLs, rules, extraction)
- **Official Crawler** - Built on Elastic's open-source crawler with full feature support
- **Production Ready** - 1-hour timeouts, comprehensive error handling, structured logging

## Architecture

The service uses a custom Docker image that combines:
- **Python 3.11** (for Modal runtime)
- **JRuby 9.4.8** (for Elastic crawler)
- **Java 21** (JRuby dependency)
- **Elastic Crawler** (cloned from official repository)

This hybrid approach allows Modal's Python-based infrastructure to orchestrate the JRuby crawler seamlessly.

## Prerequisites

- Python 3.11+
- [Modal.com account](https://modal.com)
- Elasticsearch cluster (Cloud, Serverless, or self-hosted)
- Elasticsearch API key with write permissions

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Authenticate with Modal

```bash
modal setup
```

Or if you have a token:

```bash
modal token set --token-id <your-token-id> --token-secret <your-token-secret>
```

### 3. Create Elasticsearch API Key

Create an API key in Elasticsearch with the following permissions:

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

Save the `encoded` value from the response.

### 4. Configure Modal Secrets

Create a Modal secret with your Elasticsearch credentials:

```bash
modal secret create elasticsearch-config \
  ELASTICSEARCH_HOST=https://your-deployment.es.region.cloud.elastic.cloud:443 \
  ELASTICSEARCH_API_KEY=your_base64_encoded_api_key
```

**Important**:
- `ELASTICSEARCH_HOST` should include the protocol (`https://`) and port (`:443` for cloud, `:9200` for localhost)
- `ELASTICSEARCH_API_KEY` should be the base64-encoded API key from step 3

### 5. Deploy to Modal

```bash
chmod +x deploy.sh
./deploy.sh
```

Or manually:

```bash
modal deploy app.py
```

### 6. Get Endpoint URLs

```bash
modal app show elastic-crawler
```

Your endpoints:
- **Health**: `https://{username}--elastic-crawler-health.modal.run`
- **Crawl**: `https://{username}--elastic-crawler-crawl-endpoint.modal.run`

## Usage

### Health Check

```bash
curl https://your-username--elastic-crawler-health.modal.run
```

Response:
```json
{
  "status": "healthy",
  "service": "elastic-crawler",
  "version": "1.0.0"
}
```

### Trigger a Crawl

```bash
curl -X POST https://your-username--elastic-crawler-crawl-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [
      {
        "url": "https://example.com",
        "seed_urls": ["https://example.com"]
      }
    ],
    "output_index": "my-crawler-index"
  }'
```

### Advanced Crawl Configuration

```bash
curl -X POST https://your-username--elastic-crawler-crawl-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [
      {
        "url": "https://example.com",
        "seed_urls": ["https://example.com/docs"]
      }
    ],
    "output_index": "docs-crawler",
    "crawl_rules": [
      {
        "policy": "allow",
        "type": "regex",
        "pattern": "https://example.com/docs/.*"
      }
    ],
    "max_crawl_depth": 5,
    "max_duration_seconds": 1800
  }'
```

## API Reference

### POST /crawl_endpoint

Trigger a web crawl with custom configuration.

**Required Fields:**
- `domains` - Array of domain objects with `url` and optional `seed_urls`
- `output_index` - Elasticsearch index name for crawled documents

**Optional Fields:**
- `crawl_rules` - URL filtering rules
- `extraction_rules` - Content extraction rules
- `max_crawl_depth` - Maximum link depth
- `max_duration_seconds` - Crawl timeout
- `user_agent` - Custom user agent

**Response:**
```json
{
  "status": "success",
  "return_code": 0,
  "output_index": "my-crawler-index",
  "domains_crawled": ["https://example.com"],
  "stats": {
    "pages_visited": "5",
    "documents_indexed": "5",
    "duration_seconds": "2.3"
  }
}
```

See [Elastic Crawler Config Docs](https://github.com/elastic/crawler/blob/main/docs/CONFIG.md) for all available options.

## Development

**View Logs:**
```bash
modal app logs elastic-crawler
```

**Update Deployment:**
```bash
modal deploy app.py
```

**Update Secrets:**
```bash
modal secret create elasticsearch-config \
  ELASTICSEARCH_HOST=new-host \
  ELASTICSEARCH_API_KEY=new-key
```

## Project Structure

```
├── app.py                # Modal application (FastAPI endpoints + crawler orchestration)
├── Dockerfile.modal      # Custom image (Python + JRuby + Elastic Crawler)
├── requirements.txt      # Python dependencies (modal, pyyaml)
├── example-config.yml    # Sample crawl configuration
└── README.md            # Documentation
```

## Security Considerations

- **Credentials**: Elasticsearch credentials stored exclusively in Modal Secrets
- **API Keys**: Use Elasticsearch API keys (not username/password)
- **Permissions**: Grant minimum required permissions (write to specific indices)
- **Rate Limiting**: Consider adding rate limiting for production workloads
- **Authentication**: Endpoints are public by default; add authentication if needed

**Adding API Authentication:**

```python
@app.function(secrets=[modal.Secret.from_name("elasticsearch-config"),
                       modal.Secret.from_name("api-keys")])
@modal.asgi_app()
def crawl_endpoint():
    from fastapi import FastAPI, Header, HTTPException

    web_app = FastAPI()

    @web_app.post("/")
    async def trigger_crawl(config: CrawlConfig, x_api_key: str = Header(None)):
        if x_api_key != os.environ.get("EXPECTED_API_KEY"):
            raise HTTPException(status_code=401, detail="Unauthorized")
        # ... rest of implementation
```

## Troubleshooting

**Deployment Errors:**
- First deployment takes 3-5 minutes (builds custom image with git clone + bundle install)
- Subsequent deployments use cached image (~2 seconds)
- Modal caches images by content hash

**Connection Issues:**
- Verify `ELASTICSEARCH_HOST` format: `https://hostname:port`
- Confirm API key has `write` and `create_index` permissions
- Test connectivity: `curl -H "Authorization: ApiKey $API_KEY" $ES_HOST`

**Crawl Failures:**
- Check Modal logs: `modal app logs elastic-crawler`
- Verify target URL is accessible
- Review `crawl_rules` for overly restrictive patterns
- Check Elasticsearch index for error messages

## Performance & Costs

- **Cold Start**: ~10-15 seconds (first request after idle period)
- **Warm Requests**: <1 second API response (crawl runs async)
- **Image Build**: 3-5 minutes (first deployment only, cached thereafter)
- **Crawl Duration**: Depends on site size; typically seconds to minutes
- **Modal Costs**: Based on compute time (CPU-seconds) + container memory

## Additional Resources

- **Crawler**: [Elastic Open Crawler Docs](https://github.com/elastic/crawler)
- **Configuration**: [Crawler Config Reference](https://github.com/elastic/crawler/blob/main/docs/CONFIG.md)
- **Platform**: [Modal Documentation](https://modal.com/docs)
- **Elasticsearch**: [API Keys Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html)

## License

This integration is provided as-is. The Elastic Open Crawler is licensed under [Elastic License 2.0](https://github.com/elastic/crawler/blob/main/LICENSE).

## Support

- **Integration Issues**: Open an issue in this repository
- **Crawler Questions**: See [elastic/crawler](https://github.com/elastic/crawler)
- **Modal Platform**: [Modal Docs](https://modal.com/docs) | [Slack Community](https://modal.com/slack)
