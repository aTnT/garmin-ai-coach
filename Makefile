# Garmin AI Coach - Makefile for Testing and Development

.PHONY: help test test-planning test-coverage test-coverage-planning clean lint format

# Default target
help:
	@echo "Garmin AI Coach - Development Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test                    - Run all tests"
	@echo "  make test-planning          - Run planning module tests only"
	@echo "  make test-coverage          - Run all tests with coverage report"
	@echo "  make test-coverage-planning - Run planning tests with detailed coverage"
	@echo "  make test-quick             - Run fast unit tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint                   - Run ruff linter"
	@echo "  make format                 - Format code with black and ruff"
	@echo "  make typecheck              - Run mypy type checker (if installed)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean                  - Remove test artifacts and cache"

# Run all tests
test:
	python -m pytest tests/ -v

# Run planning module tests only (fast, focused)
test-planning:
	python -m pytest tests/test_plan*.py tests/test_workout*.py tests/test_performance*.py -v

# Run all tests with coverage
test-coverage:
	python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Run planning tests with detailed coverage
test-coverage-planning:
	@echo "Running planning module tests with coverage..."
	python -m pytest \
		tests/test_plan_storage.py \
		tests/test_plan_lifecycle_integration.py \
		tests/test_workout_selector.py \
		tests/test_workout_selector_advanced.py \
		tests/test_performance_analyzer.py \
		tests/test_performance_analyzer_advanced.py \
		tests/test_workout_generator.py \
		-v \
		--cov=services/ai/planning \
		--cov=services/ai/workouts \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/planning
	@echo ""
	@echo "Coverage report generated in htmlcov/planning/index.html"

# Run quick unit tests (skip slow integration tests)
test-quick:
	python -m pytest tests/ -v -m "not integration" --tb=short

# Run linter
lint:
	ruff check . --exclude .pixi

# Format code
format:
	black . --exclude .pixi
	ruff check --fix . --exclude .pixi

# Type checking (optional, requires mypy)
typecheck:
	@if command -v mypy > /dev/null; then \
		mypy services cli --ignore-missing-imports; \
	else \
		echo "mypy not installed. Install with: pip install mypy"; \
	fi

# Clean test artifacts and cache
clean:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete!"

# Development workflow shortcuts
dev-test: lint test-planning
	@echo "Development tests complete!"

# CI/CD workflow
ci: lint test-coverage
	@echo "CI tests complete!"
