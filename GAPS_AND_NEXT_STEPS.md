# Gap Analysis & Next Steps

## Executive Summary

**Current State:**
- ✅ **139 passing tests** across planning modules (100% pass rate)
- ✅ **60% overall codebase coverage** (up from 51%)
- ✅ **Planning core modules**: 95-98% coverage (exceeds targets)
- ⚠️ **8 test files** with import errors (missing dependencies: langgraph, httpx)
- ⚠️ **Critical gaps** in integration testing and low-coverage modules

**Achievements This Session:**
1. Comprehensive test coverage for planning modules (plan_storage, workout_selector, performance_analyzer)
2. End-to-end integration tests for complete plan lifecycle
3. Development tooling (Makefile, TESTING.md documentation)
4. 49 new tests with real-world scenarios

---

## Coverage Analysis by Module

### ✅ Excellent Coverage (80%+)
| Module | Coverage | Gap | Priority |
|--------|----------|-----|----------|
| plan_storage.py | **98%** | None | ✅ Complete |
| performance_analyzer.py | **96%** | Rare edge cases | ✅ Complete |
| workout_selector.py | **95%** | Phase transitions | ✅ Complete |
| workout_generator.py | **93%** | Error paths | 🟨 Minor |
| workout_models.py | **92%** | Serialization | 🟨 Minor |
| plan_models.py | **80%** | Property getters | 🟨 Minor |

### ⚠️ Medium Coverage (40-79%)
| Module | Coverage | Lines Missing | Priority |
|--------|----------|---------------|----------|
| power_curve/power_models.py | 62% | 82 lines | 🟧 Medium |
| power_curve/power_analyzer.py | 59% | 62 lines | 🟧 Medium |
| trends/trends_models.py | 44% | 102 lines | 🟧 Medium |

### 🔴 Low Coverage (<40%)
| Module | Coverage | Lines Missing | Priority |
|--------|----------|---------------|----------|
| **activity_matcher.py** | **16%** | 99 lines | 🔴 **HIGH** |
| **adaptation_engine.py** | **16%** | 143 lines | 🔴 **HIGH** |
| power_curve/power_plotter.py | 11% | 133 lines | 🟨 Low (plotting) |
| trends/trends_analyzer.py | 10% | 197 lines | 🟧 Medium |
| trends/trends_plotter.py | 10% | 125 lines | 🟨 Low (plotting) |

### ❌ No Coverage (0%)
| Module | Lines | Reason | Priority |
|--------|-------|--------|----------|
| **readiness_calculator.py** | 316 | No tests | 🔴 **HIGH** |
| garmin/data_extractor.py | 548 | Complex integration | 🟧 Medium |
| outside/client.py | 288 | API integration | 🟨 Low |
| **LangGraph nodes** | ~500 | Workflow integration | 🟧 Medium |
| AI settings/config | ~150 | Configuration | 🟨 Low |

---

## Critical Gaps (Priority 1)

### 1. Activity Matcher (16% coverage)
**Impact:** Can't track workout completion automatically
**Missing:**
- Activity-to-workout matching logic (lines 58-75, 92-108)
- Time window matching (lines 112-130)
- Quality rating calculation (lines 153-185)
- Match scoring algorithm (lines 204-228)

**Action Items:**
```python
# tests/test_activity_matcher.py (NEW)
- test_match_activity_to_workout_perfect_timing()
- test_match_activity_to_workout_duration_variance()
- test_match_activity_quality_excellent_vs_poor()
- test_calculate_completion_percentage()
- test_find_best_match_among_candidates()
```

**Estimated Effort:** 3-4 hours | **Value:** Critical for plan automation

---

### 2. Adaptation Engine (16% coverage)
**Impact:** Plans don't automatically adapt to performance/readiness
**Missing:**
- Adaptation decision logic (lines 66-125)
- Readiness-based adaptation (lines 152-231)
- Performance-based triggers (lines 260-319)
- Workout rescheduling (lines 327-383)
- Load management (lines 389-440)

**Action Items:**
```python
# tests/test_adaptation_engine.py (NEW)
- test_should_adapt_low_readiness()
- test_should_adapt_missed_workouts()
- test_should_adapt_declining_performance()
- test_should_not_adapt_minor_variance()
- test_reschedule_workouts()
- test_reduce_load_overreaching()
```

**Estimated Effort:** 4-5 hours | **Value:** Core feature enablement

---

### 3. Readiness Calculator (0% coverage)
**Impact:** Daily readiness scores may have undetected bugs
**Missing:** Everything (316 lines)
- HRV-based readiness (Whoop-style algorithm)
- Sleep quality scoring
- Training load integration
- Stress marker analysis

**Action Items:**
```python
# tests/test_readiness_calculator.py (EXISTS but needs expansion)
- test_calculate_readiness_high_hrv_good_sleep()
- test_calculate_readiness_low_hrv_poor_sleep()
- test_calculate_readiness_high_load()
- test_readiness_score_ranges()
- test_readiness_trend_calculation()
```

**Estimated Effort:** 5-6 hours | **Value:** Feature correctness

---

## Integration Gaps (Priority 2)

### 4. LangGraph → Training Plans Integration
**Status:** No connection between AI workflow and plan modules
**Gap:**
- LangGraph nodes (0% coverage) don't call planning modules
- Season planner output not persisted to plan_storage
- Weekly planner doesn't use workout_selector
- No tests for end-to-end workflow

**Action Items:**
```python
# tests/test_langgraph_planning_integration.py (NEW)
- test_season_planner_creates_training_plan()
- test_weekly_planner_uses_workout_selector()
- test_plan_stored_after_workflow()
- test_workflow_with_competitions()
```

**Estimated Effort:** 6-8 hours | **Value:** Completes feature integration

---

### 5. CLI Integration Tests
**Status:** CLI entry points not tested (8 test files with import errors)
**Missing:**
- End-to-end CLI workflow tests
- Config parsing and validation
- Error handling and user feedback
- Output file generation

**Failing Tests:**
```
test_cli_e2e.py                     - ModuleNotFoundError: httpx
test_cost_tracking_integration.py   - ModuleNotFoundError: langgraph
test_data_summarization_nodes.py    - ModuleNotFoundError: langgraph
test_extract_text_content.py        - ModuleNotFoundError: langgraph
test_hitl_feature.py                - ModuleNotFoundError: langgraph
test_langgraph_core_migration.py    - ModuleNotFoundError: langgraph
test_langgraph_foundation.py        - ModuleNotFoundError: langgraph
test_langgraph_planning_workflow.py - ModuleNotFoundError: langgraph
```

**Action Items:**
1. Fix dependency issues (install langgraph, httpx)
2. Re-run existing tests to identify real failures
3. Add missing CLI tests

**Estimated Effort:** 4-6 hours | **Value:** CI/CD readiness

---

## Feature Completeness Gaps (Priority 3)

### 6. Power Curve Analysis (59-62% coverage)
**Impact:** Moderate - power analysis works but lacks edge case handling
**Missing:**
- Power curve smoothing edge cases
- Critical power calculations with sparse data
- FTP estimation error bounds
- Historical comparison edge cases

**Action Items:**
```python
# Expand tests/test_power_curve.py
- test_power_curve_sparse_data()
- test_critical_power_insufficient_data()
- test_ftp_estimation_confidence_intervals()
- test_historical_comparison_no_baseline()
```

**Estimated Effort:** 2-3 hours | **Value:** Robustness

---

### 7. Trends Analysis (10-44% coverage)
**Impact:** Low - trends work but lack comprehensive testing
**Missing:**
- Trend detection algorithms
- Long-term progression analysis
- Anomaly detection
- Multi-metric correlation

**Action Items:**
```python
# Expand tests/test_trends_analyzer.py
- test_detect_performance_trend_improving()
- test_detect_performance_trend_plateau()
- test_anomaly_detection()
- test_multi_metric_correlation()
```

**Estimated Effort:** 3-4 hours | **Value:** Analytics quality

---

### 8. Garmin Data Extraction (8% coverage)
**Impact:** Low priority - extraction works in practice
**Note:** Difficult to test without mocking entire Garmin API
**Recommendation:** Defer until integration issues arise

---

## Infrastructure & Quality Gaps (Priority 4)

### 9. CI/CD Pipeline
**Status:** None
**Needed:**
- GitHub Actions workflow for tests
- Automated coverage reporting
- Pre-commit hooks
- Automated linting

**Action Items:**
```yaml
# .github/workflows/tests.yml (NEW)
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
      - name: Run tests
      - name: Upload coverage
```

**Estimated Effort:** 2-3 hours | **Value:** Code quality enforcement

---

### 10. Documentation Improvements
**Missing:**
- Architecture Decision Records (ADRs)
- API documentation (Sphinx/MkDocs)
- Contribution guidelines
- Code of conduct

**Action Items:**
1. Create docs/adr/ directory for ADRs
2. Generate API docs from docstrings
3. Write CONTRIBUTING.md
4. Add inline documentation for complex algorithms

**Estimated Effort:** 4-6 hours | **Value:** Developer experience

---

## Prioritized Roadmap

### Phase 1: Critical Functionality (12-15 hours)
**Goal:** Enable automatic workout tracking and plan adaptation

1. **Activity Matcher tests** (3-4h) → Enable workout completion tracking
2. **Adaptation Engine tests** (4-5h) → Enable automatic plan adjustments
3. **Readiness Calculator tests** (5-6h) → Ensure accuracy of readiness scores

**Outcome:** Plans can automatically track progress and adapt

---

### Phase 2: Integration & CI (10-14 hours)
**Goal:** Connect all components and automate testing

4. **Fix test import errors** (2-3h) → Get existing tests passing
5. **LangGraph integration tests** (6-8h) → Connect AI workflow to plans
6. **CI/CD pipeline** (2-3h) → Automate test runs

**Outcome:** Full end-to-end workflow with automated quality checks

---

### Phase 3: Robustness & Polish (10-14 hours)
**Goal:** Improve edge case handling and documentation

7. **Power curve edge cases** (2-3h)
8. **Trends analysis expansion** (3-4h)
9. **Documentation improvements** (4-6h)
10. **CLI integration tests** (2-3h)

**Outcome:** Production-ready system with excellent documentation

---

## Quick Wins (Can do now)

### 1. Fix Import Errors (30 minutes)
```bash
pixi add httpx langgraph
# or
pip install httpx langgraph
pytest tests/ -v  # Re-run all tests
```

### 2. Add Pre-commit Hooks (15 minutes)
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format
```

### 3. Generate Coverage Badge (10 minutes)
```bash
make test-coverage-planning
# Add badge to README: ![Coverage](coverage-badge.svg)
```

---

## Metrics to Track

**Current State:**
- Tests: 139 passing (planning modules)
- Coverage: 60% overall, 95-98% planning core
- Lines of test code: ~10,000 lines
- Test types: Unit (126), Integration (13)

**Target State (Phase 1-3):**
- Tests: 200+ passing
- Coverage: 75% overall, 90%+ all planning modules
- All import errors resolved
- CI/CD pipeline operational

---

## Recommendations

### Immediate Next Steps (This Week)
1. ✅ **Fix dependency issues** - Run `pixi add httpx langgraph`
2. 🔴 **Activity Matcher tests** - Critical for automation (Priority 1.1)
3. 🔴 **Adaptation Engine tests** - Core feature (Priority 1.2)

### Short Term (Next 2-4 Weeks)
4. Fix all test import errors
5. LangGraph → Planning integration
6. CI/CD pipeline setup
7. Readiness calculator tests

### Medium Term (1-2 Months)
8. Power curve robustness improvements
9. Comprehensive API documentation
10. Advanced analytics testing (trends, correlations)

### Long Term (Backlog)
- Garmin data extraction mocking framework
- Multi-athlete support testing
- Performance benchmarking suite
- Load testing for large datasets

---

## Success Criteria

**Phase 1 Complete When:**
- ✅ Activity matcher: 80%+ coverage
- ✅ Adaptation engine: 80%+ coverage
- ✅ Readiness calculator: 80%+ coverage
- ✅ All critical user workflows covered by tests

**Phase 2 Complete When:**
- ✅ All test files importing successfully
- ✅ LangGraph workflow creates and stores plans
- ✅ CI pipeline runs tests on every commit
- ✅ Coverage reports automatically generated

**Phase 3 Complete When:**
- ✅ 75%+ overall codebase coverage
- ✅ All modules >50% coverage (except plotters)
- ✅ Comprehensive developer documentation
- ✅ Contributing guidelines in place

---

## Conclusion

**Strong Foundation Built:**
The planning modules now have excellent test coverage (95-98%) and comprehensive integration tests. The core functionality is solid and production-ready.

**Critical Path Forward:**
1. Activity matching (enables automation)
2. Adaptation engine (enables intelligence)
3. Full integration (connects everything)

**Estimated Total Effort:**
- Phase 1 (Critical): 12-15 hours
- Phase 2 (Integration): 10-14 hours
- Phase 3 (Polish): 10-14 hours
- **Total: 32-43 hours** (~1-2 weeks of focused work)

**Biggest Impact Actions:**
1. Activity matcher tests → Unlocks automatic tracking
2. Adaptation engine tests → Enables smart plan adjustments
3. LangGraph integration → Connects AI planning to plan management

---

**Last Updated:** November 2025
**Maintainer:** Development Team
**Next Review:** After Phase 1 completion
