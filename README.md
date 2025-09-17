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

### Option 1: Docker (Recommended)

The easiest way to get started is using Docker:

```bash
# Build the image
./docker-run.sh build

# Analyze a single URL
./docker-run.sh url "https://example.com" en

# Batch analysis from file
./docker-run.sh batch examples/urls.txt es

# Run examples
./docker-run.sh examples

# Interactive shell
./docker-run.sh shell
```

### Option 2: Local Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run CLI
python -m transqa.cli.main scan --url "https://example.com" --lang en
```

### Option 3: Poetry (Advanced)

```bash
# Install with Poetry
poetry install

# Install with extras for full functionality
poetry install --extras "full"

# Run CLI
poetry run transqa scan --url "https://example.com" --lang en
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

## Docker Commands

```bash
# Build the Docker image
./docker-run.sh build

# Analyze a single URL
./docker-run.sh url "https://example.com" en [output-name]

# Batch analysis from file  
./docker-run.sh batch examples/urls.txt es [output-name]

# Show configuration
./docker-run.sh config

# Validate configuration
./docker-run.sh validate

# Run interactive shell
./docker-run.sh shell

# Run example analyses
./docker-run.sh examples
```

## Development

```bash
# Local development setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Or with Poetry
poetry install --with dev
poetry run pre-commit install

# Run tests
pytest tests/

# Format code
black src/ tests/
isort src/ tests/
```

## Contributing

We welcome contributions! This is an open source project under the MIT License.

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Follow code style**: Run `black` and `isort` on your code
5. **Commit your changes**: `git commit -m '🚀 Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Areas for Contribution

- 🌍 **Language Support**: Add support for more languages
- 🔧 **Verifiers**: Implement new verification rules
- 🎨 **UI/UX**: Improve the desktop and web interfaces
- 📖 **Documentation**: Improve docs and examples
- 🧪 **Testing**: Add more test cases and coverage
- 🐛 **Bug Fixes**: Help identify and fix issues

## License

**MIT License** © 2025 TransQA Project

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for full details.

### What this means:
- ✅ **Free to use** for personal and commercial projects
- ✅ **Free to modify** and distribute
- ✅ **Free to contribute** back to the project
- ✅ **No warranty** - use at your own risk

## Support

- 📖 **Documentation**: Check the docs and examples
- 🐛 **Issues**: Report bugs via GitHub Issues
- 💡 **Feature Requests**: Suggest improvements via GitHub Issues
- 🤝 **Community**: Join discussions and help others
