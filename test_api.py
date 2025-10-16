#!/usr/bin/env python3
"""
Test script for the Elastic Crawler Modal API

This script sends a test crawl request to your deployed Modal endpoint.
"""

import requests
import json
import sys


def test_health(base_url: str):
    """Test the health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{base_url}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_crawl(base_url: str, config: dict):
    """Test the crawl endpoint"""
    print("Testing crawl endpoint...")
    print(f"Config: {json.dumps(config, indent=2)}")
    print("\nSending request...")

    response = requests.post(
        f"{base_url}/crawl_endpoint", json=config, timeout=3600  # 1 hour timeout
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"Crawl status: {result.get('status')}")

        if result.get("status") == "success":
            print(f"Return code: {result.get('return_code')}")
            stdout = result.get("stdout", "")
            if stdout:
                print(f"\nOutput (last 1000 chars):")
                print(stdout[-1000:])
        else:
            print(f"Error: {result.get('message', 'Unknown error')}")
            stderr = result.get("stderr", "")
            if stderr:
                print(f"\nError output:")
                print(stderr)
    else:
        print(f"Request failed: {response.text}")


if __name__ == "__main__":
    # Replace with your actual Modal endpoint URL
    # You can find this after deploying with: modal app show elastic-crawler
    BASE_URL = "https://your-username--elastic-crawler-crawl-endpoint.modal.run"

    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]

    print(f"Testing Modal Crawler API at: {BASE_URL}\n")

    # Test health endpoint
    test_health(BASE_URL)

    # Test crawl endpoint with example config
    crawl_config = {
        "domains": [
            {"url": "https://example.com", "seed_urls": ["https://example.com"]}
        ],
        "output_index": "test-crawler-example-com",
    }

    test_crawl(BASE_URL, crawl_config)
