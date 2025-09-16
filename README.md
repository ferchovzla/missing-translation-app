# TransQA - Web Translation Quality Assurance Tool

A powerful tool for detecting translation errors and language leakage in web pages across Spanish (ES), English (EN), and Dutch (NL).

## Features

- 🌐 **Web Page Analysis**: Extract and analyze visible text from any public URL
- 🔍 **Language Detection**: Identify language leakage and untranslated content
- 📝 **Grammar & Spelling**: Advanced verification using LanguageTool and spell checkers
- 🖥️ **Desktop UI**: Modern, accessible interface with dark/light theme support
- ⚡ **CLI Interface**: Batch processing and CI/CD integration
- 📊 **Export Reports**: CSV, JSON, and HTML report formats
- 🚀 **JavaScript Support**: Optional rendering for dynamic content

## Quick Start

### Installation

```bash
# Install with Poetry (recommended)
poetry install

# Install with extras for full functionality
poetry install --extras "full"

# Install browser for JavaScript rendering (optional)
poetry run playwright install chromium
```

### Desktop Application

```bash
poetry run transqa gui
```

### CLI Usage

```bash
# Basic analysis
poetry run transqa scan --url "https://example.com" --lang en

# With JavaScript rendering and export
poetry run transqa scan --url "https://example.com" --lang en --render --out report.json

# Batch processing
poetry run transqa scan --file urls.txt --lang es --parallel 4 --format csv
```

## Supported Languages

- 🇪🇸 Spanish (ES)
- 🇬🇧 English (EN)  
- 🇳🇱 Dutch (NL)

## Configuration

Create a `transqa.toml` file for custom settings:

```toml
[target]
language = "en"
render_js = false

[rules]
leak_threshold = 0.08
ignore_selectors = [".visually-hidden", "script", "style"]
whitelist = "whitelist.txt"

[languagetool]
server_url = "http://localhost:8081"
local_server = true
```

## Development

```bash
# Setup development environment
poetry install --with dev
poetry run pre-commit install

# Run tests
poetry run pytest

# Format code
poetry run black src/ tests/
poetry run isort src/ tests/
```

## License

MIT License - see LICENSE file for details.
