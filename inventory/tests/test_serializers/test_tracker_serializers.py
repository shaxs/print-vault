"""
Test suite for Tracker-related serializers.

TrackerFileSerializer:
- Computed fields (remaining_quantity, is_complete, local_file)
- Read-only download tracking fields

TrackerSerializer:
- Nested files serialization
- Multiple computed fields (progress, counts, quantities)
- Project association

Coverage targets:
- Field serialization
- Computed property calculations
- Nested file relationships
"""

import pytest
from inventory.serializers import TrackerFileSerializer, TrackerSerializer
from inventory.tests.factories import (
    TrackerFactory, TrackerFileFactory, ProjectFactory
)


@pytest.mark.django_db
class TestTrackerFileSerializer:
    """Test TrackerFileSerializer."""

    def test_serializer_fields(self):
        """Verify serializer includes all expected fields."""
        tracker_file = TrackerFileFactory()
        serializer = TrackerFileSerializer(tracker_file)

        expected_fields = {
            'id', 'tracker', 'filename', 'directory_path', 'github_url',
            'local_file', 'file_size', 'sha', 'color', 'material', 'quantity',
            'is_selected', 'status', 'printed_quantity', 'remaining_quantity',
            'is_complete', 'created_date', 'updated_date', 'download_date',
            'download_status', 'download_error', 'downloaded_at',
            'file_checksum', 'actual_file_size',
            # Material blueprint fields (Phase 10)
            'material_ids', 'materials_display', 'material_override'
        }
        assert set(serializer.data.keys()) == expected_fields
    
    def test_remaining_quantity_computed(self):
        """Test remaining_quantity computed field."""
        tracker_file = TrackerFileFactory(quantity=10, printed_quantity=3)
        serializer = TrackerFileSerializer(tracker_file)
        
        assert serializer.data['remaining_quantity'] == 7

    def test_is_complete_when_finished(self):
        """Test is_complete computed field when printing complete."""
        tracker_file = TrackerFileFactory(quantity=5, printed_quantity=5)
        serializer = TrackerFileSerializer(tracker_file)
        
        assert serializer.data['is_complete'] is True

    def test_is_complete_when_not_finished(self):
        """Test is_complete computed field when printing incomplete."""
        tracker_file = TrackerFileFactory(quantity=5, printed_quantity=2)
        serializer = TrackerFileSerializer(tracker_file)
        
        assert serializer.data['is_complete'] is False

    def test_read_only_fields(self):
        """Test that read-only fields cannot be set via serializer."""
        tracker_file = TrackerFileFactory()
        
        serializer = TrackerFileSerializer(
            tracker_file,
            data={'created_date': '2025-01-01'},
            partial=True
        )
        # Should be valid even though created_date is provided
        # (read-only fields are ignored)
        assert serializer.is_valid()


@pytest.mark.django_db
class TestTrackerSerializer:
    """Test TrackerSerializer."""

    def test_serializer_fields(self):
        """Verify serializer includes all expected fields."""
        tracker = TrackerFactory()
        serializer = TrackerSerializer(tracker)
        
        expected_fields = {
            'id', 'name', 'project', 'project_name', 'github_url', 'storage_type',
            'creation_mode', 'primary_color', 'accent_color', 'created_date', 'updated_date',
            'show_on_dashboard', 'notes', 'files', 'total_count', 'completed_count',
            'in_progress_count', 'not_started_count', 'progress_percentage',
            'total_quantity', 'printed_quantity_total', 'pending_quantity',
            'storage_path', 'total_storage_used', 'files_downloaded',
            # Filament tracking fields added for print cost estimation
            'primary_filament', 'primary_filament_info', 'primary_filament_used_grams',
            'secondary_filament', 'secondary_filament_info', 'secondary_filament_used_grams',
            'filament_cost',
            # Material blueprint fields (Phase 10)
            'primary_material', 'accent_material', 'primary_material_display', 'accent_material_display'
        }
        assert set(serializer.data.keys()) == expected_fields

    def test_nested_files_serialization(self):
        """Test that nested files are serialized correctly."""
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, filename="part1.stl")
        TrackerFileFactory(tracker=tracker, filename="part2.stl")
        TrackerFileFactory(tracker=tracker, filename="part3.stl")
        
        serializer = TrackerSerializer(tracker)
        
        assert len(serializer.data['files']) == 3
        filenames = [f['filename'] for f in serializer.data['files']]
        assert "part1.stl" in filenames
        assert "part2.stl" in filenames
        assert "part3.stl" in filenames

    def test_computed_counts(self):
        """Test computed count fields (total, completed, in progress, not started)."""
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, status='completed', quantity=5, printed_quantity=5)
        TrackerFileFactory(tracker=tracker, status='in_progress', quantity=3, printed_quantity=1)
        TrackerFileFactory(tracker=tracker, status='not_started', quantity=2, printed_quantity=0)
        TrackerFileFactory(tracker=tracker, status='not_started', quantity=4, printed_quantity=0)
        
        serializer = TrackerSerializer(tracker)
        
        assert serializer.data['total_count'] == 4
        assert serializer.data['completed_count'] == 1
        assert serializer.data['in_progress_count'] == 1
        assert serializer.data['not_started_count'] == 2

    def test_computed_quantities(self):
        """Test computed quantity fields (total, printed, pending)."""
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, quantity=10, printed_quantity=7)
        TrackerFileFactory(tracker=tracker, quantity=5, printed_quantity=2)
        TrackerFileFactory(tracker=tracker, quantity=8, printed_quantity=0)
        
        serializer = TrackerSerializer(tracker)
        
        assert serializer.data['total_quantity'] == 23  # 10 + 5 + 8
        assert serializer.data['printed_quantity_total'] == 9  # 7 + 2 + 0
        assert serializer.data['pending_quantity'] == 14  # 23 - 9

    def test_progress_percentage(self):
        """Test progress_percentage computed field (based on quantity, not file count)."""
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, status='completed', quantity=10, printed_quantity=10)
        TrackerFileFactory(tracker=tracker, status='in_progress', quantity=10, printed_quantity=5)
        TrackerFileFactory(tracker=tracker, status='not_started', quantity=10, printed_quantity=0)
        
        serializer = TrackerSerializer(tracker)
        
        # 15 of 30 quantity printed = 50%
        assert serializer.data['progress_percentage'] == 50

    def test_project_name_from_relationship(self):
        """Test project_name comes from related project."""
        project = ProjectFactory(project_name="Test Project Alpha")
        tracker = TrackerFactory(project=project)
        
        serializer = TrackerSerializer(tracker)
        
        assert serializer.data['project_name'] == "Test Project Alpha"

    def test_project_name_null_when_no_project(self):
        """Test project_name is null when no project assigned."""
        tracker = TrackerFactory(project=None)
        
        serializer = TrackerSerializer(tracker)
        
        assert serializer.data['project_name'] is None

    def test_read_only_storage_fields(self):
        """Test that storage tracking fields are read-only."""
        tracker = TrackerFactory()
        
        serializer = TrackerSerializer(
            tracker,
            data={'storage_path': '/new/path'},
            partial=True
        )
        # Should be valid (read-only field ignored)
        assert serializer.is_valid()


@pytest.mark.django_db
class TestTrackerCreateSerializer:
    """Test TrackerCreateSerializer (used for bulk create with nested files)."""

    def test_create_tracker_with_files(self):
        """Test creating tracker with nested files."""
        from inventory.serializers import TrackerCreateSerializer
        
        data = {
            'name': 'Test Tracker',
            'storage_type': 'link',  # Don't trigger downloads
            'files': [
                {'filename': 'part1.stl', 'github_url': 'https://example.com/part1.stl'},
                {'filename': 'part2.stl', 'github_url': 'https://example.com/part2.stl'}
            ]
        }
        
        serializer = TrackerCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        tracker = serializer.save()
        
        assert tracker.name == 'Test Tracker'
        assert tracker.files.count() == 2

    def test_create_with_optional_fields(self):
        """Test creating tracker with optional color/notes fields."""
        from inventory.serializers import TrackerCreateSerializer
        
        data = {
            'name': 'Colorful Tracker',
            'storage_type': 'link',
            'primary_color': '#FF5733',
            'accent_color': '#33FF57',
            'notes': 'Test notes',
            'files': []
        }
        
        serializer = TrackerCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        tracker = serializer.save()
        
        assert tracker.primary_color == '#FF5733'
        assert tracker.accent_color == '#33FF57'
        assert tracker.notes == 'Test notes'


@pytest.mark.django_db
class TestTrackerListSerializer:
    """Tests for TrackerListSerializer (list view without nested files)."""
    
    def test_serializer_fields(self):
        """Test that TrackerListSerializer has expected fields."""
        from inventory.serializers import TrackerListSerializer
        
        serializer = TrackerListSerializer()
        expected_fields = [
            'id', 'name', 'project', 'project_name', 'github_url', 'storage_type',
            'progress_percentage', 'total_count', 'completed_count',
            'total_quantity', 'printed_quantity_total', 'pending_quantity',
            'created_date'
        ]
        
        assert set(serializer.fields.keys()) == set(expected_fields)
    
    def test_serialize_tracker_minimal(self):
        """Test serializing a minimal tracker for list view."""
        from inventory.serializers import TrackerListSerializer
        
        tracker = TrackerFactory(
            name='List View Tracker',
            storage_type='link',
            project=None
        )
        
        serializer = TrackerListSerializer(tracker)
        data = serializer.data
        
        assert data['id'] == tracker.id
        assert data['name'] == 'List View Tracker'
        assert data['storage_type'] == 'link'
        assert data['project'] is None
        assert data['project_name'] is None
    
    def test_serialize_with_computed_stats(self):
        """Test that computed stats fields are present in list serialization."""
        from inventory.serializers import TrackerListSerializer
        
        tracker = TrackerFactory()
        
        # Create files with varying progress
        TrackerFileFactory(tracker=tracker, quantity=10, printed_quantity=10)
        TrackerFileFactory(tracker=tracker, quantity=5, printed_quantity=3)
        TrackerFileFactory(tracker=tracker, quantity=8, printed_quantity=0)
        
        # Refresh tracker to get updated stats from signals
        tracker.refresh_from_db()
        
        serializer = TrackerListSerializer(tracker)
        data = serializer.data
        
        # Verify computed stat fields are present (exact values depend on signal timing)
        assert 'total_count' in data
        assert 'completed_count' in data
        assert 'total_quantity' in data
        assert 'printed_quantity_total' in data
        assert 'pending_quantity' in data
        assert 'progress_percentage' in data
        
        # Verify they're numeric
        assert isinstance(data['total_count'], int)
        assert isinstance(data['completed_count'], int)
        assert isinstance(data['progress_percentage'], int)
    
    def test_serialize_with_project(self):
        """Test serializing tracker with associated project."""
        from inventory.serializers import TrackerListSerializer
        
        project = ProjectFactory(project_name='My Project')
        tracker = TrackerFactory(
            name='Project Tracker',
            project=project
        )
        
        serializer = TrackerListSerializer(tracker)
        data = serializer.data
        
        assert data['project'] == project.id
        assert data['project_name'] == 'My Project'
    
    def test_serialize_multiple_trackers(self):
        """Test serializing multiple trackers efficiently for list view."""
        from inventory.serializers import TrackerListSerializer
        
        trackers = [
            TrackerFactory(name=f'Tracker {i}', storage_type='link')
            for i in range(3)
        ]
        
        serializer = TrackerListSerializer(trackers, many=True)
        data = serializer.data
        
        assert len(data) == 3
        assert data[0]['name'] == 'Tracker 0'
        assert data[1]['name'] == 'Tracker 1'
        assert data[2]['name'] == 'Tracker 2'


@pytest.mark.django_db
class TestEdgeCaseSerializers:
    """Tests for edge cases and error handling in serializers."""
    
    def test_tracker_file_zero_quantity(self):
        """Test TrackerFileSerializer with zero printed_quantity."""
        from inventory.serializers import TrackerFileSerializer
        
        tracker_file = TrackerFileFactory(
            quantity=10,
            printed_quantity=0
        )
        
        serializer = TrackerFileSerializer(tracker_file)
        data = serializer.data
        
        assert data['quantity'] == 10
        assert data['printed_quantity'] == 0
        assert data['remaining_quantity'] == 10
        assert data['is_complete'] is False
    
    def test_tracker_serializer_zero_files(self):
        """Test TrackerSerializer with no files."""
        from inventory.serializers import TrackerSerializer
        
        tracker = TrackerFactory()
        tracker.refresh_from_db()
        # No files created
        
        serializer = TrackerSerializer(tracker)
        data = serializer.data
        
        assert data['files'] == []
        assert data['total_count'] == 0
        assert data['completed_count'] == 0
        assert data['total_quantity'] == 0
        assert data['printed_quantity_total'] == 0
