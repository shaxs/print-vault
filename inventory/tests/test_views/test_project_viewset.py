"""
Tests for Project ViewSet API endpoints.

Covers CRUD operations, filtering, search, ordering, and BOM field inclusion.
Uses pytest-django and factory-boy for efficient test setup.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import Project
from inventory.tests.factories import (
    ProjectFactory,
    InventoryItemFactory,
    PrinterFactory,
    ProjectBOMItemFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


# ============================================================================
# LIST
# ============================================================================

class TestProjectList:

    def test_list_returns_200(self, db, api_client):
        """GET /api/projects/ returns HTTP 200."""
        response = api_client.get('/api/projects/')
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_all_projects(self, db, api_client):
        """Projects list contains all created projects."""
        ProjectFactory.create_batch(3)
        response = api_client.get('/api/projects/')
        assert len(response.data) == 3

    def test_list_ordered_by_name(self, db, api_client):
        """Projects are returned ordered alphabetically by project_name."""
        ProjectFactory(project_name="Zebra Project")
        ProjectFactory(project_name="Alpha Project")
        ProjectFactory(project_name="Middle Project")
        response = api_client.get('/api/projects/')
        names = [p['project_name'] for p in response.data]
        assert names == sorted(names)

    def test_list_includes_bom_items_field(self, db, api_client):
        """Each project in list includes bom_items field."""
        ProjectFactory()
        response = api_client.get('/api/projects/')
        assert 'bom_items' in response.data[0]

    def test_list_empty_when_no_projects(self, db, api_client):
        """Returns empty list when no projects exist."""
        response = api_client.get('/api/projects/')
        assert response.data == []


# ============================================================================
# CREATE
# ============================================================================

class TestProjectCreate:

    def test_create_minimal_project(self, db, api_client):
        """POST with only project_name creates a project."""
        response = api_client.post('/api/projects/', {'project_name': 'New Project'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Project.objects.filter(project_name='New Project').exists()

    def test_create_project_with_all_fields(self, db, api_client):
        """POST with all fields creates project correctly."""
        payload = {
            'project_name': 'Full Project',
            'description': 'A detailed description',
            'status': 'Planning',
            'notes': 'Some notes',
        }
        response = api_client.post('/api/projects/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        project = Project.objects.get(pk=response.data['id'])
        assert project.description == 'A detailed description'
        assert project.status == 'Planning'

    def test_create_returns_bom_items_field(self, db, api_client):
        """Created project response includes bom_items field."""
        response = api_client.post('/api/projects/', {'project_name': 'BOM Test'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'bom_items' in response.data
        assert response.data['bom_items'] == []

    def test_create_missing_name_returns_400(self, db, api_client):
        """POST without project_name returns 400."""
        response = api_client.post('/api/projects/', {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# RETRIEVE
# ============================================================================

class TestProjectRetrieve:

    def test_retrieve_existing_project(self, db, api_client):
        """GET /api/projects/{id}/ returns the project."""
        project = ProjectFactory(project_name="My Project")
        response = api_client.get(f'/api/projects/{project.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['project_name'] == "My Project"

    def test_retrieve_nonexistent_project_returns_404(self, db, api_client):
        """GET for a non-existent project ID returns 404."""
        response = api_client.get('/api/projects/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_includes_bom_items(self, db, api_client):
        """Retrieved project includes bom_items populated from DB."""
        project = ProjectFactory()
        bom_items = ProjectBOMItemFactory.create_batch(3, project=project)
        response = api_client.get(f'/api/projects/{project.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['bom_items']) == 3

    def test_retrieve_includes_associated_inventory(self, db, api_client):
        """Retrieved project includes associated_inventory_items."""
        project = ProjectFactory()
        item = InventoryItemFactory()
        project.associated_inventory_items.add(item)
        response = api_client.get(f'/api/projects/{project.id}/')
        assert response.status_code == status.HTTP_200_OK
        ids = [i['id'] for i in response.data['associated_inventory_items']]
        assert item.id in ids


# ============================================================================
# UPDATE
# ============================================================================

class TestProjectUpdate:

    def test_patch_updates_field(self, db, api_client):
        """PATCH updates a single field without affecting others."""
        project = ProjectFactory(project_name="Old Name", status='Planning')
        response = api_client.patch(f'/api/projects/{project.id}/', {'project_name': 'New Name'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        project.refresh_from_db()
        assert project.project_name == 'New Name'
        assert project.status == 'Planning'  # unchanged

    def test_put_replaces_project(self, db, api_client):
        """PUT replaces all updatable fields."""
        project = ProjectFactory(project_name="Original", notes="Some note")
        response = api_client.put(
            f'/api/projects/{project.id}/',
            {'project_name': 'Replaced', 'notes': ''},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        project.refresh_from_db()
        assert project.project_name == 'Replaced'

    def test_patch_nonexistent_returns_404(self, db, api_client):
        """PATCH on a non-existent project returns 404."""
        response = api_client.patch('/api/projects/99999/', {'project_name': 'X'}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# DELETE
# ============================================================================

class TestProjectDelete:

    def test_delete_removes_project(self, db, api_client):
        """DELETE removes the project from the database."""
        project = ProjectFactory()
        pk = project.id
        response = api_client.delete(f'/api/projects/{pk}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Project.objects.filter(pk=pk).exists()

    def test_delete_nonexistent_returns_404(self, db, api_client):
        """DELETE on a non-existent project returns 404."""
        response = api_client.delete('/api/projects/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_also_removes_bom_items(self, db, api_client):
        """Deleting a project cascades to its BOM items."""
        from inventory.models import ProjectBOMItem
        project = ProjectFactory()
        ProjectBOMItemFactory.create_batch(2, project=project)
        pk = project.id
        api_client.delete(f'/api/projects/{pk}/')
        assert not ProjectBOMItem.objects.filter(project_id=pk).exists()


# ============================================================================
# SEARCH & FILTER
# ============================================================================

class TestProjectSearchFilter:

    def test_search_by_name(self, db, api_client):
        """Search filter narrows results by project_name."""
        ProjectFactory(project_name="Voron Build")
        ProjectFactory(project_name="Ender Upgrade")
        response = api_client.get('/api/projects/?search=Voron')
        assert len(response.data) == 1
        assert response.data[0]['project_name'] == "Voron Build"

    def test_search_by_status(self, db, api_client):
        """Search filter works on status field."""
        ProjectFactory(project_name="In Progress One", status='In Progress')
        ProjectFactory(project_name="Planning One", status='Planning')
        response = api_client.get('/api/projects/?search=In+Progress')
        names = [p['project_name'] for p in response.data]
        assert "In Progress One" in names
        assert "Planning One" not in names

    def test_order_by_project_name_desc(self, db, api_client):
        """Ordering by -project_name returns projects in reverse alphabetical order."""
        ProjectFactory(project_name="Alpha")
        ProjectFactory(project_name="Zebra")
        response = api_client.get('/api/projects/?ordering=-project_name')
        names = [p['project_name'] for p in response.data]
        assert names[0] == "Zebra"
        assert names[-1] == "Alpha"
