"""
Tests for FilamentSpool ViewSet API endpoints.

Tests CRUD operations, filtering, search, custom actions (split, open-spool,
update-weight, mark-empty, archive), and both Blueprint and Quick Add modes.
Uses pytest-django and factory-boy for efficient test setup.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import FilamentSpool, Material
from inventory.tests.factories import (
    FilamentSpoolFactory,
    QuickAddSpoolFactory,
    FilamentBlueprintMaterialFactory,
    GenericMaterialFactory,
    BrandFactory,
    LocationFactory,
    PrinterFactory,
    ProjectFactory
)


@pytest.fixture
def api_client():
    """Provide an API client for making requests."""
    return APIClient()


@pytest.fixture
def generic_pla(db):
    """Get or create a generic PLA material type."""
    pla, _ = Material.objects.get_or_create(name='PLA', defaults={'is_generic': True})
    return pla


@pytest.fixture
def sample_blueprint_spools(db, generic_pla):
    """Create sample blueprint-based spools for testing."""
    brand = BrandFactory(name="Polymaker")
    location1 = LocationFactory(name="Filament Rack")
    location2 = LocationFactory(name="Dry Box")
    printer = PrinterFactory(title="Prusa MK4")
    project = ProjectFactory(project_name="Test Project")
    
    # Create a filament blueprint (Material with is_generic=False)
    blueprint, _ = Material.objects.get_or_create(
        name="PolyTerra PLA",
        defaults={
            "is_generic": False,
            "brand": brand,
            "base_material": generic_pla,
            "diameter": "1.75",
            "spool_weight": 1000,
            "price_per_spool": Decimal("24.99")
        }
    )
    
    # Create spools with various statuses
    spool_new = FilamentSpoolFactory(
        filament_type=blueprint,
        quantity=3,
        is_opened=False,
        initial_weight=1000,
        current_weight=1000,
        location=location1,
        status='new'
    )
    
    spool_opened = FilamentSpoolFactory(
        filament_type=blueprint,
        quantity=1,
        is_opened=True,
        initial_weight=1000,
        current_weight=750,
        location=location1,
        status='opened'
    )
    
    spool_in_use = FilamentSpoolFactory(
        filament_type=blueprint,
        quantity=1,
        is_opened=True,
        initial_weight=1000,
        current_weight=500,
        location=None,
        assigned_printer=printer,
        status='in_use'
    )
    
    spool_low = FilamentSpoolFactory(
        filament_type=blueprint,
        quantity=1,
        is_opened=True,
        initial_weight=1000,
        current_weight=150,
        location=location2,
        status='low'
    )
    
    spool_empty = FilamentSpoolFactory(
        filament_type=blueprint,
        quantity=1,
        is_opened=True,
        initial_weight=1000,
        current_weight=0,
        location=location2,
        status='empty'
    )
    
    return {
        'spools': [spool_new, spool_opened, spool_in_use, spool_low, spool_empty],
        'spool_new': spool_new,
        'spool_opened': spool_opened,
        'spool_in_use': spool_in_use,
        'spool_low': spool_low,
        'spool_empty': spool_empty,
        'blueprint': blueprint,
        'brand': brand,
        'locations': [location1, location2],
        'printer': printer,
        'project': project
    }


@pytest.fixture
def quick_add_spool(db, generic_pla):
    """Create a Quick Add spool (no blueprint)."""
    brand = BrandFactory(name="Unknown Brand")
    location = LocationFactory(name="Quick Storage")
    
    return QuickAddSpoolFactory(
        standalone_name="Convention Special Blue",
        standalone_brand=brand,
        standalone_material_type=generic_pla,
        standalone_colors=["#0066CC", "#003366"],
        standalone_color_family="blue",
        initial_weight=750,
        current_weight=750,
        location=location,
        price_paid=Decimal("15.00")
    )


# ============================================================================
# CRUD OPERATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestFilamentSpoolCRUD:
    """Test Create, Read, Update, Delete operations."""
    
    def test_list_filament_spools(self, api_client, sample_blueprint_spools):
        """Test listing all filament spools."""
        url = '/api/filament-spools/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5
    
    def test_retrieve_filament_spool(self, api_client, sample_blueprint_spools):
        """Test retrieving a single filament spool."""
        spool = sample_blueprint_spools['spool_new']
        url = f'/api/filament-spools/{spool.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == spool.pk
        assert response.data['quantity'] == 3
        assert response.data['status'] == 'new'
        assert response.data['is_quick_add'] == False
    
    def test_retrieve_quick_add_spool(self, api_client, quick_add_spool):
        """Test retrieving a Quick Add spool."""
        url = f'/api/filament-spools/{quick_add_spool.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_quick_add'] == True
        assert response.data['standalone_name'] == "Convention Special Blue"
        assert response.data['standalone_colors'] == ["#0066CC", "#003366"]
        assert response.data['price_paid'] == "15.00"
    
    def test_create_blueprint_spool(self, api_client, sample_blueprint_spools):
        """Test creating a new blueprint-based spool."""
        blueprint = sample_blueprint_spools['blueprint']
        location = sample_blueprint_spools['locations'][0]
        
        url = '/api/filament-spools/'
        data = {
            'filament_type_id': blueprint.pk,
            'quantity': 2,
            'is_opened': False,
            'initial_weight': 1000,
            'current_weight': 1000,
            'location_id': location.pk,
            'status': 'new'
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['quantity'] == 2
        assert response.data['is_quick_add'] == False
    
    def test_create_quick_add_spool(self, api_client, generic_pla):
        """Test creating a new Quick Add spool."""
        brand = BrandFactory(name="Test Brand")
        location = LocationFactory(name="Test Location")
        
        url = '/api/filament-spools/'
        data = {
            'is_quick_add': True,  # Flag required for Quick Add mode
            'standalone_name': 'Test Quick Add',
            'standalone_brand': {'name': brand.name},
            'standalone_material_type_id': generic_pla.pk,
            'standalone_colors': ['#FF0000'],
            'standalone_color_family': 'red',
            'quantity': 1,
            'is_opened': False,
            'initial_weight': 800,
            'current_weight': 800,
            'location': {'name': location.name},
            'status': 'new',
            'price_paid': '12.50'
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['is_quick_add'] == True
        assert response.data['standalone_name'] == 'Test Quick Add'
        assert response.data['price_paid'] == '12.50'
    
    def test_update_filament_spool(self, api_client, sample_blueprint_spools):
        """Test updating a filament spool."""
        spool = sample_blueprint_spools['spool_opened']
        
        url = f'/api/filament-spools/{spool.pk}/'
        data = {
            'current_weight': 600,
            'notes': 'Used for test print'
        }
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['current_weight'] == 600
        assert response.data['notes'] == 'Used for test print'
    
    def test_delete_filament_spool(self, api_client, sample_blueprint_spools):
        """Test deleting a filament spool."""
        spool = sample_blueprint_spools['spool_empty']
        
        url = f'/api/filament-spools/{spool.pk}/'
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not FilamentSpool.objects.filter(pk=spool.pk).exists()


# ============================================================================
# FILTERING TESTS
# ============================================================================

@pytest.mark.django_db
class TestFilamentSpoolFiltering:
    """Test filtering and search functionality."""
    
    def test_filter_by_status(self, api_client, sample_blueprint_spools):
        """Test filtering spools by status."""
        url = '/api/filament-spools/?status=in_use'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['status'] == 'in_use'
    
    def test_filter_by_printer(self, api_client, sample_blueprint_spools):
        """Test filtering spools by assigned printer."""
        printer = sample_blueprint_spools['printer']
        url = f'/api/filament-spools/?printer={printer.pk}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['assigned_printer']['id'] == printer.pk
    
    def test_filter_active_status(self, api_client, sample_blueprint_spools):
        """Test filtering by active status (excludes empty/archived)."""
        url = '/api/filament-spools/?status=active'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Should include: new, opened, in_use, low (4 total)
        # Should exclude: empty (1)
        for spool in response.data:
            assert spool['status'] not in ['empty', 'archived']


# ============================================================================
# CUSTOM ACTION TESTS
# ============================================================================

@pytest.mark.django_db
class TestFilamentSpoolSplit:
    """Test the split action for unopened spools."""
    
    def test_split_spool_success(self, api_client, sample_blueprint_spools):
        """Test successfully splitting an unopened spool batch."""
        spool = sample_blueprint_spools['spool_new']
        original_quantity = spool.quantity
        
        url = f'/api/filament-spools/{spool.pk}/split/'
        data = {'split_count': 1}  # API uses split_count not initial_weight
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, response.data
        
        # Check that original spool quantity decreased
        spool.refresh_from_db()
        assert spool.quantity == original_quantity - 1
    
    def test_split_opened_spool_fails(self, api_client, sample_blueprint_spools):
        """Test that splitting an already-opened spool fails."""
        spool = sample_blueprint_spools['spool_opened']
        
        url = f'/api/filament-spools/{spool.pk}/split/'
        data = {'split_count': 1}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot split opened' in response.data['error'].lower()
    
    def test_split_last_spool_fails(self, api_client, db, generic_pla):
        """Test that splitting a spool with quantity=1 fails (need qty > 1)."""
        blueprint = FilamentBlueprintMaterialFactory(base_material=generic_pla)
        location = LocationFactory()
        
        spool = FilamentSpoolFactory(
            filament_type=blueprint,
            quantity=1,  # Only 1 spool
            is_opened=False,
            initial_weight=1000,
            current_weight=1000,
            location=location,
            status='new'
        )
        
        url = f'/api/filament-spools/{spool.pk}/split/'
        data = {'split_count': 1}
        response = api_client.post(url, data, format='json')
        
        # API requires quantity > 1 to split
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'quantity must be > 1' in response.data['error'].lower()


@pytest.mark.django_db
class TestFilamentSpoolOpenSpool:
    """Test the open-spool action for batch splitting."""
    
    def test_open_spool_single(self, api_client, sample_blueprint_spools):
        """Test opening a single spool from a batch."""
        spool = sample_blueprint_spools['spool_new']
        original_quantity = spool.quantity
        location = sample_blueprint_spools['locations'][0]
        
        url = f'/api/filament-spools/{spool.pk}/open-spool/'
        data = {
            'spools_to_open': [  # API uses spools_to_open not spools
                {
                    'status': 'opened',
                    'location_id': location.pk,
                    'printer_id': None
                }
            ]
        }
        response = api_client.post(url, data, format='json')
        
        # API returns 201 CREATED for newly created spools
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert len(response.data['opened_spools']) == 1
        
        # Check original quantity decreased
        spool.refresh_from_db()
        assert spool.quantity == original_quantity - 1
    
    def test_open_spool_multiple(self, api_client, sample_blueprint_spools):
        """Test opening multiple spools from a batch at once."""
        spool = sample_blueprint_spools['spool_new']
        original_quantity = spool.quantity
        location1 = sample_blueprint_spools['locations'][0]
        location2 = sample_blueprint_spools['locations'][1]
        printer = sample_blueprint_spools['printer']
        
        url = f'/api/filament-spools/{spool.pk}/open-spool/'
        data = {
            'spools_to_open': [  # API uses spools_to_open not spools
                {
                    'status': 'opened',
                    'location_id': location1.pk,
                    'printer_id': None
                },
                {
                    'status': 'in_use',
                    'location_id': None,
                    'printer_id': printer.pk
                }
            ]
        }
        response = api_client.post(url, data, format='json')
        
        # API returns 201 CREATED for newly created spools
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert len(response.data['opened_spools']) == 2
        
        # Check original quantity decreased by 2
        spool.refresh_from_db()
        assert spool.quantity == original_quantity - 2
    
    def test_open_spool_exceeds_quantity(self, api_client, sample_blueprint_spools):
        """Test that opening more spools than available fails."""
        spool = sample_blueprint_spools['spool_new']
        location = sample_blueprint_spools['locations'][0]
        
        url = f'/api/filament-spools/{spool.pk}/open-spool/'
        data = {
            'spools_to_open': [  # API uses spools_to_open
                {'status': 'opened', 'location_id': location.pk, 'printer_id': None}
                for _ in range(10)  # Try to open 10 spools
            ]
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_open_spool_opened_batch_fails(self, api_client, sample_blueprint_spools):
        """Test that open-spool fails on already-opened spool (status not 'new')."""
        spool = sample_blueprint_spools['spool_opened']
        
        url = f'/api/filament-spools/{spool.pk}/open-spool/'
        data = {
            'spools_to_open': [
                {'status': 'opened', 'location_id': None, 'printer_id': None}
            ]
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFilamentSpoolUpdateWeight:
    """Test the update-weight action."""
    
    def test_update_weight_success(self, api_client, sample_blueprint_spools):
        """Test updating spool weight."""
        spool = sample_blueprint_spools['spool_opened']
        
        url = f'/api/filament-spools/{spool.pk}/update-weight/'
        data = {'current_weight': 400}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        spool.refresh_from_db()
        assert spool.current_weight == 400
    
    def test_update_weight_auto_status_low(self, api_client, sample_blueprint_spools):
        """Test that weight update auto-sets status to 'low' at <20%."""
        spool = sample_blueprint_spools['spool_opened']
        
        url = f'/api/filament-spools/{spool.pk}/update-weight/'
        data = {'current_weight': 150}  # 15% of 1000g
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        spool.refresh_from_db()
        assert spool.status == 'low'
    
    def test_update_weight_auto_status_empty(self, api_client, sample_blueprint_spools):
        """Test that weight update auto-sets status to 'empty' at 0g."""
        spool = sample_blueprint_spools['spool_opened']
        
        url = f'/api/filament-spools/{spool.pk}/update-weight/'
        data = {'current_weight': 0}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        spool.refresh_from_db()
        assert spool.status == 'empty'


@pytest.mark.django_db
class TestFilamentSpoolMarkEmpty:
    """Test the mark-empty action."""
    
    def test_mark_empty_success(self, api_client, sample_blueprint_spools):
        """Test marking a spool as empty."""
        spool = sample_blueprint_spools['spool_low']
        
        url = f'/api/filament-spools/{spool.pk}/mark-empty/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        spool.refresh_from_db()
        assert spool.current_weight == 0
        assert spool.status == 'empty'
        assert spool.date_emptied is not None


@pytest.mark.django_db
class TestFilamentSpoolArchive:
    """Test the archive action."""
    
    def test_archive_empty_spool(self, api_client, sample_blueprint_spools):
        """Test archiving an empty spool."""
        spool = sample_blueprint_spools['spool_empty']
        
        url = f'/api/filament-spools/{spool.pk}/archive/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        spool.refresh_from_db()
        assert spool.status == 'archived'
        assert spool.date_archived is not None
    
    def test_archive_non_empty_spool_fails(self, api_client, sample_blueprint_spools):
        """Test that archiving a non-empty spool fails."""
        spool = sample_blueprint_spools['spool_opened']
        
        url = f'/api/filament-spools/{spool.pk}/archive/'
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db  
class TestFilamentSpoolBulkArchive:
    """Test the bulk-archive action."""
    
    def test_bulk_archive_success(self, api_client, db, generic_pla):
        """Test bulk archiving multiple empty spools."""
        blueprint = FilamentBlueprintMaterialFactory(base_material=generic_pla)
        
        empty1 = FilamentSpoolFactory(
            filament_type=blueprint,
            is_opened=True,
            current_weight=0,
            status='empty'
        )
        empty2 = FilamentSpoolFactory(
            filament_type=blueprint,
            is_opened=True,
            current_weight=0,
            status='empty'
        )
        
        url = '/api/filament-spools/bulk-archive/'
        data = {'spool_ids': [empty1.pk, empty2.pk]}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        empty1.refresh_from_db()
        empty2.refresh_from_db()
        assert empty1.status == 'archived'
        assert empty2.status == 'archived'


# ============================================================================
# COMPUTED FIELD TESTS
# ============================================================================

@pytest.mark.django_db
class TestFilamentSpoolComputedFields:
    """Test computed/read-only fields in responses."""
    
    def test_weight_remaining_percent(self, api_client, sample_blueprint_spools):
        """Test that weight_remaining_percent is calculated correctly."""
        spool = sample_blueprint_spools['spool_in_use']  # 500/1000 = 50%
        
        url = f'/api/filament-spools/{spool.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['weight_remaining_percent'] == 50.0
    
    def test_display_name_blueprint(self, api_client, sample_blueprint_spools):
        """Test display_name for blueprint-based spool."""
        spool = sample_blueprint_spools['spool_new']
        
        url = f'/api/filament-spools/{spool.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # display_name should contain blueprint name
        assert 'PolyTerra' in response.data['display_name']
    
    def test_display_name_quick_add(self, api_client, quick_add_spool):
        """Test display_name for Quick Add spool."""
        url = f'/api/filament-spools/{quick_add_spool.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['display_name'] == "Convention Special Blue"
    
    def test_is_quick_add_flag(self, api_client, sample_blueprint_spools, quick_add_spool):
        """Test is_quick_add computed field."""
        blueprint_spool = sample_blueprint_spools['spool_new']
        
        # Blueprint spool
        url = f'/api/filament-spools/{blueprint_spool.pk}/'
        response = api_client.get(url)
        assert response.data['is_quick_add'] == False
        
        # Quick Add spool
        url = f'/api/filament-spools/{quick_add_spool.pk}/'
        response = api_client.get(url)
        assert response.data['is_quick_add'] == True
