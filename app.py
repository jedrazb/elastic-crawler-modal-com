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

# Image for the crawler - use custom Dockerfile with Python installed
# This builds from the standard (non-Wolfi) crawler image which is Ubuntu-based
crawler_image = modal.Image.from_dockerfile("Dockerfile.modal")

# Separate image for web endpoints
web_image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi[standard]",
    "pyyaml",
)


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
        },
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False, dir="/tmp"
    ) as config_file:
        yaml.dump(full_config, config_file)
        config_path = config_file.name

    try:
        # Run the crawler (it's in /crawler)
        result = subprocess.run(
            ["jruby", "bin/crawler", "crawl", config_path],
            cwd="/crawler",
            capture_output=True,
            text=True,
            timeout=3300,  # 55 minutes (less than function timeout)
        )

        # Extract crawl statistics from stdout for user feedback
        crawl_stats = {}
        if result.stdout:
            # Parse basic stats from the output
            for line in result.stdout.split("\n"):
                if "Pages visited:" in line:
                    crawl_stats["pages_visited"] = line.split(":")[-1].strip()
                elif "Documents upserted:" in line:
                    crawl_stats["documents_indexed"] = line.split(":")[-1].strip()
                elif "Crawl duration" in line:
                    crawl_stats["duration_seconds"] = line.split(":")[-1].strip()

        # Return sanitized response (no credentials, no verbose logs)
        response = {
            "status": "success" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "output_index": crawl_config.get("output_index"),
            "domains_crawled": [d.get("url") for d in crawl_config.get("domains", [])],
        }

        # Add stats if available
        if crawl_stats:
            response["stats"] = crawl_stats

        # Include error details only if failed
        if result.returncode != 0:
            response["error_message"] = (
                result.stderr[:500] if result.stderr else "Crawl failed"
            )

        return response

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
    image=web_image,
    secrets=[
        modal.Secret.from_name("elasticsearch-config"),
        modal.Secret.from_name("api-keys"),
    ],
)
@modal.asgi_app()
def crawl_endpoint():
    from fastapi import FastAPI, HTTPException, Header, Depends
    from pydantic import BaseModel

    web_app = FastAPI()

    class CrawlConfig(BaseModel):
        domains: list
        output_index: str
        crawl_rules: list | None = None
        extraction_rules: list | None = None
        max_crawl_depth: int | None = None
        max_duration_seconds: int | None = None
        max_url_length: int | None = None
        user_agent: str | None = None

    async def verify_api_key(x_api_key: str = Header(None)):
        """Verify API key from X-API-Key header"""
        expected_key = os.environ.get("CRAWLER_API_KEY")

        if not expected_key:
            # If no API key configured, authentication is disabled
            return True

        if not x_api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing API key. Provide X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if x_api_key != expected_key:
            raise HTTPException(status_code=403, detail="Invalid API key")

        return True

    @web_app.post("/")
    async def trigger_crawl(
        config: CrawlConfig,
        async_mode: bool = True,
        authenticated: bool = Depends(verify_api_key),
    ) -> Dict[str, Any]:
        """
        Web endpoint to trigger a crawl.

        Query params:
        - async_mode: If true (default), returns immediately with execution_id.
                      If false, waits for completion (may timeout for long crawls).

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

        Returns (async_mode=true):
            {"status": "started", "execution_id": "...", "check_url": "..."}

        Returns (async_mode=false):
            Dictionary with crawl results
        """
        # Convert Pydantic model to dict
        crawl_config = config.model_dump(exclude_none=True)

        if async_mode:
            # Start crawl asynchronously and return immediately
            function_call = run_crawler.spawn(crawl_config)
            execution_id = function_call.object_id

            return {
                "status": "started",
                "execution_id": execution_id,
                "message": "Crawl started successfully",
                "check_status_url": f"/status/{execution_id}",
            }
        else:
            # Run synchronously (wait for completion)
            result = run_crawler.remote(crawl_config)
            return result

    @web_app.get("/status/{execution_id}")
    async def check_status(
        execution_id: str, authenticated: bool = Depends(verify_api_key)
    ) -> Dict[str, Any]:
        """
        Check the status of a running crawl.

        Returns:
        - status: "running", "completed", "failed"
        - result: (only if completed) crawl results
        - error: (only if failed) error message
        """
        from modal.functions import FunctionCall

        try:
            function_call = FunctionCall.from_id(execution_id)

            # Try to get the result (non-blocking check)
            try:
                result = function_call.get(timeout=0)
                return {"status": "completed", "result": result}
            except TimeoutError:
                # Still running
                return {
                    "status": "running",
                    "execution_id": execution_id,
                    "message": "Crawl is still in progress",
                }
            except Exception as e:
                # Failed
                return {
                    "status": "failed",
                    "execution_id": execution_id,
                    "error": str(e),
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Could not find execution: {str(e)}",
            }

    return web_app


# Health check endpoint
@app.function(
    image=web_image,
)
@modal.asgi_app()
def health():
    """Health check endpoint"""
    from fastapi import FastAPI

    web_app = FastAPI()

    @web_app.get("/")
    async def health_check() -> Dict[str, str]:
        return {"status": "healthy", "service": "elastic-crawler", "version": "1.0.0"}

    return web_app


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
