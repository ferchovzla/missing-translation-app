.PHONY: install install-dev test lint format clean build help

help: ## Show this help message
	@echo "TransQA - Web Translation Quality Assurance Tool"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m%-20s\033[0m %s\n", "Command", "Description"} /^[a-zA-Z_-]+:.*?##/ { printf "\033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation

install: ## Install the package for production
	poetry install --only=main

install-dev: ## Install the package with development dependencies
	poetry install --with=dev
	poetry run pre-commit install

install-full: ## Install with all optional dependencies (GUI, rendering, NLP)
	poetry install --extras="full" --with=dev
	poetry run playwright install chromium

##@ Development

test: ## Run tests
	poetry run pytest tests/ -v

test-cov: ## Run tests with coverage
	poetry run pytest tests/ --cov=src/transqa --cov-report=html --cov-report=term-missing

lint: ## Run linting (mypy, flake8)
	poetry run mypy src/transqa
	poetry run black --check src/ tests/
	poetry run isort --check-only src/ tests/

format: ## Format code with black and isort
	poetry run black src/ tests/
	poetry run isort src/ tests/

clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

##@ Building and Distribution

build: ## Build the package
	poetry build

build-exe: ## Build executable with PyInstaller (requires full install)
	poetry run pyinstaller --onefile --name transqa src/transqa/__main__.py

##@ Running

run-cli: ## Run CLI with poetry
	poetry run transqa

run-gui: ## Run GUI with poetry
	poetry run transqa gui

demo: ## Run demo analysis
	poetry run transqa scan --url "https://example.com" --lang en --verbose

##@ Configuration and Setup

init-config: ## Initialize default configuration file
	poetry run transqa config --init

validate-config: ## Validate configuration file
	poetry run transqa validate transqa.toml

download-models: ## Download language models (when implemented)
	@echo "Model download not yet implemented"

##@ Docker (Future)

docker-build: ## Build Docker image
	docker build -t transqa .

docker-run: ## Run in Docker
	docker run -it --rm transqa

##@ Debugging

debug: ## Run with debug logging
	TRANSQA_LOG_LEVEL=DEBUG poetry run transqa

profile: ## Run with profiling (when implemented)
	@echo "Profiling not yet implemented"
