# Testing Guide

This document explains how to run tests, understand coverage reports, and contribute new tests to the PrintVault project.

## Table of Contents

- [Quick Start](#quick-start)
- [Backend Testing (Django)](#backend-testing-django)
- [Frontend Testing (Vue)](#frontend-testing-vue)
- [Coverage Reports](#coverage-reports)
- [Writing Tests](#writing-tests)
- [Test Organization](#test-organization)
- [CI/CD Integration](#cicd-integration)

## Quick Start

### Backend Prerequisites

Ensure you have testing dependencies installed:

```bash
pip install -r requirements-dev.txt
```

This includes:

- pytest 8.3.4 - Test framework
- pytest-django 4.9.0 - Django integration for pytest
- coverage 7.6.9 - Code coverage measurement
- pytest-cov 6.0.0 - Coverage plugin for pytest
- factory-boy 3.3.1 - Test data generation

**Note:** Production deployments use `requirements.txt` (no testing packages). Development/CI uses `requirements-dev.txt` (includes testing).

### Frontend Prerequisites

Install frontend testing dependencies:

```bash
cd frontend
npm install
```

This includes:

- vitest 3.0.1 - Fast Vite-native test framework
- @vue/test-utils 2.4.6 - Vue component testing utilities
- happy-dom 16.2.0 - Lightweight DOM implementation
- @vitest/coverage-v8 3.0.1 - Coverage reporting

### Run All Tests

**Backend:**

```bash
pytest
```

**Frontend:**

```bash
cd frontend
npm test
```

### Run Tests with Coverage

**Backend:**

```bash
pytest --cov=inventory --cov-report=html
```

**Frontend:**

```bash
cd frontend
npm run test:coverage
```

This generates HTML coverage reports in `htmlcov/` (backend) and `frontend/coverage/` (frontend) directories.

## Running Tests

### Run All Tests

```bash
# Run all tests with verbose output
pytest -v

# Run all tests and show print statements
pytest -s

# Run tests and stop on first failure
pytest -x
```

### Run Specific Test Files

```bash
# Run all model tests
pytest inventory/tests/test_models/

# Run specific test file
pytest inventory/tests/test_models/test_inventory_item.py

# Run specific test class
pytest inventory/tests/test_models/test_inventory_item.py::InventoryItemModelTest

# Run specific test method
pytest inventory/tests/test_models/test_inventory_item.py::InventoryItemModelTest::test_create_inventory_item_minimal
```

### Run Tests by Markers

```bash
# Run only unit tests
pytest -m unit

# Run all tests except slow ones
pytest -m "not slow"

# Run model tests
pytest -m models
```

### Run Tests in Parallel (Future Enhancement)

```bash
# Install pytest-xdist first: pip install pytest-xdist
pytest -n auto  # Use all available CPUs
pytest -n 4     # Use 4 CPUs
```

## Coverage Reports

### Generate Coverage Report

```bash
# HTML report (most detailed, open htmlcov/index.html in browser)
pytest --cov=inventory --cov-report=html

# Terminal report (quick overview)
pytest --cov=inventory --cov-report=term

# Missing lines report (shows which lines need testing)
pytest --cov=inventory --cov-report=term-missing

# XML report (for CI/CD tools)
pytest --cov=inventory --cov-report=xml
```

### Understanding Coverage Reports

**Coverage Metrics:**

- **Statements**: Lines of code executed during tests
- **Branches**: If/else paths taken (branch coverage enabled in .coveragerc)
- **Missing**: Lines not executed by any test

**Coverage Goals:**

- **Current Target**: 80% overall coverage before v1.0 release
- **Critical Modules**: Inventory, Tracker - aim for 90%+
- **Acceptable Lower**: Admin, migrations, config files - can be lower

**Reading HTML Reports:**

1. Open `htmlcov/index.html` in browser
2. Green = covered, Red = not covered, Yellow = partially covered
3. Click module names to see line-by-line coverage
4. Focus on red/yellow lines when writing new tests

### Coverage Configuration

Coverage is configured in `.coveragerc`:

- Source code measured: `inventory`, `backend`
- Excluded: migrations, tests, admin.py, wsgi.py, asgi.py
- Branch coverage: Enabled (tracks if/else paths)
- Fail threshold: Currently 0% (will increase to 80% before v1.0)

## Writing Tests

### Test Structure (AAA Pattern)

All tests follow the **Arrange-Act-Assert** pattern:

```python
def test_create_inventory_item_minimal(self):
    """Test creating an inventory item with only required fields"""
    # ARRANGE: Set up test data (done in setUp or inline)
    # (no additional setup needed here)

    # ACT: Perform the action being tested
    item = InventoryItem.objects.create(title="0.4mm Brass Nozzle")

    # ASSERT: Verify the outcome
    self.assertEqual(item.title, "0.4mm Brass Nozzle")
    self.assertEqual(str(item), "0.4mm Brass Nozzle")
    self.assertEqual(item.quantity, 0)
```

### Test Naming Conventions

- Test files: `test_*.py` (e.g., `test_inventory_item.py`)
- Test classes: `*Test` or `*TestCase` (e.g., `InventoryItemModelTest`)
- Test methods: `test_*` (e.g., `test_create_inventory_item_minimal`)

**Descriptive Names:**

- ✅ `test_inventory_item_quantity_validation`
- ✅ `test_printer_status_choices`
- ❌ `test_item_1`
- ❌ `test_validation`

### Common Test Patterns

**Testing Model Creation:**

```python
def test_create_model_minimal(self):
    """Test creating a model with only required fields"""
    obj = Model.objects.create(required_field="value")
    self.assertEqual(obj.required_field, "value")
```

**Testing Required Fields:**

```python
def test_field_required(self):
    """Test that field is required"""
    from django.db import IntegrityError
    with self.assertRaises(IntegrityError):
        Model.objects.create(required_field=None)
```

**Testing Validation:**

```python
def test_quantity_validation(self):
    """Test that quantity cannot be negative"""
    item = InventoryItem.objects.create(title="Test", quantity=-5)
    with self.assertRaises(ValidationError) as cm:
        item.full_clean()
    self.assertIn('quantity', cm.exception.error_dict)
```

**Testing ForeignKey Relationships:**

```python
def test_fk_set_null_on_delete(self):
    """Test that deleting related object sets FK to null"""
    related = RelatedModel.objects.create(name="Related")
    obj = Model.objects.create(title="Test", related=related)

    related.delete()
    obj.refresh_from_db()
    self.assertIsNone(obj.related)
```

**Testing Ordering:**

```python
def test_ordering(self):
    """Test that models are ordered by title"""
    Model.objects.create(title="Zebra")
    Model.objects.create(title="Alpha")

    items = list(Model.objects.all())
    self.assertEqual(items[0].title, "Alpha")
    self.assertEqual(items[1].title, "Zebra")
```

### Using setUp and tearDown

```python
class MyModelTest(TestCase):
    """Test suite for MyModel"""

    def setUp(self):
        """Create test data used across multiple tests"""
        self.brand = Brand.objects.create(name="Test Brand")
        self.location = Location.objects.create(name="Test Location")

    def tearDown(self):
        """Clean up after tests (usually not needed - Django handles this)"""
        pass  # Django automatically rolls back test database

    def test_something(self):
        """Test uses self.brand and self.location from setUp"""
        item = InventoryItem.objects.create(
            title="Test",
            brand=self.brand,
            location=self.location
        )
        self.assertEqual(item.brand, self.brand)
```

### Testing Best Practices

1. **One Assertion per Test** (ideally, but multiple related assertions OK)
2. **Test One Thing** - Keep tests focused on single behavior
3. **Use Descriptive Docstrings** - Explain what's being tested
4. **Keep Tests Fast** - Avoid unnecessary database queries/file I/O
5. **Use Markers** - Tag slow/integration tests for selective running
6. **Mock External Services** - Don't hit real APIs in tests
7. **Test Edge Cases** - Null values, boundary conditions, error cases

## Test Organization

### Directory Structure

```
inventory/
└── tests/
    ├── __init__.py
    ├── test_models/
    │   ├── __init__.py
    │   ├── test_simple_models.py    # Brand, PartType, Location, Material, Vendor
    │   ├── test_printer.py           # Printer model
    │   └── test_inventory_item.py    # InventoryItem model
    ├── test_serializers/
    │   └── __init__.py
    ├── test_views/
    │   └── __init__.py
    └── test_services/
        └── __init__.py
```

### Test Categories

**Unit Tests** (test_models/, test_serializers/):

- Test individual components in isolation
- Fast, no external dependencies
- Tagged with `@pytest.mark.unit`

**Integration Tests** (test_views/, test_services/):

- Test multiple components working together
- May involve database, file system, or external services
- Tagged with `@pytest.mark.integration`

**Functional Tests** (future):

- Test complete user workflows
- May use Selenium/Playwright for frontend testing

## CI/CD Integration

### GitHub Actions (Planned - Phase 4)

Tests will run automatically on:

- Every push to main branch
- Every pull request
- Scheduled nightly builds

**Workflow Steps:**

1. Set up Python environment
2. Install dependencies
3. Run migrations
4. Run pytest with coverage
5. Upload coverage reports
6. Fail build if coverage < 80%

### Local Pre-Commit Checks (Future Enhancement)

```bash
# Install pre-commit hooks
pre-commit install

# Run checks manually
pre-commit run --all-files
```

## Troubleshooting

### Common Issues

**Import Errors:**

```bash
# Make sure Django settings are configured
export DJANGO_SETTINGS_MODULE=backend.settings
pytest
```

**Database Issues:**

```bash
# pytest-django automatically creates/destroys test database
# If issues persist, manually delete test database:
python manage.py flush --database=test
```

**Coverage Not Measuring Code:**

```bash
# Ensure source paths are correct in .coveragerc
# Ensure you're running pytest with --cov flag
pytest --cov=inventory --cov-report=term-missing
```

**Frontend Tests Not Running:**

```bash
# Make sure you're in the frontend directory
cd frontend

# Reinstall dependencies if needed
npm install

# Run tests
npm test
```

## Frontend Testing (Vue)

### Running Frontend Tests

```bash
cd frontend

# Run all tests (watch mode)
npm test

# Run tests once (CI mode)
npm test -- --run

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- BaseModal.spec.js

# Run tests matching pattern
npm test -- --grep "Close Events"
```

### Frontend Test Structure

Frontend tests use **Vitest** and **@vue/test-utils**. Tests follow the AAA pattern:

```javascript
it("emits close event when close button is clicked", async () => {
  // ARRANGE: Mount component with props
  const wrapper = mount(BaseModal, {
    props: { show: true, title: "Test Modal" },
  });

  // ACT: Trigger the close button click
  await wrapper.find(".close-button").trigger("click");

  // ASSERT: Verify event was emitted
  expect(wrapper.emitted("close")).toBeTruthy();
});
```

### Common Frontend Test Patterns

**Testing Component Visibility:**

```javascript
it("renders when show prop is true", () => {
  const wrapper = mount(Component, { props: { show: true } });
  expect(wrapper.isVisible()).toBe(true);
});
```

**Testing Props:**

```javascript
it("displays the title prop correctly", () => {
  const wrapper = mount(Component, { props: { title: "Test" } });
  expect(wrapper.find("h3").text()).toBe("Test");
});
```

**Testing Events:**

```javascript
it("emits event when button clicked", async () => {
  const wrapper = mount(Component);
  await wrapper.find("button").trigger("click");
  expect(wrapper.emitted("event-name")).toBeTruthy();
});
```

**Testing Slots:**

```javascript
it("renders slot content", () => {
  const wrapper = mount(Component, {
    slots: { default: "<p>Slot content</p>" },
  });
  expect(wrapper.html()).toContain("Slot content");
});
```

**Testing Keyboard Events:**

```javascript
it("handles Escape key", async () => {
  const wrapper = mount(Component, { attachTo: document.body });
  await new Promise((resolve) => setTimeout(resolve, 50)); // Wait for watchers

  const event = new KeyboardEvent("keydown", { key: "Escape" });
  window.dispatchEvent(event);

  expect(wrapper.emitted("close")).toBeTruthy();
});
```

### Frontend Coverage Reports

```bash
cd frontend
npm run test:coverage
```

**Coverage output:**

- HTML: `frontend/coverage/index.html`
- Terminal: Shows % covered for each file
- Goal: 80% coverage on components and composables

### Frontend Test Organization

```
frontend/src/tests/
├── setup.js              # Global test setup (mocks, config)
├── BaseModal.spec.js     # Component tests
├── AboutTab.spec.js      # Component tests (future)
└── ...                   # More component tests
```

## Test Implementation Progress

### Phase 1 ✅ (Completed)
**Backend Model Tests**
- **Tests**: 59 tests covering all models
- **Coverage**: 75.93% → 87.39% models, 47.83% → 100% filters
- **Runtime**: 1.21 seconds
- **Commit**: 0722f45
- **Files**:
  - `inventory/tests/test_models/test_inventory_item.py` (23 tests)
  - `inventory/tests/test_models/test_brand.py` (5 tests)
  - `inventory/tests/test_models/test_part_type.py` (5 tests)
  - `inventory/tests/test_models/test_location.py` (5 tests)
  - `inventory/tests/test_models/test_material.py` (5 tests)
  - `inventory/tests/test_models/test_vendor.py` (5 tests)
  - `inventory/tests/test_models/test_printer.py` (11 tests)

### Phase 2 ✅ (Completed)
**Frontend Component Tests - BaseModal**
- **Tests**: 14 tests (13 passing, 1 skipped - watchEffect timing issue)
- **Coverage**: 85.36% statements, 81.81% branches, 75% functions
- **Runtime**: 494ms
- **Commit**: 0722f45
- **File**: `frontend/src/tests/BaseModal.spec.js`
- **Patterns Established**:
  - Component mounting and unmounting
  - Props validation
  - Event emission testing
  - Slot rendering
  - Keyboard event handling
  - Accessibility structure validation

### Phase 3 ✅ (Completed)
**Critical Path Tests - Backend & Frontend**

**Backend (Commit: 51b474e)**
- **Tests**: 64 new tests (123 total)
- **Coverage**: 
  - Models: 87.39% (exceeded 85% target)
  - Filters: 100% (exceeded 80% target)
  - Overall inventory module: 22.23%
- **Runtime**: 3.17 seconds (1.65s for Phase 3 only)
- **Files**:
  - `inventory/tests/factories.py` - Factory-boy patterns for all models
  - `inventory/tests/test_models/test_tracker.py` (30 tests):
    * Tracker/TrackerFile model creation
    * Computed properties (total_count, completed_count, etc.)
    * Statistics and progress calculations
    * GitHub URL handling
    * Storage types and directory structures
  - `inventory/tests/test_views/test_inventory_viewset.py` (16 tests):
    * CRUD operations (list, retrieve, create, update, delete)
    * Filtering (brand, part_type, location)
    * Search functionality
    * Ordering
    * Low stock endpoint
    * Project associations
  - `inventory/tests/test_views/test_tracker_viewset.py` (18 tests):
    * CRUD operations
    * Filtering by project
    * Search (name, GitHub URL)
    * Serializer depth differences (list vs detail)
    * TrackerFile sub-endpoints
    * Cascade deletes

**Frontend (Commit: 67e6e8b)**
- **Tests**: 35 new tests (49 total)
- **Coverage**:
  - APIService: 56.48% (method existence validation)
  - BaseModal: 85.36% (maintained from Phase 2)
- **Runtime**: 2.63 seconds (540ms for APIService only)
- **File**: `frontend/src/tests/services/APIService.spec.js`
- **Test Approach**: Simplified method existence tests due to axios.create() module-level timing issues with Vitest mocking
- **Methods Tested**:
  - Inventory Items: 5 methods (CRUD + list)
  - Trackers: 6 methods (CRUD + list + download)
  - Tracker Files: 3 methods (list, update status, delete)
  - Projects: 6 methods (CRUD + list + download)
  - Printers: 5 methods (CRUD + list)
  - Lookups: 5 methods (brands, part types, locations, materials, vendors)
  - Mods: 4 methods (CRUD)
  - GitHub Integration: 1 method (crawl)

**Phase 3 Key Decisions:**
- ✅ Used factory-boy + Faker for efficient test data generation (reduced boilerplate significantly)
- ✅ Fixed pagination assumptions in ViewSet tests (API returns lists directly, not paginated results)
- ✅ Simplified APIService tests to method existence checks (avoids complex axios mocking issues)
- ⚠️ Deferred complex view component tests (TrackerDetailView, InventoryListView) to Phase 5:
  - TrackerDetailView: 2119 lines with extensive router dependencies and child components
  - Better suited for E2E/integration testing approach
  - Phase 3 established testing patterns with simpler components first

**Phase 3 Totals:**
- **Backend**: 123 tests passing (3.17s runtime)
- **Frontend**: 49 tests (48 passing + 1 skipped) (2.63s runtime)
- **Combined**: 172 tests across full stack (5.80s total runtime)

### Phase 4 (Next)
**CI/CD Pipeline**
- GitHub Actions workflow for automated testing
- Backend job: pytest with requirements-dev.txt
- Frontend job: npm test
- Coverage reporting and quality gates (70%+ minimum)
- Parallel execution for speed

### Phase 5 (Planned)
**Comprehensive Coverage - 80%+ Target**
- Expand serializer tests (currently 50.29% coverage)
- Service layer tests:
  - `github_service.py` (11.93% coverage)
  - `file_download_service.py` (8.58% coverage)
  - `storage_manager.py` (12.21% coverage)
- Views comprehensive testing (currently 10.35% coverage)
- Complex component testing:
  - TrackerDetailView (E2E/integration approach)
  - InventoryListView (routing + filtering integration)
- Feature-level integration tests
- Performance and load testing

## Resources

**Backend Testing:**

- [pytest documentation](https://docs.pytest.org/)
- [pytest-django documentation](https://pytest-django.readthedocs.io/)
- [Django testing guide](https://docs.djangoproject.com/en/5.2/topics/testing/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)

**Frontend Testing:**

- [Vitest documentation](https://vitest.dev/)
- [Vue Test Utils documentation](https://test-utils.vuejs.org/)
- [Testing Vue Components Guide](https://vuejs.org/guide/scaling-up/testing.html)
