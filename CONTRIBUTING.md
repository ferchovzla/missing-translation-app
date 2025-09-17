# Contributing to TransQA

¡Gracias por tu interés en contribuir al proyecto TransQA! 🎉

We welcome contributions from everyone. This document provides guidelines for contributing to the project.

## Quick Start

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your feature or fix
4. **Make your changes**
5. **Test** your changes thoroughly
6. **Submit** a pull request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Docker (optional, for testing)

### Local Development

```bash
# Clone your fork
git clone https://github.com/your-username/missing-translation-app.git
cd missing-translation-app

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt

# Or with Poetry (if available)
poetry install --with dev --extras full
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/transqa

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Code Style

We use strict code formatting and linting:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check types
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

## Types of Contributions

### 🐛 Bug Reports

When reporting bugs, please include:

- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Logs or error messages** if available

### 💡 Feature Requests

For new features:

- **Describe the problem** you're trying to solve
- **Explain your proposed solution**
- **Consider alternative approaches**
- **Discuss implementation complexity**

### 🔧 Code Contributions

#### Areas Where We Need Help

1. **Language Support**
   - Add support for new languages (Arabic, Chinese, etc.)
   - Improve language detection algorithms
   - Add language-specific validation rules

2. **Verification Rules**
   - Implement new issue detection patterns
   - Improve existing verification logic
   - Add domain-specific validators

3. **User Interfaces**
   - Enhance the desktop GUI (PySide6)
   - Improve the web interface (FastAPI + HTML/CSS/JS)
   - Mobile-responsive design improvements

4. **Performance**
   - Optimize text processing algorithms
   - Improve concurrent processing
   - Reduce memory usage

5. **Documentation**
   - API documentation improvements
   - User guides and tutorials
   - Code examples and demos

6. **Testing**
   - Unit tests for new features
   - Integration tests
   - Performance benchmarks

### 🎨 UI/UX Contributions

For interface improvements:

- **Follow modern design principles**
- **Ensure accessibility** (WCAG guidelines)
- **Test on multiple devices** and browsers
- **Maintain responsive design**
- **Keep consistent styling** with existing components

## Pull Request Process

### Before Submitting

1. **Ensure tests pass**: `pytest`
2. **Format code**: `black src/ tests/`
3. **Sort imports**: `isort src/ tests/`
4. **Type check**: `mypy src/`
5. **Update documentation** as needed
6. **Add tests** for new functionality

### PR Guidelines

1. **Create a descriptive title**:
   - ✅ `🚀 Add support for French language detection`
   - ❌ `Fix bug`

2. **Write a clear description**:
   ```markdown
   ## Changes
   - Add French language support to language detector
   - Update configuration to include French rules
   - Add unit tests for French text processing
   
   ## Testing
   - All existing tests pass
   - Added 15 new test cases for French
   - Tested with French websites
   
   ## Documentation
   - Updated README with French language support
   - Added French examples to docs
   ```

3. **Keep PRs focused**: One feature/fix per PR
4. **Link related issues**: Use `Fixes #123` or `Closes #456`
5. **Add breaking change notes** if applicable

### Review Process

- All PRs require at least one approval
- CI tests must pass
- Code coverage should not decrease
- Documentation must be updated for user-facing changes

## Code Architecture

### Project Structure

```
src/transqa/
├── models/          # Pydantic data models
├── core/           # Core analysis logic
│   ├── fetchers/   # Web content fetching
│   ├── extractors/ # Text extraction
│   ├── language/   # Language detection
│   └── verification/ # QA rules and checks
├── cli/            # Command line interface
└── utils/          # Utility functions

landing-page-app/   # Web interface
├── api/           # FastAPI backend
├── static/        # Frontend assets
└── templates/     # HTML templates
```

### Design Principles

1. **Modular Architecture**: Each component has a single responsibility
2. **Interface-based Design**: Use Python protocols for flexibility
3. **Configuration-driven**: Behavior controlled by config files
4. **Async-friendly**: Support for concurrent processing
5. **Error Resilience**: Graceful handling of failures
6. **Extensible**: Easy to add new languages and rules

### Adding New Components

#### Language Support

1. **Detector**: Implement `BaseLanguageDetector`
2. **Verifier**: Add language-specific rules in `verification/`
3. **Configuration**: Update `transqa.toml` with language settings
4. **Tests**: Add comprehensive test coverage

#### Verification Rules

1. **Inherit from `BaseVerifier`**
2. **Implement issue detection logic**
3. **Return structured `Issue` objects**
4. **Add configuration options**
5. **Write unit tests**

## Community Guidelines

### Code of Conduct

- **Be respectful** and inclusive
- **Welcome newcomers** and help them learn
- **Focus on constructive feedback**
- **Assume good intentions**

### Communication

- **GitHub Issues**: Bug reports, feature requests
- **Pull Requests**: Code discussions
- **Discussions**: General questions and ideas

### Recognition

Contributors are recognized in:
- Project README
- Release notes
- GitHub contributors page

## Getting Help

- **Documentation**: Check README and code comments
- **Issues**: Search existing issues first
- **Discussions**: Ask questions in GitHub Discussions
- **Code**: Look at existing implementations for patterns

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Quick Reference

### Commit Message Format

```
🤖 Add feature description

Detailed explanation of changes made
- Bullet point 1
- Bullet point 2

Fixes #123
```

### Common Commands

```bash
# Setup
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# Development
pytest tests/
black src/ tests/
mypy src/

# Submission
git add .
git commit -m "🚀 Add amazing feature"
git push origin feature/my-feature
```

---

**Thank you for contributing to TransQA!** 🚀
