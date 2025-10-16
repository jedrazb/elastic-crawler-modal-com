"""
Elastic Open Crawler Service on Modal.com

This service runs the Elastic Open Crawler as an API-invoked service.
Elasticsearch configuration is handled via environment variables (Modal Secrets),
while crawl configurations are provided via API request payload.
"""

import modal
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Create Modal app
app = modal.App("elastic-crawler")

# Use the official Elastic crawler Docker image
crawler_image = modal.Image.from_registry(
    "docker.elastic.co/integrations/crawler:latest",
    add_python="3.11",  # Add Python for our API handler
).pip_install("pyyaml")


# Define the crawler function
@app.function(
    image=crawler_image,
    secrets=[modal.Secret.from_name("elasticsearch-config")],
    timeout=3600,  # 1 hour timeout for long crawls
    memory=2048,  # 2GB memory
    cpu=2.0,  # 2 CPUs
)
def run_crawler(crawl_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Elastic crawler with the provided configuration.

    Args:
        crawl_config: Dictionary containing the crawl configuration
                     (domains, output_index, etc.)

    Returns:
        Dictionary with crawl results and status
    """
    import subprocess
    import yaml

    # Get Elasticsearch config from environment variables
    es_host = os.environ.get("ELASTICSEARCH_HOST")
    es_api_key = os.environ.get("ELASTICSEARCH_API_KEY")

    if not es_host or not es_api_key:
        return {
            "status": "error",
            "message": "Elasticsearch configuration not found in environment variables",
        }

    # Merge Elasticsearch config into crawl config
    full_config = {
        **crawl_config,
        "output_sink": "elasticsearch",
        "elasticsearch": {
            "host": es_host,
            "api_key": es_api_key,
            "pipeline_enabled": False,
        },
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False, dir="/tmp"
    ) as config_file:
        yaml.dump(full_config, config_file)
        config_path = config_file.name

    try:
        # Run the crawler
        result = subprocess.run(
            ["jruby", "bin/crawler", "crawl", config_path],
            cwd="/home/app",
            capture_output=True,
            text=True,
            timeout=3300,  # 55 minutes (less than function timeout)
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "config_used": full_config,
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Crawler execution timed out"}
    except Exception as e:
        return {"status": "error", "message": f"Error running crawler: {str(e)}"}
    finally:
        # Clean up temporary config file
        if os.path.exists(config_path):
            os.unlink(config_path)


# Define the web endpoint
@app.function(
    secrets=[modal.Secret.from_name("elasticsearch-config")],
)
@modal.web_endpoint(method="POST")
def crawl_endpoint(crawl_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Web endpoint to trigger a crawl.

    POST payload should include:
    {
        "domains": [
            {
                "url": "https://example.com",
                "seed_urls": ["https://example.com/page1"]
            }
        ],
        "output_index": "my-crawler-index",
        "crawl_rules": [...],  // optional
        "extraction_rules": [...],  // optional
        ... other crawler config options
    }

    Returns:
        Dictionary with crawl results
    """
    # Validate required fields
    if "domains" not in crawl_config:
        return {"status": "error", "message": "Missing required field: domains"}

    if "output_index" not in crawl_config:
        return {"status": "error", "message": "Missing required field: output_index"}

    # Run the crawler asynchronously
    result = run_crawler.remote(crawl_config)

    return result


# Health check endpoint
@app.function()
@modal.web_endpoint(method="GET")
def health() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "elastic-crawler", "version": "1.0.0"}


# CLI for local testing
@app.local_entrypoint()
def main(config_file: Optional[str] = None):
    """
    Local entrypoint for testing.

    Usage:
        modal run app.py --config-file example-config.yml
    """
    import yaml

    if config_file and os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        print(f"Running crawler with config from {config_file}")
        result = run_crawler.remote(config)
        print(f"\nCrawl result:")
        print(f"Status: {result['status']}")
        if result["status"] == "success":
            print(f"Return code: {result['return_code']}")
            print(f"\nOutput (last 1000 chars):\n{result['stdout'][-1000:]}")
        else:
            print(f"Error: {result.get('message', 'Unknown error')}")
            if "stderr" in result:
                print(f"\nError output:\n{result['stderr']}")
    else:
        print("Testing crawler service...")
        print("Please provide a config file with --config-file")
        print("\nExample:")
        print("  modal run app.py --config-file example-config.yml")
