# Contributing to InstaTitan

Thank you for considering contributing! Here's how to get started:

## Development Setup

```bash
# Clone and setup
git clone https://github.com/aman/instatitan.git
cd instatitan
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pre-commit install

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest tests/ -v
```

## Code Style

- Follow PEP 8, 100 char line limit
- Run `black src/` before committing
- Type hints required for all public APIs
- Docstrings for all modules and classes

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass (`pytest tests/ -v`)
4. Run `flake8 src/` with zero warnings
5. Submit PR with clear description of changes

## Commit Messages

Follow conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
