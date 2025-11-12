# Testing Guide

## Quick Start

Run all planning module tests:
```bash
make test-planning
```

Run with coverage report:
```bash
make test-coverage-planning
```

## Test Commands

### Basic Testing
- `make test` - Run all tests
- `make test-planning` - Run planning module tests only (fastest)
- `make test-quick` - Run unit tests only (skip slow integration tests)

### Coverage Reporting
- `make test-coverage` - All tests with full coverage report
- `make test-coverage-planning` - Planning module tests with detailed coverage
  - Generates HTML report in `htmlcov/planning/index.html`
  - Shows line-by-line coverage

### Code Quality
- `make lint` - Run ruff linter
- `make format` - Auto-format with black and ruff
- `make clean` - Remove test artifacts

## Test Structure

### Unit Tests
- **test_plan_storage.py** (21 tests) - TrainingPlan persistence, versioning, backups
- **test_workout_selector.py** (12 tests) - Basic workout selection logic
- **test_workout_selector_advanced.py** (21 tests) - Advanced selection (TAPER, constraints)
- **test_performance_analyzer.py** (12 tests) - Basic performance analysis
- **test_performance_analyzer_advanced.py** (31 tests) - Advanced analysis (power, pace, intervals)
- **test_workout_generator.py** (11 tests) - Structured workout generation

### Integration Tests
- **test_plan_lifecycle_integration.py** (13 tests) - End-to-end plan workflows
  - Plan creation → storage → retrieval
  - Multi-week execution (8-13 week plans)
  - Workout completion tracking
  - Plan adaptation flow
  - Constraint-based schedule adjustments

## Coverage Targets (Achieved)

| Module | Target | Actual | Status |
|--------|--------|--------|--------|
| plan_storage.py | 80% | **98%** | ✅ Exceeded |
| workout_selector.py | 80% | **95%** | ✅ Exceeded |
| performance_analyzer.py | 80% | **96%** | ✅ Exceeded |
| workout_generator.py | - | **93%** | ✅ Bonus |
| workout_models.py | - | **92%** | ✅ Bonus |

**Overall: 139 tests passing | 60% codebase coverage**

## Running Specific Tests

### By Module
```bash
# Planning storage tests
pytest tests/test_plan_storage.py -v

# Workout selection tests
pytest tests/test_workout_selector*.py -v

# Performance analysis tests
pytest tests/test_performance_analyzer*.py -v

# Integration tests
pytest tests/test_plan_lifecycle_integration.py -v
```

### By Test Class
```bash
# Test specific functionality
pytest tests/test_plan_storage.py::TestBackupManagement -v
pytest tests/test_workout_selector_advanced.py::TestTaperPhaseSelection -v
```

### By Test Function
```bash
# Run single test
pytest tests/test_plan_storage.py::TestBackupManagement::test_create_backup_on_save -v
```

## Continuous Integration

For CI/CD pipelines:
```bash
make ci  # Runs lint + full test coverage
```

## Coverage Reports

### Terminal Report
```bash
pytest tests/test_plan*.py --cov=services/ai/planning --cov-report=term-missing
```

Shows missing lines directly in terminal.

### HTML Report
```bash
make test-coverage-planning
# Open htmlcov/planning/index.html in browser
```

Interactive line-by-line coverage visualization.

## Test Markers

Tests can be marked for selective execution:

```python
@pytest.mark.unit
def test_simple_function():
    ...

@pytest.mark.integration
def test_complex_workflow():
    ...
```

Run by marker:
```bash
pytest -m unit  # Unit tests only
pytest -m integration  # Integration tests only
```

## Writing New Tests

### Test File Naming
- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`
- Advanced tests: `test_<module_name>_advanced.py`

### Test Class Organization
```python
class TestFeatureName:
    """Test <feature> functionality."""

    def test_basic_case(self):
        """Test basic happy path."""
        ...

    def test_edge_case(self):
        """Test boundary conditions."""
        ...

    def test_error_handling(self):
        """Test error cases."""
        ...
```

### Coverage Best Practices
1. **Test all public methods** - 100% coverage of public API
2. **Test error paths** - Don't just test happy path
3. **Test edge cases** - Empty inputs, None values, boundary conditions
4. **Test integration points** - How components work together

## Debugging Tests

### Verbose output
```bash
pytest tests/test_plan_storage.py -vv
```

### Show print statements
```bash
pytest tests/test_plan_storage.py -s
```

### Stop on first failure
```bash
pytest tests/test_plan_storage.py -x
```

### Debug with pdb
```bash
pytest tests/test_plan_storage.py --pdb
```

## Performance

- **Unit tests**: ~0.1s each (fast, focused)
- **Integration tests**: ~0.3s each (comprehensive workflows)
- **Full planning suite**: ~15-17s (139 tests)

## Maintenance

### Update test data
Test fixtures use `create_*` helper functions:
- `create_test_plan()` - TrainingPlan with full structure
- `create_base_phase()` - Base phase with realistic volumes
- `create_simple_workout()` - StructuredWorkout for testing

### Update coverage targets
Edit Makefile coverage thresholds if needed:
```makefile
--cov-fail-under=80  # Fail if coverage drops below 80%
```

## Troubleshooting

### Import errors
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH=/home/user/garmin-ai-coach:$PYTHONPATH
```

### Missing dependencies
```bash
pip install pytest pytest-cov black ruff
```

### Test database conflicts
```bash
make clean  # Remove test artifacts
```

## Next Steps

To further improve test coverage:

1. **Activity Matcher** (16% → 80%) - Add tests for workout matching logic
2. **Adaptation Engine** (16% → 80%) - Test plan adaptation triggers
3. **Workout Generator** (93% → 95%) - Fill remaining edge cases
4. **End-to-end workflows** - Add more integration scenarios

---

**Last Updated**: November 2025
**Maintainer**: Development Team
**Test Framework**: pytest 9.0.1 with pytest-cov 7.0.0
