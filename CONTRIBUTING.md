# Contributing to Elastic Crawler Modal

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/elastic-crawler-modal-com.git`
3. Create a branch: `git checkout -b feature/your-feature-name`

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Authenticate with Modal
modal setup

# Configure secrets for testing
modal secret create elasticsearch-config \
  ELASTICSEARCH_HOST=your-test-host \
  ELASTICSEARCH_API_KEY=your-test-key
```

## Testing Your Changes

```bash
# Test locally with example config
modal run app.py --config-file example-config.yml

# Deploy to your Modal account
modal deploy app.py

# Test the deployed API
python test_api.py https://your-username--elastic-crawler-crawl-endpoint.modal.run
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and single-purpose

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issues when applicable (e.g., "Fix #123: Description")

## Pull Request Process

1. Update README.md with details of changes if needed
2. Update example-config.yml if adding new configuration options
3. Ensure your code passes all tests
4. Create a pull request with a clear description of changes

## Areas for Contribution

- **Features**: New crawler configuration options, authentication methods
- **Documentation**: Improved examples, troubleshooting guides
- **Testing**: Additional test cases, integration tests
- **Performance**: Optimization improvements
- **Bug fixes**: Address issues in the issue tracker

## Questions?

Feel free to open an issue for discussion before starting work on major changes.
