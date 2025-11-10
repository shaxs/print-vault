# printvault/inventory/serializers.py
import json
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Brand, PartType, Location, Material, Vendor, Printer, Mod, ModFile,
    InventoryItem, Project, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters,
    Tracker, TrackerFile
)
from .services.storage_manager import StorageManager, InsufficientStorageError, StoragePermissionError
from .services.file_download_service import (
    FileDownloadService, 
    DownloadError, 
    FileTooLargeError, 
    DownloadTimeoutError
)

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']

class PartTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartType
        fields = ['id', 'name']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name']

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ['id', 'name']

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name']
        
class ModFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModFile
        fields = '__all__'

class ModSerializer(serializers.ModelSerializer):
    files = ModFileSerializer(many=True, read_only=True)
    class Meta:
        model = Mod
        fields = ['id', 'printer', 'name', 'link', 'status', 'files']

class ProjectLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLink
        fields = ['id', 'name', 'url', 'project']

class ProjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = '__all__'

class SimpleProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'project_name']

def get_or_create_nested(model_class, data):
    if not data: return None
    if isinstance(data, str):
        try: data = json.loads(data)
        except (json.JSONDecodeError, TypeError): return None
    if isinstance(data, dict) and 'name' in data and data['name']:
        instance, _ = model_class.objects.get_or_create(name=data['name'])
        return instance
    return None

class InventoryItemSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    part_type = PartTypeSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    vendor = VendorSerializer(read_only=True)
    associated_projects = SimpleProjectSerializer(many=True, read_only=True)
    project_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Project.objects.all(), source='associated_projects', write_only=True, required=False
    )
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'title', 'brand', 'part_type', 'quantity', 
            'cost', 'location', 'photo', 'notes',
            'associated_projects', 'project_ids',
            # --- New Fields for Consumables ---
            'is_consumable', 'low_stock_threshold',
            # --- Vendor and Model Fields ---
            'vendor', 'vendor_link', 'model'
        ]

    def create(self, validated_data):
        projects = validated_data.pop('associated_projects', None)
        request_data = self.context['request'].data
        validated_data['brand'] = get_or_create_nested(Brand, request_data.get('brand'))
        validated_data['part_type'] = get_or_create_nested(PartType, request_data.get('part_type'))
        validated_data['location'] = get_or_create_nested(Location, request_data.get('location'))
        validated_data['vendor'] = get_or_create_nested(Vendor, request_data.get('vendor'))
        instance = InventoryItem.objects.create(**validated_data)
        if projects:
            instance.associated_projects.set(projects)
        return instance

    def update(self, instance, validated_data):
        projects = validated_data.pop('associated_projects', None)
        request_data = self.context['request'].data
        if 'brand' in request_data:
            instance.brand = get_or_create_nested(Brand, request_data.get('brand'))
        if 'part_type' in request_data:
            instance.part_type = get_or_create_nested(PartType, request_data.get('part_type'))
        if 'location' in request_data:
            instance.location = get_or_create_nested(Location, request_data.get('location'))
        if 'vendor' in request_data:
            instance.vendor = get_or_create_nested(Vendor, request_data.get('vendor'))
        instance = super().update(instance, validated_data)
        if projects is not None:
            instance.associated_projects.set(projects)
        return instance

class PrinterSerializer(serializers.ModelSerializer):
    manufacturer = BrandSerializer(read_only=True)
    mods = ModSerializer(many=True, read_only=True)
    associated_projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = Printer
        fields = '__all__'

    def create(self, validated_data):
        request_data = self.context['request'].data
        validated_data['manufacturer'] = get_or_create_nested(Brand, request_data.get('manufacturer'))
        return Printer.objects.create(**validated_data)

    def update(self, instance, validated_data):
        request_data = self.context['request'].data
        if 'manufacturer' in request_data:
            instance.manufacturer = get_or_create_nested(Brand, request_data.get('manufacturer'))
        return super().update(instance, validated_data)

class ProjectSerializer(serializers.ModelSerializer):
    associated_inventory_items = InventoryItemSerializer(many=True, read_only=True)
    associated_printers = PrinterSerializer(many=True, read_only=True)
    total_cost = serializers.SerializerMethodField()
    links = ProjectLinkSerializer(many=True, read_only=True)
    files = ProjectFileSerializer(many=True, read_only=True)
    trackers = serializers.SerializerMethodField()  # Add trackers to project detail

    inventory_item_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=InventoryItem.objects.all(), source='associated_inventory_items', write_only=True, required=False)
    printer_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Printer.objects.all(), source='associated_printers', write_only=True, required=False)
    tracker_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    
    class Meta:
        model = Project
        fields = [
            'id', 'project_name', 'description', 'status', 'start_date', 'due_date',
            'notes', 'photo', 'associated_inventory_items', 'associated_printers', 
            'total_cost', 'inventory_item_ids', 'printer_ids', 'links', 'files', 'trackers', 'tracker_ids'
        ]
    
    def get_total_cost(self, obj):
        total = sum(item.cost for item in obj.associated_inventory_items.all() if item.cost)
        return total
    
    def get_trackers(self, obj):
        """Return list of trackers associated with this project."""
        from .serializers import TrackerListSerializer
        return TrackerListSerializer(obj.trackers.all(), many=True).data

    def create(self, validated_data):
        inventory_items = validated_data.pop('associated_inventory_items', None)
        printers = validated_data.pop('associated_printers', None)
        tracker_ids = validated_data.pop('tracker_ids', None)
        project = Project.objects.create(**validated_data)
        if inventory_items: project.associated_inventory_items.set(inventory_items)
        if printers: project.associated_printers.set(printers)
        if tracker_ids is not None:
            # Update trackers to point to this project
            from .models import Tracker
            Tracker.objects.filter(id__in=tracker_ids).update(project=project)
        return project

    def update(self, instance, validated_data):
        inventory_items = validated_data.pop('associated_inventory_items', None)
        printers = validated_data.pop('associated_printers', None)
        tracker_ids = validated_data.pop('tracker_ids', None)
        instance = super().update(instance, validated_data)
        if inventory_items is not None: instance.associated_inventory_items.set(inventory_items)
        if printers is not None: instance.associated_printers.set(printers)
        if tracker_ids is not None:
            # Update trackers: clear old associations and set new ones
            from .models import Tracker
            # Clear any trackers that were previously associated with this project but are no longer selected
            Tracker.objects.filter(project=instance).exclude(id__in=tracker_ids).update(project=None)
            # Associate selected trackers with this project
            Tracker.objects.filter(id__in=tracker_ids).update(project=instance)
        return instance

class ProjectInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInventory
        fields = '__all__'

class ProjectPrintersSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPrinters
        fields = '__all__'


# ============================================================================
# PRINT TRACKER SERIALIZERS
# ============================================================================

class TrackerFileSerializer(serializers.ModelSerializer):
    """Serializer for individual tracker files."""
    remaining_quantity = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    local_file = serializers.SerializerMethodField()
    
    class Meta:
        model = TrackerFile
        fields = [
            'id', 'tracker', 'filename', 'directory_path', 'github_url', 
            'local_file', 'file_size', 'sha', 'color', 'material', 'quantity',
            'is_selected', 'status', 'printed_quantity', 'remaining_quantity',
            'is_complete', 'created_date', 'updated_date', 'download_date',
            # Download tracking fields
            'download_status', 'download_error', 'downloaded_at', 
            'file_checksum', 'actual_file_size'
        ]
        read_only_fields = [
            'created_date', 'updated_date', 'download_date',
            'download_status', 'download_error', 'downloaded_at',
            'file_checksum', 'actual_file_size'
        ]
    
    def get_local_file(self, obj):
        """Return relative URL for local_file to avoid mixed content issues with HTTPS."""
        if obj.local_file:
            # Return relative URL starting with /media/
            return obj.local_file.url if obj.local_file.url.startswith('/') else f"/{obj.local_file.url}"
        return None


class TrackerFileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tracker files in nested creation (excludes tracker field)."""
    
    class Meta:
        model = TrackerFile
        fields = [
            'filename', 'directory_path', 'github_url', 'file_size', 'sha',
            'color', 'material', 'quantity', 'is_selected'
        ]
        extra_kwargs = {
            'github_url': {'required': False, 'allow_blank': True}
        }


class TrackerSerializer(serializers.ModelSerializer):
    """Serializer for Tracker with nested files and computed properties."""
    files = TrackerFileSerializer(many=True, read_only=True)
    total_count = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    in_progress_count = serializers.IntegerField(read_only=True)
    not_started_count = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    printed_quantity_total = serializers.IntegerField(read_only=True)
    pending_quantity = serializers.IntegerField(read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Tracker
        fields = [
            'id', 'name', 'project', 'project_name', 'github_url', 'storage_type',
            'creation_mode', 'primary_color', 'accent_color', 'created_date', 'updated_date',
            'show_on_dashboard',
            'files', 'total_count', 'completed_count', 'in_progress_count',
            'not_started_count', 'progress_percentage', 'total_quantity',
            'printed_quantity_total', 'pending_quantity',
            # Storage tracking fields
            'storage_path', 'total_storage_used', 'files_downloaded'
        ]
        read_only_fields = [
            'created_date', 'updated_date', 
            'storage_path', 'total_storage_used', 'files_downloaded'
        ]


class TrackerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new tracker with files in a single request."""
    files = TrackerFileCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Tracker
        fields = [
            'id', 'name', 'project', 'github_url', 'storage_type', 'creation_mode',
            'primary_color', 'accent_color', 'files'
        ]
    
    def create(self, validated_data):
        """
        Create tracker and associated files.
        If storage_type is 'local', automatically download files after creation.
        """
        files_data = validated_data.pop('files', [])
        storage_type = validated_data.get('storage_type', 'link')
        
        # Create tracker
        tracker = Tracker.objects.create(**validated_data)
        
        # Create tracker files
        created_files = []
        for file_data in files_data:
            tracker_file = TrackerFile.objects.create(tracker=tracker, **file_data)
            created_files.append(tracker_file)
        
        # If storage_type is 'local', initiate file downloads
        download_results = None
        if storage_type == 'local' and created_files:
            download_results = self._download_tracker_files(tracker, created_files)
            
            # Store download results in tracker context for view to return
            tracker._download_results = download_results
        
        return tracker
    
    def _download_tracker_files(self, tracker, tracker_files):
        """
        Download files for a tracker using StorageManager and FileDownloadService.
        
        Returns:
            dict: Download results with successful/failed files
        """
        storage_manager = StorageManager()
        download_service = FileDownloadService()
        
        # Calculate total size needed
        total_size = sum(f.file_size for f in tracker_files if f.file_size)
        
        # Check available disk space
        try:
            space_check = storage_manager.check_available_space(total_size)
            if not space_check['sufficient']:
                # Mark all files as failed due to insufficient space
                for tf in tracker_files:
                    tf.download_status = 'failed'
                    tf.download_error = f"Insufficient disk space. Need {storage_manager._format_bytes(total_size)}, only {space_check['available_formatted']} available."
                    tf.save()
                
                return {
                    'successful': [],
                    'failed': [
                        {
                            'file_id': tf.id,
                            'filename': tf.filename,
                            'error': tf.download_error
                        } for tf in tracker_files
                    ],
                    'total_bytes': 0,
                    'error': 'Insufficient disk space'
                }
        except InsufficientStorageError as e:
            # Same handling as above but with exception
            for tf in tracker_files:
                tf.download_status = 'failed'
                tf.download_error = str(e)
                tf.save()
            
            return {
                'successful': [],
                'failed': [
                    {
                        'file_id': tf.id,
                        'filename': tf.filename,
                        'error': str(e)
                    } for tf in tracker_files
                ],
                'total_bytes': 0,
                'error': str(e)
            }
        except StoragePermissionError as e:
            # Permission error - can't create storage directories
            for tf in tracker_files:
                tf.download_status = 'failed'
                tf.download_error = f"Storage permission error: {str(e)}"
                tf.save()
            
            return {
                'successful': [],
                'failed': [
                    {
                        'file_id': tf.id,
                        'filename': tf.filename,
                        'error': f"Storage permission error: {str(e)}"
                    } for tf in tracker_files
                ],
                'total_bytes': 0,
                'error': f"Storage permission error: {str(e)}"
            }
        
        # Get storage path for this tracker
        try:
            storage_path = storage_manager.get_tracker_storage_path(tracker.id, create=True)
            tracker.storage_path = storage_path
            tracker.save()
        except Exception as e:
            # Failed to create storage path
            for tf in tracker_files:
                tf.download_status = 'failed'
                tf.download_error = f"Failed to create storage path: {str(e)}"
                tf.save()
            
            return {
                'successful': [],
                'failed': [
                    {
                        'file_id': tf.id,
                        'filename': tf.filename,
                        'error': f"Failed to create storage path: {str(e)}"
                    } for tf in tracker_files
                ],
                'total_bytes': 0,
                'error': f"Failed to create storage path: {str(e)}"
            }
        
        # Prepare file list for batch download
        # Also build a mapping of tracker_file_id to relative path for local_file field
        file_list = []
        file_path_mapping = {}  # Maps tracker_file_id to relative path from MEDIA_ROOT
        
        for tracker_file in tracker_files:
            # Get category path (directory_path is used as category)
            category_path = storage_manager.get_category_path(
                tracker.id, 
                tracker_file.directory_path or 'uncategorized',
                create=True
            )
            
            # Sanitize filename
            safe_filename = storage_manager.sanitize_filename(tracker_file.filename)
            destination = f"{category_path}/{safe_filename}"
            
            # Build relative path for FileField (relative to MEDIA_ROOT)
            # destination is absolute, e.g., C:\...\media\trackers\8\files\test\file.stl
            # We need: trackers/8/files/test/file.stl
            category = tracker_file.directory_path or 'uncategorized'
            safe_category = storage_manager.sanitize_filename(category)
            relative_path = f"trackers/{tracker.id}/files/{safe_category}/{safe_filename}"
            file_path_mapping[tracker_file.id] = relative_path
            
            file_list.append({
                'url': tracker_file.github_url,
                'destination': destination,
                'name': tracker_file.filename,
                'tracker_file_id': tracker_file.id
            })
            
            # Mark as downloading
            tracker_file.download_status = 'downloading'
            tracker_file.save()
        
        # Download files in batch
        results = download_service.download_files_batch(file_list)
        
        # Process results and update tracker files
        successful_downloads = []
        failed_downloads = []
        total_bytes_downloaded = 0
        
        for success_info in results['successful']:
            # Find the tracker file
            tracker_file = next(
                (tf for tf in tracker_files if tf.id == success_info.get('tracker_file_id')),
                None
            )
            
            if tracker_file:
                tracker_file.download_status = 'completed'
                tracker_file.downloaded_at = timezone.now()
                tracker_file.file_checksum = success_info.get('checksum', '')
                tracker_file.actual_file_size = success_info.get('bytes_downloaded', 0)
                tracker_file.download_error = ''
                # Set the local_file path (relative to MEDIA_ROOT)
                tracker_file.local_file = file_path_mapping.get(tracker_file.id, '')
                tracker_file.save()
                
                total_bytes_downloaded += success_info.get('bytes_downloaded', 0)
                successful_downloads.append({
                    'file_id': tracker_file.id,
                    'filename': tracker_file.filename,
                    'bytes_downloaded': success_info.get('bytes_downloaded', 0),
                    'duration': success_info.get('duration', 0)
                })
        
        for fail_info in results['failed']:
            # Find the tracker file
            tracker_file = next(
                (tf for tf in tracker_files if tf.id == fail_info.get('tracker_file_id')),
                None
            )
            
            if tracker_file:
                tracker_file.download_status = 'failed'
                tracker_file.download_error = fail_info.get('error', 'Unknown error')
                tracker_file.save()
                
                failed_downloads.append({
                    'file_id': tracker_file.id,
                    'filename': tracker_file.filename,
                    'error': fail_info.get('error', 'Unknown error')
                })
        
        # Update tracker totals
        tracker.total_storage_used = total_bytes_downloaded
        tracker.files_downloaded = len(failed_downloads) == 0  # True if no failures
        tracker.save()
        
        return {
            'successful': successful_downloads,
            'failed': failed_downloads,
            'total_bytes': total_bytes_downloaded,
            'duration': results.get('duration', 0)
        }


class TrackerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for tracker list view (without nested files)."""
    progress_percentage = serializers.IntegerField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    printed_quantity_total = serializers.IntegerField(read_only=True)
    pending_quantity = serializers.IntegerField(read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Tracker
        fields = [
            'id', 'name', 'project', 'project_name', 'github_url', 'storage_type',
            'progress_percentage', 'total_count', 'completed_count', 
            'total_quantity', 'printed_quantity_total', 'pending_quantity',
            'created_date'
        ]
        read_only_fields = ['created_date']