# AI Assistant Instructions for usb-remote

## Python Package Manager

This project uses **`uv`** as the Python package manager and task runner.

### Running Python Commands

Always use `uv run` prefix when executing Python commands:

```bash
# ✅ Correct - Use uv run
uv run python -m pytest tests/
uv run python -m usb_remote --help
uv run python -c "import usb_remote; print('OK')"

# ❌ Incorrect - Don't use python directly
python -m pytest tests/
python -m usb_remote --help
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_cli.py

# Run with verbose output
uv run pytest -xvs

# Run with coverage
uv run pytest --cov=usb_remote
```

### Running Tox

The project uses tox with uv support via `tox-uv`:

```bash
# Run all tox environments in parallel
uv run tox -p

# Run specific environment
uv run tox -e tests
uv run tox -e pre-commit
uv run tox -e type-checking
uv run tox -e docs
```

### Type Checking

```bash
uv run pyright
```

### Linting and Formatting

```bash
uv run ruff check .
uv run ruff format .
```

### Building Documentation

```bash
uv run sphinx-build -b html docs build/html
uv run sphinx-autobuild docs build/html
```

### Installing Dependencies

```bash
# Sync dependencies from pyproject.toml
uv sync

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name
```

## Project Structure

- `src/usb_remote/` - Main package source code
  - `__main__.py` - CLI entry point with typer commands
  - `server.py` - USB sharing server
  - `client.py` - Client functions for connecting to servers
  - `client_service.py` - Client service that accepts socket commands
  - `api.py` - Pydantic models for server API
  - `client_api.py` - Pydantic models for client service API
  - `config.py` - Configuration management
  - `usbdevice.py` - USB device detection and management
  - `port.py` - USB/IP port management
  - `service.py` - Systemd service installation

- `tests/` - Test suite
- `docs/` - Sphinx documentation

## Key Commands

- `usb-remote server` - Start the USB sharing server
- `usb-remote client-service` - Start the client service with socket API
- `usb-remote list` - List available USB devices
- `usb-remote attach` - Attach a USB device
- `usb-remote detach` - Detach a USB device
- `usb-remote config` - Manage configuration

## Testing Philosophy

- Always run commands through `uv run` to ensure consistent environment
- Use pytest for testing
- Run tox for comprehensive testing across all environments
- Maintain test coverage with `pytest-cov`
