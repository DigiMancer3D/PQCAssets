# =====================================================
# PQCassets Master Makefile
# =====================================================
# Usage:
#   make setup     # One-time setup (venv + deps + build)
#   make build     # Build the pah C binary
#   make test      # Run the full test suite
#   make clean     # Clean build artifacts
# =====================================================

PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: setup build test clean venv

# Default target
all: setup test

# Create virtual environment
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
	fi

# Install Python dependencies
deps: venv
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi

# Build the pah C binary
build:
	@echo "Building pah binary..."
	@$(MAKE) -C pah || (echo "Building pah with gcc..." && cd pah && gcc -o pah pah.c -loqs -lm)
	@chmod +x pah/pah

# Full one-time setup
setup: venv deps build
	@echo ""
	@echo "✅ Setup complete!"
	@echo "Run tests with: make test"
	@echo ""

# Run the master test suite
test:
	@echo "Running PQCassets Full Test Suite..."
	@$(PY) tests/run_full_test_suite.py

# Clean build artifacts
clean:
	@echo "Cleaning..."
	@rm -rf $(VENV)
	@rm -f pah/pah
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean done."

# Quick help
help:
	@echo "PQCassets Makefile targets:"
	@echo "  make setup   - Full setup (venv + deps + build)"
	@echo "  make build   - Build only the pah binary"
	@echo "  make test    - Run full test suite"
	@echo "  make clean   - Remove venv and build artifacts"
