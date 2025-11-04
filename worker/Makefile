.PHONY: test test-cov test-fast lint clean install

# Install dependencies
install:
	pip install -r requirements.txt

# Run all tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ -v --cov=simulation --cov=worker --cov-report=term-missing --cov-report=html

# Run fast tests only (skip slow/integration)
test-fast:
	pytest tests/ -v -m "not slow and not integration"

# Run unit tests only
test-unit:
	pytest tests/ -v -m "unit"

# Run integration tests only
test-integration:
	pytest tests/ -v -m "integration"

# View coverage report
coverage:
	python -m http.server 8000 -d htmlcov

# Lint code
lint:
	pylint simulation/ worker.py cli_runner.py || true
	flake8 simulation/ worker.py cli_runner.py || true

# Clean up
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name __pycache__ -exec rm -r {} + || true
	find . -type f -name "*.pyc" -delete || true

# Run simulation
run:
	python cli_runner.py --config configs/default.json

