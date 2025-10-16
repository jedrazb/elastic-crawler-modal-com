.PHONY: help install setup deploy test clean logs status

help:
	@echo "Elastic Crawler Modal - Available commands:"
	@echo ""
	@echo "  make install    - Install Python dependencies"
	@echo "  make setup      - Setup Modal authentication"
	@echo "  make deploy     - Deploy app to Modal"
	@echo "  make test       - Run API tests (requires MODAL_URL env var)"
	@echo "  make logs       - View Modal app logs"
	@echo "  make status     - Show deployed app status"
	@echo "  make clean      - Clean up temporary files"
	@echo ""

install:
	pip install -r requirements.txt

setup:
	@echo "Setting up Modal authentication..."
	@modal setup

deploy:
	@chmod +x deploy.sh
	@./deploy.sh

test:
	@if [ -z "$(MODAL_URL)" ]; then \
		echo "Error: MODAL_URL environment variable is not set"; \
		echo "Usage: MODAL_URL=your-endpoint-url make test"; \
		exit 1; \
	fi
	python test_api.py $(MODAL_URL)

logs:
	modal app logs elastic-crawler

status:
	@echo "Checking Modal app status..."
	@modal app show elastic-crawler

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	@echo "Cleaned up temporary files"
