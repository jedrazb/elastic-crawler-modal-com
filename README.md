# Elastic Open Crawler on Modal.com

Serverless API wrapper for the [Elastic Open Crawler](https://github.com/elastic/crawler). Deploy once, crawl websites via API calls, index results directly into Elasticsearch.

## Why This?

- **No Infrastructure** - Deploy to Modal.com, forget about servers
- **API-First** - Trigger crawls with HTTP POST, integrate anywhere
- **Zero Config Per Crawl** - Elasticsearch credentials set once, crawl configs passed dynamically
- **Uses Official Crawler** - Full Elastic crawler feature set (rules, extraction, depth control)
- **Production Ready** - 1-hour timeouts, auto-scaling, comprehensive error handling

## Quick Start

### 1. Setup Modal

```bash
pip install modal
modal setup
```

### 2. Configure Secrets

**Elasticsearch credentials:**
```bash
modal secret create elasticsearch-config \
  ELASTICSEARCH_HOST=https://your-cluster.es.region.elastic.cloud:443 \
  ELASTICSEARCH_API_KEY=your_base64_encoded_api_key
```

**API authentication (secure your endpoints):**
```bash
# Generate a secure API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Create Modal secret with the key
modal secret create api-keys \
  CRAWLER_API_KEY=your_generated_api_key
```

**Create API Key in Elasticsearch:**
```json
POST /_security/api_key
{
  "name": "crawler-modal-key",
  "role_descriptors": {
    "crawler-role": {
      "indices": [{
        "names": ["*-crawler-*"],
        "privileges": ["write", "create_index"]
      }]
    }
  }
}
```

### 3. Deploy

```bash
modal deploy app.py
```

Get your endpoint URL:
```bash
modal app show elastic-crawler
```

## API Reference

### Trigger a Crawl

```bash
curl -X POST https://{username}--elastic-crawler-crawl-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "domains": [{
      "url": "https://example.com",
      "seed_urls": ["https://example.com/docs"]
    }],
    "output_index": "my-crawler-index"
  }'
```

**Required:**
- `domains` - Array with `url` (required), `seed_urls` (optional)
- `output_index` - Elasticsearch index name

**Optional:**
- `crawl_rules` - URL filtering (allow/deny patterns)
- `extraction_rules` - Content extraction rules
- `max_crawl_depth` - Link depth limit
- `max_duration_seconds` - Timeout
- `user_agent` - Custom user agent

**Response:**
```json
{
  "status": "success",
  "return_code": 0,
  "output_index": "my-crawler-index",
  "domains_crawled": ["https://example.com"],
  "stats": {
    "pages_visited": "15",
    "documents_indexed": "15",
    "duration_seconds": "8.2"
  }
}
```

### Advanced: Crawl Rules

```bash
curl -X POST https://{username}--elastic-crawler-crawl-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "domains": [{
      "url": "https://docs.example.com"
    }],
    "output_index": "docs-crawler",
    "crawl_rules": [{
      "policy": "allow",
      "type": "regex",
      "pattern": "https://docs.example.com/.*"
    }],
    "max_crawl_depth": 5
  }'
```

Full configuration options: [Elastic Crawler Config Docs](https://github.com/elastic/crawler/blob/main/docs/CONFIG.md)

### Health Check

```bash
curl https://{username}--elastic-crawler-health.modal.run
```

## Managing on Modal.com

**View Live Logs:**
```bash
modal app logs elastic-crawler --follow
```

**Update Deployment:**
```bash
modal deploy app.py
```

**Update Credentials:**
```bash
modal secret create elasticsearch-config \
  ELASTICSEARCH_HOST=new-host \
  ELASTICSEARCH_API_KEY=new-key
```

**Check Deployment Status:**
```bash
modal app list
modal app show elastic-crawler
```

**Stop App:**
```bash
modal app stop elastic-crawler
```

## Architecture

Custom Docker image combining:
- **Python 3.11** (Modal runtime)
- **JRuby 9.4.8** (Elastic crawler)
- **Java 21** (JRuby dependency)

First deployment takes 3-5 minutes (builds image + clones crawler repo). Subsequent deployments use cached image (~2 seconds).

## Security

- ✅ **API Key Authentication** - Endpoints protected with `X-API-Key` header
- ✅ **Elasticsearch Credentials** - Stored in Modal Secrets (never in code)
- ✅ **Sanitized Responses** - No credentials or verbose logs leaked
- ✅ **Secure Transport** - All traffic over HTTPS

**How It Works:**
1. Generate a secure API key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Store it in Modal: `modal secret create api-keys CRAWLER_API_KEY=your_key`
3. Include `X-API-Key` header in all requests
4. Requests without valid API key receive 401/403 errors

**From Your Server:**
```python
import requests

response = requests.post(
    "https://{username}--elastic-crawler-crawl-endpoint.modal.run",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "your_api_key"
    },
    json={
        "domains": [{"url": "https://example.com"}],
        "output_index": "my-index"
    }
)
```

## Troubleshooting

**Connection Issues:**
```bash
# Test Elasticsearch connectivity
curl -H "Authorization: ApiKey YOUR_KEY" https://your-cluster.es.cloud:443

# Check Modal logs
modal app logs elastic-crawler
```

**Slow Deployment:**
- First deploy: 3-5 minutes (normal - building custom image)
- Subsequent deploys: 2-10 seconds (uses cache)

**Crawl Failures:**
- Verify target URL is accessible
- Check `crawl_rules` aren't too restrictive
- Review logs: `modal app logs elastic-crawler`
- Verify API key has `write` + `create_index` permissions

## Performance & Costs

- **Cold Start**: ~10-15 seconds (after idle period)
- **Warm Latency**: <1 second API response
- **Crawl Duration**: Seconds to minutes (depends on site size)
- **Modal Costs**: Pay only for compute time (CPU-seconds + memory)

## Resources

- [Elastic Crawler Docs](https://github.com/elastic/crawler)
- [Crawler Config Reference](https://github.com/elastic/crawler/blob/main/docs/CONFIG.md)
- [Modal Documentation](https://modal.com/docs)

## License

This integration is provided as-is. Elastic Open Crawler is licensed under [Elastic License 2.0](https://github.com/elastic/crawler/blob/main/LICENSE).
