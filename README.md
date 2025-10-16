# Elastic Open Crawler on Modal.com

Run the [Elastic Open Crawler](https://github.com/elastic/crawler) as a serverless API service on [Modal.com](https://modal.com).

This service allows you to trigger web crawls via API, with results automatically indexed into Elasticsearch. Elasticsearch configuration is managed via environment variables (Modal Secrets), while crawl configurations are provided dynamically via API requests.

## 🌟 Features

- **API-driven crawling**: Trigger crawls via HTTP POST requests
- **Serverless deployment**: Runs on Modal.com with automatic scaling
- **Secure configuration**: Elasticsearch credentials stored as Modal Secrets
- **Flexible crawl configs**: Each API call can crawl different websites with custom configurations
- **Official Elastic crawler**: Uses the official `docker.elastic.co/integrations/crawler` image
- **Production-ready**: Includes health checks, error handling, and timeout management

## 📋 Prerequisites

- Python 3.11+
- [Modal.com account](https://modal.com) (free tier available)
- Elasticsearch instance (Elastic Cloud, Serverless, or self-hosted)
- Elasticsearch API key with appropriate permissions

## 🚀 Quick Start

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

### 6. Get Your Endpoint URLs

```bash
modal app show elastic-crawler
```

This will show your deployed endpoints:
- Health check: `https://your-username--elastic-crawler-health.modal.run`
- Crawl endpoint: `https://your-username--elastic-crawler-crawl-endpoint.modal.run`

## 🔧 Usage

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

### Using the Test Script

```bash
python test_api.py https://your-username--elastic-crawler-crawl-endpoint.modal.run
```

## 📝 Configuration Options

The crawl configuration accepts all options from the [Elastic Crawler configuration](https://github.com/elastic/crawler/blob/main/docs/CONFIG.md). Key options include:

### Required Fields

- `domains`: List of domain configurations
  - `url`: The base URL to crawl (required)
  - `seed_urls`: List of starting URLs (optional, defaults to domain URL)
- `output_index`: Elasticsearch index name for storing crawled documents

### Optional Fields

- `crawl_rules`: Rules to control which URLs are crawled
- `extraction_rules`: Rules to extract specific content from pages
- `max_crawl_depth`: Maximum depth to crawl (default: unlimited)
- `max_duration_seconds`: Maximum crawl duration
- `max_url_length`: Maximum URL length to crawl
- `user_agent`: Custom user agent string
- `http_auth`: HTTP authentication credentials

See [example-config.yml](./example-config.yml) for a complete example.

## 🛠️ Development

### Local Testing

Test your configuration locally before deploying:

```bash
modal run app.py --config-file example-config.yml
```

### View Logs

```bash
modal app logs elastic-crawler
```

### Update Deployment

After making changes to `app.py`:

```bash
modal deploy app.py
```

## 📚 Project Structure

```
.
├── app.py                 # Main Modal application
├── requirements.txt       # Python dependencies
├── example-config.yml     # Example crawl configuration
├── env-template          # Template for environment variables
├── deploy.sh             # Deployment script
├── test_api.py           # API testing script
└── README.md             # This file
```

## 🔐 Security Best Practices

1. **Never commit credentials**: Keep your Elasticsearch credentials in Modal Secrets only
2. **Use API keys**: Don't use username/password authentication
3. **Limit permissions**: Grant only necessary permissions to your API key
4. **Rate limiting**: Consider adding rate limiting to your API endpoint
5. **Authentication**: Add authentication to your Modal endpoints in production

### Adding Authentication

To add authentication to your endpoints, modify `app.py`:

```python
from modal import Secret

@app.function(
    secrets=[
        modal.Secret.from_name("elasticsearch-config"),
        modal.Secret.from_name("api-keys")  # Add your API keys
    ]
)
@modal.web_endpoint(method="POST")
def crawl_endpoint(crawl_config: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    # Verify API key
    api_key = headers.get("x-api-key")
    if api_key != os.environ.get("EXPECTED_API_KEY"):
        return {"status": "error", "message": "Unauthorized"}, 401

    # ... rest of the code
```

## 🐛 Troubleshooting

### Secret not found error

```bash
# List your secrets
modal secret list

# Create the secret if missing
modal secret create elasticsearch-config \
  ELASTICSEARCH_HOST=your-host \
  ELASTICSEARCH_API_KEY=your-key
```

### Connection refused to Elasticsearch

- Verify your `ELASTICSEARCH_HOST` includes protocol and port
- Check that your API key has the correct permissions
- Ensure your Elasticsearch instance is accessible from Modal's infrastructure

### Timeout errors

- Increase the timeout in `app.py` (default: 3600 seconds)
- Use `max_duration_seconds` in your crawl config to limit crawl time
- Consider crawling in smaller batches

### Container build errors

- Modal will automatically pull the latest crawler image
- If you see cache issues, try: `modal app build elastic-crawler --force-build`

## 📖 Additional Resources

- [Elastic Open Crawler Documentation](https://github.com/elastic/crawler)
- [Elastic Crawler Configuration Guide](https://github.com/elastic/crawler/blob/main/docs/CONFIG.md)
- [Modal.com Documentation](https://modal.com/docs)
- [Elasticsearch API Keys](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project follows the same license as the Elastic Open Crawler.

## 💬 Support

For issues related to:
- **This Modal integration**: Open an issue in this repository
- **Elastic Open Crawler**: See the [Elastic Crawler repository](https://github.com/elastic/crawler)
- **Modal.com platform**: Check [Modal documentation](https://modal.com/docs) or their [Slack community](https://modal.com/slack)
