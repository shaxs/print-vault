"""
Tests for DashboardDataView — GET /api/dashboard/

Covers:
- Basic response structure (200, keys present)
- _get_active_projects() health status logic:
    - healthy (no issues)
    - at-risk (due within 7 days)
    - overdue (past due date)
    - blocked (ALL printers unavailable)
    - partially-blocked (SOME but not all printers unavailable)
    - priority ordering (overdue > blocked > partially-blocked > at-risk > healthy)
"""
import pytest
from datetime import date, timedelta
from rest_framework import status
from rest_framework.test import APIClient
from inventory.tests.factories import ProjectFactory, PrinterFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def today():
    return date.today()


# ============================================================================
# BASIC RESPONSE STRUCTURE
# ============================================================================

class TestDashboardResponseStructure:

    def test_returns_200(self, db, api_client):
        """GET /api/dashboard/ returns HTTP 200."""
        response = api_client.get('/api/dashboard/')
        assert response.status_code == status.HTTP_200_OK

    def test_response_has_required_keys(self, db, api_client):
        """Dashboard response contains all expected top-level keys."""
        response = api_client.get('/api/dashboard/')
        keys = response.data.keys()
        assert 'alerts' in keys
        assert 'stats' in keys
        assert 'active_projects' in keys

    def test_stats_has_counts(self, db, api_client):
        """Stats block contains inventory, printer, project, and tracker counts."""
        response = api_client.get('/api/dashboard/')
        stats = response.data['stats']
        assert 'inventory_count' in stats
        assert 'printer_count' in stats
        assert 'project_count' in stats

    def test_active_projects_is_list(self, db, api_client):
        """active_projects is returned as a list."""
        response = api_client.get('/api/dashboard/')
        assert isinstance(response.data['active_projects'], list)

    def test_only_in_progress_projects_appear(self, db, api_client):
        """Only 'In Progress' projects appear in active_projects; Planning, Completed are excluded."""
        ProjectFactory(status='In Progress', project_name="Active Project")
        ProjectFactory(status='Planning', project_name="Planning Project")
        ProjectFactory(status='Completed', project_name="Completed Project")
        response = api_client.get('/api/dashboard/')
        names = [p['name'] for p in response.data['active_projects']]
        assert "Active Project" in names
        assert "Planning Project" not in names
        assert "Completed Project" not in names


# ============================================================================
# HEALTH STATUS — HEALTHY
# ============================================================================

class TestHealthStatusHealthy:

    def test_project_with_no_issues_is_healthy(self, db, api_client):
        """Project with no printers and no due date is healthy."""
        ProjectFactory(status='In Progress')
        response = api_client.get('/api/dashboard/')
        projects = response.data['active_projects']
        assert len(projects) == 1
        assert projects[0]['health'] == 'healthy'

    def test_healthy_is_primary_when_no_issues(self, db, api_client, today):
        """Project with an active printer and future due date (>7 days) is healthy."""
        printer = PrinterFactory(status='Active')
        project = ProjectFactory(
            status='In Progress',
            due_date=today + timedelta(days=30),
        )
        project.associated_printers.add(printer)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'healthy'


# ============================================================================
# HEALTH STATUS — AT-RISK
# ============================================================================

class TestHealthStatusAtRisk:

    def test_project_due_within_7_days_is_at_risk(self, db, api_client, today):
        """Project due in 5 days is 'at-risk'."""
        project = ProjectFactory(
            status='In Progress',
            due_date=today + timedelta(days=5),
        )
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'at-risk'

    def test_project_due_exactly_7_days_is_at_risk(self, db, api_client, today):
        """Project due exactly today+7 days is 'at-risk'."""
        project = ProjectFactory(
            status='In Progress',
            due_date=today + timedelta(days=7),
        )
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'at-risk'

    def test_project_due_8_days_is_healthy(self, db, api_client, today):
        """Project due in 8 days is healthy (not yet at-risk)."""
        project = ProjectFactory(
            status='In Progress',
            due_date=today + timedelta(days=8),
        )
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'healthy'


# ============================================================================
# HEALTH STATUS — OVERDUE
# ============================================================================

class TestHealthStatusOverdue:

    def test_project_past_due_date_is_overdue(self, db, api_client, today):
        """Project whose due_date is yesterday is 'overdue'."""
        project = ProjectFactory(
            status='In Progress',
            due_date=today - timedelta(days=1),
        )
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'overdue'

    def test_project_with_no_due_date_is_not_overdue(self, db, api_client):
        """Project with no due_date is not overdue."""
        project = ProjectFactory(status='In Progress', due_date=None)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] != 'overdue'


# ============================================================================
# HEALTH STATUS — BLOCKED (all printers unavailable)
# ============================================================================

class TestHealthStatusBlocked:

    @pytest.mark.parametrize("blocking_status", ['Under Repair', 'Sold', 'Archived'])
    def test_project_fully_blocked_when_single_printer_unavailable(
        self, db, api_client, blocking_status
    ):
        """Single printer with a blocking status → project is 'blocked'."""
        printer = PrinterFactory(status=blocking_status)
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(printer)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'blocked'

    def test_project_blocked_when_all_printers_unavailable(self, db, api_client):
        """Project with 2 printers, both Under Repair → 'blocked'."""
        printer_a = PrinterFactory(status='Under Repair')
        printer_b = PrinterFactory(status='Sold')
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(printer_a, printer_b)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'blocked'


# ============================================================================
# HEALTH STATUS — PARTIALLY BLOCKED (some printers unavailable)
# ============================================================================

class TestHealthStatusPartiallyBlocked:

    def test_project_partially_blocked_when_one_of_two_printers_unavailable(
        self, db, api_client
    ):
        """Project with 2 printers — 1 active, 1 under repair — is 'partially-blocked'."""
        printer_active = PrinterFactory(status='Active')
        printer_repair = PrinterFactory(status='Under Repair')
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(printer_active, printer_repair)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'partially-blocked'

    def test_partially_blocked_includes_count_in_health_reason(self, db, api_client):
        """health_reason for partially-blocked includes 'X of Y printers unavailable'."""
        printer_active = PrinterFactory(status='Active')
        printer_sold = PrinterFactory(status='Sold')
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(printer_active, printer_sold)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        reason = projects[0]['health_reason']
        assert 'of' in reason
        assert 'printers unavailable' in reason

    def test_project_with_all_active_printers_is_healthy(self, db, api_client):
        """Project with 2 active printers is healthy (not partially blocked)."""
        printer_a = PrinterFactory(status='Active')
        printer_b = PrinterFactory(status='Active')
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(printer_a, printer_b)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'healthy'

    def test_partially_blocked_with_three_printers_one_down(self, db, api_client):
        """3 printers, 1 under repair → partially-blocked (not blocked)."""
        p1 = PrinterFactory(status='Active')
        p2 = PrinterFactory(status='Active')
        p3 = PrinterFactory(status='Archived')
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(p1, p2, p3)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'partially-blocked'

    def test_partially_blocked_health_statuses_includes_flag(self, db, api_client):
        """health_statuses list contains 'partially-blocked' entry."""
        printer_active = PrinterFactory(status='Active')
        printer_repair = PrinterFactory(status='Under Repair')
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(printer_active, printer_repair)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert 'partially-blocked' in projects[0]['health_statuses']


# ============================================================================
# PRIORITY ORDERING
# ============================================================================

class TestHealthPriorityOrdering:

    def test_overdue_beats_blocked(self, db, api_client, today):
        """Project that is both overdue and fully blocked → primary health is 'overdue'."""
        printer = PrinterFactory(status='Under Repair')
        project = ProjectFactory(
            status='In Progress',
            due_date=today - timedelta(days=3),
        )
        project.associated_printers.add(printer)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'overdue'

    def test_blocked_beats_partially_blocked(self, db, api_client):
        """All printers blocked → 'blocked', not 'partially-blocked'."""
        printer_a = PrinterFactory(status='Under Repair')
        printer_b = PrinterFactory(status='Sold')
        project = ProjectFactory(status='In Progress')
        project.associated_printers.add(printer_a, printer_b)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'blocked'

    def test_partially_blocked_beats_at_risk(self, db, api_client, today):
        """Project partially blocked AND at-risk → primary health is 'partially-blocked'."""
        printer_active = PrinterFactory(status='Active')
        printer_repair = PrinterFactory(status='Under Repair')
        project = ProjectFactory(
            status='In Progress',
            due_date=today + timedelta(days=3),
        )
        project.associated_printers.add(printer_active, printer_repair)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'partially-blocked'
        # at-risk should still be present in health_statuses
        assert 'at-risk' in projects[0]['health_statuses']

    def test_overdue_beats_partially_blocked(self, db, api_client, today):
        """Project that is both overdue and partially blocked → primary health is 'overdue'."""
        printer_active = PrinterFactory(status='Active')
        printer_repair = PrinterFactory(status='Under Repair')
        project = ProjectFactory(
            status='In Progress',
            due_date=today - timedelta(days=2),
        )
        project.associated_printers.add(printer_active, printer_repair)
        response = api_client.get('/api/dashboard/')
        projects = [p for p in response.data['active_projects'] if p['id'] == project.id]
        assert projects[0]['health'] == 'overdue'
