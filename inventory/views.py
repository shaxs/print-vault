# printvault/inventory/views.py
import csv
import zipfile
import os
import shutil
import tempfile
import hashlib
import json
from io import BytesIO, StringIO
from datetime import date, timedelta
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, filters, mixins
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from rest_framework.decorators import action
from .models import (
    Brand, PartType, Location, Material, Printer, Mod, ModFile,
    InventoryItem, Project, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters,
    Tracker, TrackerFile, AlertDismissal
)
from .serializers import (
    BrandSerializer, PartTypeSerializer, LocationSerializer, MaterialSerializer, PrinterSerializer, ModSerializer, ModFileSerializer,
    InventoryItemSerializer, ProjectSerializer, ProjectLinkSerializer, ProjectFileSerializer,
    ProjectInventorySerializer, ProjectPrintersSerializer,
    TrackerSerializer, TrackerFileSerializer, TrackerCreateSerializer, TrackerListSerializer
)
from .filters import InventoryItemFilter, PrinterFilter, ProjectFilter
from .services.github_service import (
    crawl_github_repository,
    GitHubCrawlerError,
    InvalidURLError,
    RepositoryNotFoundError,
    RateLimitError,
    NetworkError,
    EmptyResultError
)
from .services.storage_manager import StorageManager, InsufficientStorageError, StoragePermissionError
from .services.file_download_service import FileDownloadService, DownloadError, FileTooLargeError, DownloadTimeoutError

# A viewset that only allows listing and retrieving (read-only)
class ReadOnlyViewSet(mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    pass

class ExportDataView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Export Inventory Items
            inv_buffer = StringIO()
            inv_writer = csv.writer(inv_buffer)
            inv_writer.writerow(['id', 'title', 'brand', 'part_type', 'location', 'quantity', 'cost', 'notes', 'photo', 'is_consumable', 'low_stock_threshold'])
            for item in InventoryItem.objects.all():
                inv_writer.writerow([
                    item.id, item.title, item.brand.name if item.brand else '',
                    item.part_type.name if item.part_type else '',
                    item.location.name if item.location else '',
                    item.quantity, item.cost, item.notes,
                    os.path.basename(item.photo.name) if item.photo else '',
                    item.is_consumable, item.low_stock_threshold
                ])
            zf.writestr('inventory.csv', inv_buffer.getvalue())

            # Export Printers
            printer_buffer = StringIO()
            printer_writer = csv.writer(printer_buffer)
            printer_writer.writerow(['id', 'title', 'manufacturer', 'serial_number', 'purchase_date', 'status', 'notes', 'purchase_price', 'photo', 'last_maintained_date', 'maintenance_reminder_date', 'last_carbon_replacement_date', 'carbon_reminder_date', 'maintenance_notes'])
            for printer in Printer.objects.all():
                printer_writer.writerow([
                    printer.id, printer.title, printer.manufacturer.name if printer.manufacturer else '',
                    printer.serial_number, printer.purchase_date, printer.status, printer.notes,
                    printer.purchase_price, os.path.basename(printer.photo.name) if printer.photo else '',
                    printer.last_maintained_date, printer.maintenance_reminder_date,
                    printer.last_carbon_replacement_date, printer.carbon_reminder_date,
                    printer.maintenance_notes
                ])
            zf.writestr('printers.csv', printer_buffer.getvalue())
            
            # Export Mods
            mod_buffer = StringIO()
            mod_writer = csv.writer(mod_buffer)
            mod_writer.writerow(['id', 'printer_id', 'name', 'link', 'status'])
            for mod in Mod.objects.all():
                mod_writer.writerow([mod.id, mod.printer.id, mod.name, mod.link, mod.status])
            zf.writestr('mods.csv', mod_buffer.getvalue())

            # Export ModFiles
            modfile_buffer = StringIO()
            modfile_writer = csv.writer(modfile_buffer)
            modfile_writer.writerow(['id', 'mod_id', 'file'])
            for modfile in ModFile.objects.all():
                modfile_writer.writerow([modfile.id, modfile.mod.id, os.path.basename(modfile.file.name) if modfile.file else ''])
            zf.writestr('modfiles.csv', modfile_buffer.getvalue())

            # Export Projects
            project_buffer = StringIO()
            project_writer = csv.writer(project_buffer)
            project_writer.writerow(['id', 'project_name', 'description', 'status', 'start_date', 'end_date', 'notes', 'photo'])
            for project in Project.objects.all():
                project_writer.writerow([
                    project.id, project.project_name, project.description, project.status,
                    project.start_date, project.end_date, project.notes,
                    os.path.basename(project.photo.name) if project.photo else ''
                ])
            zf.writestr('projects.csv', project_buffer.getvalue())

            # Export ProjectLinks
            projectlink_buffer = StringIO()
            projectlink_writer = csv.writer(projectlink_buffer)
            projectlink_writer.writerow(['id', 'project_id', 'name', 'url'])
            for link in ProjectLink.objects.all():
                projectlink_writer.writerow([link.id, link.project.id, link.name, link.url])
            zf.writestr('project_links.csv', projectlink_buffer.getvalue())

            # Export ProjectFiles
            projectfile_buffer = StringIO()
            projectfile_writer = csv.writer(projectfile_buffer)
            projectfile_writer.writerow(['id', 'project_id', 'file'])
            for pfile in ProjectFile.objects.all():
                projectfile_writer.writerow([pfile.id, pfile.project.id, os.path.basename(pfile.file.name) if pfile.file else ''])
            zf.writestr('project_files.csv', projectfile_buffer.getvalue())

            # Export ProjectInventory
            projectinventory_buffer = StringIO()
            projectinventory_writer = csv.writer(projectinventory_buffer)
            projectinventory_writer.writerow(['project_id', 'inventory_item_id', 'quantity_used'])
            for pi in ProjectInventory.objects.all():
                projectinventory_writer.writerow([pi.project.id, pi.inventory_item.id, pi.quantity_used])
            zf.writestr('project_inventory.csv', projectinventory_buffer.getvalue())

            # Export ProjectPrinters
            projectprinters_buffer = StringIO()
            projectprinters_writer = csv.writer(projectprinters_buffer)
            projectprinters_writer.writerow(['project_id', 'printer_id'])
            for pp in ProjectPrinters.objects.all():
                projectprinters_writer.writerow([pp.project.id, pp.printer.id])
            zf.writestr('project_printers.csv', projectprinters_buffer.getvalue())

            # Export Print Trackers
            tracker_buffer = StringIO()
            tracker_writer = csv.writer(tracker_buffer)
            tracker_writer.writerow([
                'id', 'name', 'project_id', 'github_url', 'storage_type',
                'primary_color', 'accent_color', 'total_quantity', 'printed_quantity_total',
                'progress_percentage', 'created_date', 'updated_date', 'storage_path',
                'total_storage_used', 'files_downloaded'
            ])
            for tracker in Tracker.objects.all():
                tracker_writer.writerow([
                    tracker.id, tracker.name,
                    tracker.project.id if tracker.project else '',
                    tracker.github_url, tracker.storage_type,
                    tracker.primary_color, tracker.accent_color,
                    tracker.total_quantity, tracker.printed_quantity_total,
                    tracker.progress_percentage, tracker.created_date, tracker.updated_date,
                    tracker.storage_path, tracker.total_storage_used, tracker.files_downloaded
                ])
            zf.writestr('trackers.csv', tracker_buffer.getvalue())

            # Export Tracker Files
            trackerfile_buffer = StringIO()
            trackerfile_writer = csv.writer(trackerfile_buffer)
            trackerfile_writer.writerow([
                'id', 'tracker_id', 'storage_type', 'filename', 'directory_path',
                'github_url', 'local_file', 'file_size', 'sha', 'color', 'material',
                'quantity', 'is_selected', 'status', 'printed_quantity',
                'created_date', 'updated_date', 'download_date', 'download_status',
                'download_error', 'downloaded_at', 'file_checksum', 'actual_file_size'
            ])
            for tfile in TrackerFile.objects.all():
                trackerfile_writer.writerow([
                    tfile.id, tfile.tracker.id, tfile.storage_type,
                    tfile.filename, tfile.directory_path, tfile.github_url,
                    os.path.basename(tfile.local_file.name) if tfile.local_file else '',
                    tfile.file_size, tfile.sha, tfile.color, tfile.material,
                    tfile.quantity, tfile.is_selected, tfile.status, tfile.printed_quantity,
                    tfile.created_date, tfile.updated_date, tfile.download_date,
                    tfile.download_status, tfile.download_error, tfile.downloaded_at,
                    tfile.file_checksum, tfile.actual_file_size
                ])
            zf.writestr('tracker_files.csv', trackerfile_buffer.getvalue())

            # Add media files to zip
            media_root = settings.MEDIA_ROOT
            for root, dirs, files in os.walk(media_root):
                for file in files:
                    # Skip CSV files - they're already added via writestr() above
                    if file.endswith('.csv'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, media_root)
                    zf.write(file_path, arcname)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=print-vault-backup.zip'
        return response


class DashboardDataView(APIView):
    """
    API endpoint that provides all data needed for the dashboard view.
    Returns alerts, stats, featured trackers, and active projects.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Generate and return dashboard data.
        
        Returns:
            Response with structure:
            {
                'alerts': {
                    'critical': [...],
                    'warning': [...],
                    'info': [...]
                },
                'stats': {
                    'inventory_count': int,
                    'printer_count': int,
                    'project_count': int,
                    'tracker_count': int
                },
                'featured_trackers': [...],
                'active_projects': [...]
            }
        """
        # Generate alerts (with state-based invalidation)
        alerts = self._generate_alerts()
        
        # Get stats
        stats = self._get_stats()
        
        # Get featured trackers
        featured_trackers = self._get_featured_trackers()
        
        # Get active projects
        active_projects = self._get_active_projects()
        
        return Response({
            'alerts': alerts,
            'stats': stats,
            'featured_trackers': featured_trackers,
            'active_projects': active_projects
        })
    
    def _generate_state_hash(self, alert_type, state_data):
        """
        Generate a SHA256 hash of the relevant state for an alert.
        
        When the state changes (e.g., printer status changes), the hash
        will be different, invalidating any previous dismissals.
        
        Args:
            alert_type: Type of alert (e.g., 'printer_repair')
            state_data: Dictionary of relevant state fields
            
        Returns:
            SHA256 hash string (64 characters)
        """
        # Define which fields matter for each alert type
        state_field_map = {
            'printer_repair': ['status', 'id'],
            'maintenance_overdue': ['last_maintained_date', 'maintenance_reminder_date', 'id'],
            'carbon_overdue': ['carbon_reminder_date', 'id'],
            'carbon_soon': ['carbon_reminder_date', 'id'],
            'project_overdue': ['due_date', 'id'],
            'project_blocked': ['printer_states', 'id'],
            'project_due_soon': ['due_date', 'id'],
            'tracker_unconfigured': ['github_url', 'id'],
            'low_stock': ['quantity', 'min_quantity', 'id'],
        }
        
        # Get relevant fields for this alert type
        relevant_fields = state_field_map.get(alert_type, ['id'])
        
        # Extract only relevant data
        filtered_state = {}
        for field in relevant_fields:
            value = state_data.get(field)
            # Convert dates to strings for consistent hashing
            if isinstance(value, (date, timezone.datetime)):
                value = value.isoformat()
            filtered_state[field] = value
        
        # Create deterministic JSON string (sorted keys)
        state_json = json.dumps(filtered_state, sort_keys=True)
        
        # Generate SHA256 hash
        return hashlib.sha256(state_json.encode('utf-8')).hexdigest()
    
    def _should_show_alert(self, alert_type, alert_id, state_data):
        """
        Check if an alert should be shown based on dismissal state.
        
        Uses state-based invalidation: if the underlying state has changed
        since dismissal, the alert will be shown again.
        
        Args:
            alert_type: Type of alert (e.g., 'printer_repair')
            alert_id: Unique alert ID (e.g., 'printer_repair_1')
            state_data: Dictionary of current state data
            
        Returns:
            Boolean - True if alert should be shown
        """
        try:
            dismissal = AlertDismissal.objects.get(
                alert_type=alert_type,
                alert_id=alert_id
            )
            
            # Generate hash of current state
            current_state_hash = self._generate_state_hash(alert_type, state_data)
            
            # If dismissal has no state_hash (old record before fix), delete it
            if dismissal.state_hash is None:
                dismissal.delete()
                return True
            
            # If state hash matches, alert is still dismissed
            if dismissal.state_hash == current_state_hash:
                return False
            
            # State changed - delete old dismissal and show alert
            dismissal.delete()
            return True
            
        except AlertDismissal.DoesNotExist:
            # No dismissal exists - show alert
            return True
    
    def _cleanup_invalid_dismissals(self):
        """
        Remove dismissals for conditions that no longer exist.
        
        For example, if a printer was "Under Repair" (alert dismissed),
        then changed to "Active", the dismissal should be removed so the
        alert can reappear if the printer goes back to "Under Repair".
        """
        # Get all dismissals
        dismissals = AlertDismissal.objects.all()
        
        for dismissal in dismissals:
            should_delete = False
            
            # Check printer_repair dismissals
            if dismissal.alert_type == 'printer_repair':
                # Extract printer ID from alert_id (format: "printer_repair_8")
                try:
                    printer_id = int(dismissal.alert_id.split('_')[-1])
                    printer = Printer.objects.get(id=printer_id)
                    # If printer is no longer under repair, delete dismissal
                    if printer.status != 'Under Repair':
                        should_delete = True
                except (ValueError, Printer.DoesNotExist):
                    # Invalid ID or printer deleted - clean up dismissal
                    should_delete = True
            
            # Check maintenance_overdue dismissals
            elif dismissal.alert_type == 'maintenance_overdue':
                try:
                    printer_id = int(dismissal.alert_id.split('_')[-1])
                    printer = Printer.objects.get(id=printer_id)
                    # If maintenance is no longer overdue, delete dismissal
                    if printer.maintenance_reminder_date is None or printer.maintenance_reminder_date >= date.today():
                        should_delete = True
                except (ValueError, Printer.DoesNotExist):
                    should_delete = True
            
            # Check carbon_overdue dismissals
            elif dismissal.alert_type == 'carbon_overdue':
                try:
                    printer_id = int(dismissal.alert_id.split('_')[-1])
                    printer = Printer.objects.get(id=printer_id)
                    # If carbon filter is no longer overdue, delete dismissal
                    if printer.carbon_reminder_date is None or printer.carbon_reminder_date >= date.today():
                        should_delete = True
                except (ValueError, Printer.DoesNotExist):
                    should_delete = True
            
            # Check carbon_soon dismissals
            elif dismissal.alert_type == 'carbon_soon':
                try:
                    printer_id = int(dismissal.alert_id.split('_')[-1])
                    printer = Printer.objects.get(id=printer_id)
                    # If carbon filter is no longer due soon (outside 7-day window), delete dismissal
                    if printer.carbon_reminder_date is None or \
                       printer.carbon_reminder_date < date.today() or \
                       printer.carbon_reminder_date >= date.today() + timedelta(days=7):
                        should_delete = True
                except (ValueError, Printer.DoesNotExist):
                    should_delete = True
            
            # Check project_overdue dismissals
            elif dismissal.alert_type == 'project_overdue':
                try:
                    project_id = int(dismissal.alert_id.split('_')[-1])
                    project = Project.objects.get(id=project_id)
                    # If project is completed or due date is today or future, delete dismissal
                    if project.status == 'Completed' or \
                       project.due_date is None or \
                       project.due_date >= date.today():
                        should_delete = True
                except (ValueError, Project.DoesNotExist):
                    should_delete = True
            
            # Check project_due_soon dismissals
            elif dismissal.alert_type == 'project_due_soon':
                try:
                    project_id = int(dismissal.alert_id.split('_')[-1])
                    project = Project.objects.get(id=project_id)
                    # If project is completed or no longer due soon, delete dismissal
                    if project.status == 'Completed' or \
                       project.due_date is None or \
                       project.due_date < date.today() or \
                       project.due_date >= date.today() + timedelta(days=7):
                        should_delete = True
                except (ValueError, Project.DoesNotExist):
                    should_delete = True
            
            # Check project_blocked dismissals
            elif dismissal.alert_type == 'project_blocked':
                try:
                    project_id = int(dismissal.alert_id.split('_')[-1])
                    project = Project.objects.get(id=project_id)
                    # If project is not in progress or has no unavailable printers, delete dismissal
                    if project.status != 'In Progress':
                        should_delete = True
                    else:
                        unavailable_printers = project.associated_printers.filter(
                            status__in=['Under Repair', 'Sold', 'Archived']
                        )
                        if not unavailable_printers.exists():
                            should_delete = True
                except (ValueError, Project.DoesNotExist):
                    should_delete = True
            
            # Check low_stock dismissals
            elif dismissal.alert_type == 'low_stock':
                try:
                    item_id = int(dismissal.alert_id.split('_')[-1])
                    item = InventoryItem.objects.get(id=item_id)
                    # Delete dismissal if:
                    # 1. Item is no longer marked as consumable (alert disabled)
                    # 2. Low stock threshold is not set (alert disabled)
                    # 3. Quantity is above threshold (restocked)
                    if not item.is_consumable or \
                       item.low_stock_threshold is None or \
                       item.quantity > item.low_stock_threshold:
                        should_delete = True
                except (ValueError, InventoryItem.DoesNotExist):
                    should_delete = True
            
            # Check tracker_unconfigured dismissals
            elif dismissal.alert_type == 'tracker_unconfigured':
                try:
                    tracker_id = int(dismissal.alert_id.split('_')[-1])
                    tracker = Tracker.objects.get(id=tracker_id)
                    # If tracker has no files missing color/material, delete dismissal
                    from django.db.models import Q
                    unconfigured_count = tracker.files.filter(
                        Q(color='') | Q(material='')
                    ).count()
                    if unconfigured_count == 0:
                        should_delete = True
                except (ValueError, Tracker.DoesNotExist):
                    should_delete = True
            
            # Delete if condition no longer exists
            if should_delete:
                dismissal.delete()
    
    def _generate_alerts(self):
        """
        Generate all dashboard alerts with state-based dismissal checking.
        
        Uses state-based invalidation: dismissed alerts will reappear if the
        underlying state changes (e.g., printer status toggles).
        
        Returns:
            Dictionary with 'critical', 'warning', and 'info' alert arrays
        """
        # Clean up dismissals for conditions that no longer exist
        self._cleanup_invalid_dismissals()
        
        today = date.today()
        alerts = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # CRITICAL ALERTS
        
        # 1. Maintenance Overdue (Critical)
        # Show for all printers with overdue maintenance, regardless of status
        maintenance_overdue = Printer.objects.filter(
            maintenance_reminder_date__lt=today
        ).select_related('manufacturer')
        
        for printer in maintenance_overdue:
            alert_id = f"maintenance_overdue_{printer.id}"
            state_data = {
                'id': printer.id,
                'last_maintained_date': printer.last_maintained_date.isoformat() if printer.last_maintained_date else None,
                'maintenance_reminder_date': printer.maintenance_reminder_date.isoformat() if printer.maintenance_reminder_date else None
            }
            if self._should_show_alert('maintenance_overdue', alert_id, state_data):
                days_overdue = (today - printer.maintenance_reminder_date).days
                alerts['critical'].append({
                    'alert_type': 'maintenance_overdue',
                    'alert_id': alert_id,
                    'title': f'Maintenance Overdue: {printer.title}',
                    'message': f'Maintenance was due {days_overdue} days ago',
                    'link': f'/printers/{printer.id}',
                    'state_data': state_data
                })
        
        # 2. Printer Under Repair (Critical)
        repair_printers = Printer.objects.filter(
            status='Under Repair'
        ).select_related('manufacturer')
        
        for printer in repair_printers:
            alert_id = f"printer_repair_{printer.id}"
            state_data = {'id': printer.id, 'status': printer.status}
            if self._should_show_alert('printer_repair', alert_id, state_data):
                alerts['critical'].append({
                    'alert_type': 'printer_repair',
                    'alert_id': alert_id,
                    'title': f'Printer Under Repair: {printer.title}',
                    'message': 'This printer is currently under repair',
                    'link': f'/printers/{printer.id}',
                    'state_data': state_data
                })
        
        # 3. Carbon Filter Overdue (Critical)
        carbon_overdue = Printer.objects.filter(
            carbon_reminder_date__lt=today
        ).select_related('manufacturer')
        
        for printer in carbon_overdue:
            alert_id = f"carbon_overdue_{printer.id}"
            state_data = {
                'id': printer.id,
                'carbon_reminder_date': printer.carbon_reminder_date.isoformat() if printer.carbon_reminder_date else None
            }
            if self._should_show_alert('carbon_overdue', alert_id, state_data):
                days_overdue = (today - printer.carbon_reminder_date).days
                alerts['critical'].append({
                    'alert_type': 'carbon_overdue',
                    'alert_id': alert_id,
                    'title': f'Carbon Filter Overdue: {printer.title}',
                    'message': f'Carbon filter replacement was due {days_overdue} days ago',
                    'link': f'/printers/{printer.id}',
                    'state_data': state_data
                })
        
        # WARNING ALERTS
        
        # 4. Carbon Filter Due Soon (Warning)
        # Show for all printers with carbon filter due within 7 days
        carbon_due_soon = Printer.objects.filter(
            carbon_reminder_date__gte=today,
            carbon_reminder_date__lt=today + timedelta(days=7)
        ).select_related('manufacturer')
        
        for printer in carbon_due_soon:
            alert_id = f"carbon_soon_{printer.id}"
            state_data = {'id': printer.id, 'carbon_reminder_date': printer.carbon_reminder_date.isoformat() if printer.carbon_reminder_date else None}
            if self._should_show_alert('carbon_soon', alert_id, state_data):
                days_until = (printer.carbon_reminder_date - today).days
                alerts['warning'].append({
                    'alert_type': 'carbon_soon',
                    'alert_id': alert_id,
                    'title': f'Carbon Filter Due Soon: {printer.title}',
                    'message': f'Carbon filter replacement due in {days_until} days',
                    'link': f'/printers/{printer.id}',
                    'state_data': state_data
                })
        
        # 5. Project Overdue (Critical)
        projects_overdue = Project.objects.filter(
            due_date__lt=today
        ).exclude(status='Completed')
        
        for project in projects_overdue:
            alert_id = f"project_overdue_{project.id}"
            state_data = {'id': project.id, 'due_date': project.due_date.isoformat() if project.due_date else None}
            if self._should_show_alert('project_overdue', alert_id, state_data):
                days_overdue = (today - project.due_date).days if project.due_date else 0
                alerts['critical'].append({
                    'alert_type': 'project_overdue',
                    'alert_id': alert_id,
                    'title': f'Project Overdue: {project.project_name}',
                    'message': f'Overdue by {days_overdue} {"day" if days_overdue == 1 else "days"}',
                    'link': f'/projects/{project.id}',
                    'state_data': state_data
                })
        
        # 6. Projects Blocked by Printer Status (Critical)
        blocked_projects = Project.objects.filter(
            status='In Progress'
        ).prefetch_related('associated_printers')
        
        for project in blocked_projects:
            # Check if any associated printers are unavailable
            unavailable_printers = project.associated_printers.filter(
                status__in=['Under Repair', 'Sold', 'Archived']
            )
            
            if unavailable_printers.exists():
                alert_id = f"project_blocked_{project.id}"
                # Include printer IDs and statuses in state
                printer_states = list(unavailable_printers.values_list('id', 'status'))
                state_data = {
                    'id': project.id,
                    'printer_states': printer_states
                }
                if self._should_show_alert('project_blocked', alert_id, state_data):
                    printer_names = list(unavailable_printers.values_list('title', flat=True))
                    if len(printer_names) == 1:
                        message = f"Printer '{printer_names[0]}' is unavailable"
                    else:
                        message = f"{len(printer_names)} printers unavailable: {', '.join(printer_names)}"
                    
                    alerts['critical'].append({
                        'alert_type': 'project_blocked',
                        'alert_id': alert_id,
                        'title': f'Project Blocked: {project.project_name}',
                        'message': message,
                        'link': f'/projects/{project.id}',
                        'state_data': state_data
                    })
        
        # 7. Project Due Soon (Warning)
        projects_due_soon = Project.objects.filter(
            due_date__gte=today,
            due_date__lt=today + timedelta(days=7)
        ).exclude(status='Completed')
        
        for project in projects_due_soon:
            alert_id = f"project_due_soon_{project.id}"
            state_data = {'id': project.id, 'due_date': project.due_date.isoformat() if project.due_date else None}
            if self._should_show_alert('project_due_soon', alert_id, state_data):
                days_until = project.days_until_due
                alerts['warning'].append({
                    'alert_type': 'project_due_soon',
                    'alert_id': alert_id,
                    'title': f'Project Due Soon: {project.project_name}',
                    'message': f'Due in {days_until} days',
                    'link': f'/projects/{project.id}',
                    'state_data': state_data
                })
        
        # 8. Tracker with Unconfigured Files (Warning)
        # Unconfigured = missing color or material configuration
        from django.db.models import Q
        
        trackers_unconfigured = Tracker.objects.filter(
            Q(files__color='') | Q(files__material='')
        ).distinct()
        
        for tracker in trackers_unconfigured:
            # Count files missing color or material
            unconfigured_count = tracker.files.filter(
                Q(color='') | Q(material='')
            ).count()
            
            if unconfigured_count == 0:
                continue  # Skip if no unconfigured files
            
            alert_id = f"tracker_unconfigured_{tracker.id}"
            state_data = {'id': tracker.id, 'github_url': tracker.github_url}
            if self._should_show_alert('tracker_unconfigured', alert_id, state_data):
                alerts['warning'].append({
                    'alert_type': 'tracker_unconfigured',
                    'alert_id': alert_id,
                    'title': f'Tracker Needs Configuration: {tracker.name}',
                    'message': f'{unconfigured_count} file(s) need configuration',
                    'link': f'/trackers/{tracker.id}',
                    'state_data': state_data
                })
        
        # INFO ALERTS
        
        # 9. Low Stock Items (Info)
        low_stock_items = InventoryItem.objects.filter(
            is_consumable=True,
            quantity__lte=F('low_stock_threshold')
        ).select_related('brand', 'part_type')
        
        for item in low_stock_items:
            alert_id = f"low_stock_{item.id}"
            state_data = {'id': item.id, 'quantity': item.quantity, 'min_quantity': item.low_stock_threshold}
            if self._should_show_alert('low_stock', alert_id, state_data):
                alerts['info'].append({
                    'alert_type': 'low_stock',
                    'alert_id': alert_id,
                    'title': f'Low Stock: {item.title}',
                    'message': f'Only {item.quantity} remaining (threshold: {item.low_stock_threshold})',
                    'link': f'/item/{item.id}',
                    'state_data': state_data
                })
        
        return alerts
    
    def _get_stats(self):
        """
        Get count statistics for dashboard.
        
        Returns:
            Dictionary with counts for inventory, printers, projects, trackers
        """
        return {
            'inventory_count': InventoryItem.objects.count(),
            'printer_count': Printer.objects.count(),
            'project_count': Project.objects.count(),
            'tracker_count': Tracker.objects.count()
        }
    
    def _get_featured_trackers(self):
        """
        Get trackers marked as featured for dashboard.
        
        Returns:
            List of tracker dictionaries with basic info and progress
        """
        trackers = Tracker.objects.filter(
            show_on_dashboard=True
        ).select_related('project')
        
        featured = []
        for tracker in trackers:
            featured.append({
                'id': tracker.id,
                'name': tracker.name,
                'project_name': tracker.project.project_name if tracker.project else None,
                'progress_percentage': tracker.progress_percentage,
                'completed_count': tracker.printed_quantity_total,  # Use printed quantity, not status count
                'total_count': tracker.total_quantity,  # Use total quantity, not file count
                'status': 'completed' if tracker.progress_percentage == 100 else 'in-progress'
            })
        
        return featured
    
    def _get_active_projects(self):
        """
        Get active projects (excluding completed, planning, on hold, canceled) with health status.
        
        Returns:
            List of project dictionaries with basic info and health status
        """
        projects = Project.objects.filter(
            status='In Progress'
        ).order_by('-start_date', '-id')[:10]
        
        active = []
        
        for project in projects:
            # Collect all applicable health statuses
            health_statuses = []
            health_reasons = []
            
            # Check if project is blocked by printer status
            blocked_printers = project.associated_printers.filter(
                status__in=['Under Repair', 'Sold', 'Archived']
            )
            
            is_blocked = blocked_printers.exists()
            is_overdue = False
            is_at_risk = False
            
            if is_blocked:
                # Build reason message for blocked status
                printer_names = list(blocked_printers.values_list('title', 'status'))
                if len(printer_names) == 1:
                    blocked_reason = f"Printer '{printer_names[0][0]}' is {printer_names[0][1]}"
                else:
                    reasons = [f"{name} ({status})" for name, status in printer_names]
                    blocked_reason = f"Printers: {', '.join(reasons)}"
                health_statuses.append('blocked')
                health_reasons.append(blocked_reason)
            
            # Check due date
            if project.due_date:
                days_until = project.days_until_due
                if days_until is not None:
                    if days_until < 0:
                        is_overdue = True
                        health_statuses.append('overdue')
                        health_reasons.append(f"Past due by {abs(days_until)} days")
                    elif days_until <= 7:
                        is_at_risk = True
                        health_statuses.append('at-risk')
                        health_reasons.append(f"Due in {days_until} days")
            
            # If no issues, it's healthy
            if not health_statuses:
                health_statuses.append('healthy')
            
            # Primary health is the most critical (overdue > blocked > at-risk > healthy)
            if is_overdue:
                primary_health = 'overdue'
            elif is_blocked:
                primary_health = 'blocked'
            elif is_at_risk:
                primary_health = 'at-risk'
            else:
                primary_health = 'healthy'
            
            # Combine reasons with semicolons
            combined_reason = '; '.join(health_reasons) if health_reasons else None
            
            active.append({
                'id': project.id,
                'name': project.project_name,
                'status': project.status,
                'health': primary_health,  # Primary for sorting/display
                'health_statuses': health_statuses,  # All applicable statuses
                'health_reason': combined_reason,
                'due_date': project.due_date.isoformat() if project.due_date else None,
                'days_until_due': project.days_until_due
            })
        
        return active


class DismissAlertView(APIView):
    """
    API endpoint to dismiss a single dashboard alert.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Dismiss a single alert with state-based invalidation.
        
        Request body:
            {
                'alert_type': str,     # e.g., 'printer_repair'
                'alert_id': str,       # e.g., 'printer_repair_1'
                'state_data': dict     # e.g., {'id': 1, 'status': 'Under Repair'}
            }
        
        The state_data is hashed and stored. If the state changes later
        (e.g., printer status changes), the dismissal becomes invalid.
        """
        alert_type = request.data.get('alert_type')
        alert_id = request.data.get('alert_id')
        state_data = request.data.get('state_data', {})
        
        if not alert_type or not alert_id:
            return Response(
                {'error': 'Both alert_type and alert_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate state hash for this alert
        dashboard_view = DashboardDataView()
        state_hash = dashboard_view._generate_state_hash(alert_type, state_data)
        
        # Create or update the dismissal record with state hash
        dismissal, created = AlertDismissal.objects.update_or_create(
            alert_type=alert_type,
            alert_id=alert_id,
            defaults={'state_hash': state_hash}
        )
        
        return Response({
            'success': True,
            'dismissed': {
                'alert_type': dismissal.alert_type,
                'alert_id': dismissal.alert_id,
                'dismissed_at': dismissal.dismissed_at,
                'state_hash': dismissal.state_hash
            }
        })


class DismissAllAlertsView(APIView):
    """
    API endpoint to dismiss multiple dashboard alerts at once.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Dismiss multiple alerts with state-based invalidation.
        
        Request body:
            {
                'alerts': [
                    {
                        'alert_type': str, 
                        'alert_id': str,
                        'state_data': dict
                    },
                    ...
                ]
            }
        """
        alerts = request.data.get('alerts', [])
        
        if not alerts or not isinstance(alerts, list):
            return Response(
                {'error': 'alerts array is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dashboard_view = DashboardDataView()
        dismissed_count = 0
        
        for alert in alerts:
            alert_type = alert.get('alert_type')
            alert_id = alert.get('alert_id')
            state_data = alert.get('state_data', {})
            
            if alert_type and alert_id:
                # Generate state hash
                state_hash = dashboard_view._generate_state_hash(alert_type, state_data)
                
                # Create or update dismissal with state hash
                AlertDismissal.objects.update_or_create(
                    alert_type=alert_type,
                    alert_id=alert_id,
                    defaults={'state_hash': state_hash}
                )
                dismissed_count += 1
        
        return Response({
            'success': True,
            'dismissed_count': dismissed_count
        })


class ImportDataView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        backup_file = request.FILES.get('backup_file')
        if not backup_file:
            return Response({'error': 'No backup file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Clear all data in the correct order
            TrackerFile.objects.all().delete()
            Tracker.objects.all().delete()
            ProjectPrinters.objects.all().delete()
            ProjectInventory.objects.all().delete()
            ProjectFile.objects.all().delete()
            ProjectLink.objects.all().delete()
            Project.objects.all().delete()
            InventoryItem.objects.all().delete()
            ModFile.objects.all().delete()
            Mod.objects.all().delete()
            Printer.objects.all().delete()
            Brand.objects.all().delete()
            PartType.objects.all().delete()
            Location.objects.all().delete()

            # Clear media directory
            media_root = settings.MEDIA_ROOT
            if os.path.isdir(media_root):
                for item in os.listdir(media_root):
                    item_path = os.path.join(media_root, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)

            # Extract all files from ZIP to media directory
            with zipfile.ZipFile(backup_file, 'r') as zf:
                for member in zf.namelist():
                    # Skip directory entries (paths ending with /)
                    if member.endswith('/'):
                        continue
                    
                    # Skip CSV files - we'll read them directly from ZIP, not extract to disk
                    if member.endswith('.csv'):
                        continue
                    
                    # Extract media files from recognized folders
                    if member.startswith(('inventory_photos/', 'printer_photos/', 'project_photos/', 'mod_files/', 'project_files/', 'trackers/')):
                        target_path = os.path.join(media_root, member)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, 'wb') as f:
                            f.write(zf.read(member))

                def read_csv_from_zip(zipfile_obj, filename):
                    with zipfile_obj.open(filename, 'r') as f:
                        reader = csv.reader(StringIO(f.read().decode('utf-8')))
                        header = next(reader)
                        return [dict(zip(header, row)) for row in reader]

                # Import Brands
                if 'inventory.csv' in zf.namelist():
                    inventory_rows = read_csv_from_zip(zf, 'inventory.csv')
                    for row in inventory_rows:
                        if row['brand']:
                            Brand.objects.get_or_create(name=row['brand'])
                        if row['part_type']:
                            PartType.objects.get_or_create(name=row['part_type'])
                        if row['location']:
                            Location.objects.get_or_create(name=row['location'])

                # Import Printers
                if 'printers.csv' in zf.namelist():
                    printer_rows = read_csv_from_zip(zf, 'printers.csv')
                    for row in printer_rows:
                        if row['manufacturer']:
                            Brand.objects.get_or_create(name=row['manufacturer'])

                # Import Locations, PartTypes, Brands (from other CSVs if needed)
                # (Already handled above)

                # Import Printer objects
                if 'printers.csv' in zf.namelist():
                    printer_rows = read_csv_from_zip(zf, 'printers.csv')
                    for row in printer_rows:
                        manufacturer = Brand.objects.filter(name=row['manufacturer']).first() if row['manufacturer'] else None
                        printer = Printer(
                            id=row['id'],
                            title=row['title'],
                            manufacturer=manufacturer,
                            serial_number=row.get('serial_number') or None,  # <-- Fix here
                            purchase_date=row.get('purchase_date', None) or None,
                            status=row.get('status', ''),
                            notes=row.get('notes', ''),
                            purchase_price=row.get('purchase_price', None) or None,
                            build_size_x=row.get('build_size_x', None) or None,
                            build_size_y=row.get('build_size_y', None) or None,
                            build_size_z=row.get('build_size_z', None) or None,
                            photo=f"printer_photos/{row['photo']}" if row.get('photo') else None,
                            last_maintained_date=row.get('last_maintained_date', None) or None,
                            maintenance_reminder_date=row.get('maintenance_reminder_date', None) or None,
                            last_carbon_replacement_date=row.get('last_carbon_replacement_date', None) or None,
                            carbon_reminder_date=row.get('carbon_reminder_date', None) or None,
                            maintenance_notes=row.get('maintenance_notes', ''),
                            moonraker_url=row.get('moonraker_url', None)
                        )
                        printer.save()

                # Import Inventory Items
                if 'inventory.csv' in zf.namelist():
                    inventory_rows = read_csv_from_zip(zf, 'inventory.csv')
                    for row in inventory_rows:
                        brand = Brand.objects.filter(name=row['brand']).first() if row['brand'] else None
                        part_type = PartType.objects.filter(name=row['part_type']).first() if row['part_type'] else None
                        location = Location.objects.filter(name=row['location']).first() if row['location'] else None
                        item = InventoryItem(
                            id=row['id'],
                            title=row['title'],
                            brand=brand,
                            part_type=part_type,
                            location=location,
                            quantity=int(row['quantity']) if row['quantity'] else 0,
                            cost=float(row['cost']) if row['cost'] else None,
                            notes=row.get('notes', ''),
                            photo=f"inventory_photos/{row['photo']}" if row.get('photo') else None,
                            is_consumable=row.get('is_consumable', 'false').lower() == 'true',
                            low_stock_threshold=int(row.get('low_stock_threshold', 0)) if row.get('low_stock_threshold') else None
                        )
                        item.save()

                # Import Projects
                if 'projects.csv' in zf.namelist():
                    project_rows = read_csv_from_zip(zf, 'projects.csv')
                    for row in project_rows:
                        project = Project(
                            id=row['id'],
                            project_name=row['project_name'],
                            description=row.get('description', ''),
                            status=row.get('status', ''),
                            start_date=row.get('start_date', None) or None,
                            end_date=row.get('end_date', None) or None,
                            notes=row.get('notes', ''),
                            photo=f"project_photos/{row['photo']}" if row.get('photo') else None
                        )
                        project.save()

                # Import Mods
                if 'mods.csv' in zf.namelist():
                    mod_rows = read_csv_from_zip(zf, 'mods.csv')
                    for row in mod_rows:
                        Mod.objects.create(
                            id=row['id'],
                            printer_id=row['printer_id'],
                            name=row['name'],
                            link=row['link'],
                            status=row['status']
                        )

                # Import ModFiles
                if 'modfiles.csv' in zf.namelist():
                    modfile_rows = read_csv_from_zip(zf, 'modfiles.csv')
                    for row in modfile_rows:
                        mf = ModFile(
                            id=row['id'],
                            mod_id=row['mod_id'],
                            file=f"mod_files/{row['file']}" if row.get('file') else None
                        )
                        mf.save()

                # Import ProjectLinks
                if 'project_links.csv' in zf.namelist():
                    link_rows = read_csv_from_zip(zf, 'project_links.csv')
                    for row in link_rows:
                        ProjectLink.objects.create(
                            id=row['id'],
                            project_id=row['project_id'],
                            name=row['name'],
                            url=row['url']
                        )

                # Import ProjectFiles
                if 'project_files.csv' in zf.namelist():
                    file_rows = read_csv_from_zip(zf, 'project_files.csv')
                    for row in file_rows:
                        pf = ProjectFile(
                            id=row['id'],
                            project_id=row['project_id'],
                            file=f"project_files/{row['file']}" if row.get('file') else None
                        )
                        pf.save()

                # Import ProjectInventory
                if 'project_inventory.csv' in zf.namelist():
                    proj_inv_rows = read_csv_from_zip(zf, 'project_inventory.csv')
                    for row in proj_inv_rows:
                        ProjectInventory.objects.create(
                            project_id=row['project_id'],
                            inventory_item_id=row['inventory_item_id'],
                            quantity_used=int(row.get('quantity_used', 0)) or 0 # <-- FIX HERE
                        )

                # Import ProjectPrinters
                if 'project_printers.csv' in zf.namelist():
                    proj_printer_rows = read_csv_from_zip(zf, 'project_printers.csv')
                    for row in proj_printer_rows:
                        ProjectPrinters.objects.create(
                            project_id=row['project_id'],
                            printer_id=row['printer_id']
                        )

                # Import Print Trackers
                if 'trackers.csv' in zf.namelist():
                    tracker_rows = read_csv_from_zip(zf, 'trackers.csv')
                    for row in tracker_rows:
                        tracker = Tracker(
                            id=row['id'],
                            name=row['name'],
                            project_id=row.get('project_id') or None,
                            github_url=row.get('github_url', ''),
                            storage_type=row.get('storage_type', 'links'),
                            primary_color=row.get('primary_color', '#3B82F6'),
                            accent_color=row.get('accent_color', '#EF4444'),
                            total_quantity=int(row.get('total_quantity', 0)) or 0,
                            printed_quantity_total=int(row.get('printed_quantity_total', 0)) or 0,
                            progress_percentage=int(row.get('progress_percentage', 0)) or 0,
                            created_date=row.get('created_date'),
                            updated_date=row.get('updated_date'),
                            storage_path=row.get('storage_path', ''),
                            total_storage_used=int(row.get('total_storage_used', 0)) or 0,
                            files_downloaded=row.get('files_downloaded', 'false').lower() == 'true'
                        )
                        tracker.save()

                # Import Tracker Files
                if 'tracker_files.csv' in zf.namelist():
                    trackerfile_rows = read_csv_from_zip(zf, 'tracker_files.csv')
                    for row in trackerfile_rows:
                        # Build the local file path if it exists
                        local_file_path = None
                        if row.get('local_file'):
                            # Files are stored in trackers/{tracker_id}/files/{directory_path}/{filename}
                            tracker_id = row['tracker_id']
                            directory_path = row.get('directory_path', '')
                            
                            if directory_path:
                                local_file_path = f"trackers/{tracker_id}/files/{directory_path}/{row['local_file']}"
                            else:
                                local_file_path = f"trackers/{tracker_id}/files/{row['local_file']}"
                        
                        tfile = TrackerFile(
                            id=row['id'],
                            tracker_id=row['tracker_id'],
                            storage_type=row.get('storage_type', 'link'),
                            filename=row['filename'],
                            directory_path=row.get('directory_path', ''),
                            github_url=row.get('github_url', ''),
                            local_file=local_file_path,
                            file_size=int(row.get('file_size', 0)) or 0,
                            sha=row.get('sha', ''),
                            color=row.get('color', ''),
                            material=row.get('material', ''),
                            quantity=int(row.get('quantity', 1)) or 1,
                            is_selected=row.get('is_selected', 'true').lower() == 'true',
                            status=row.get('status', 'not_started'),
                            printed_quantity=int(row.get('printed_quantity', 0)) or 0,
                            created_date=row.get('created_date'),
                            updated_date=row.get('updated_date'),
                            download_date=row.get('download_date') or None,
                            download_status=row.get('download_status', 'pending'),
                            download_error=row.get('download_error', ''),
                            downloaded_at=row.get('downloaded_at') or None,
                            file_checksum=row.get('file_checksum', ''),
                            actual_file_size=int(row.get('actual_file_size', 0)) if row.get('actual_file_size') else None
                        )
                        tfile.save()

            return Response({'success': 'Data restored successfully.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteAllData(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        try:
            TrackerFile.objects.all().delete()
            Tracker.objects.all().delete()
            ProjectPrinters.objects.all().delete()
            ProjectInventory.objects.all().delete()
            ProjectFile.objects.all().delete()
            ProjectLink.objects.all().delete()
            Project.objects.all().delete()
            InventoryItem.objects.all().delete()
            ModFile.objects.all().delete()
            Mod.objects.all().delete()
            Printer.objects.all().delete()
            Brand.objects.all().delete()
            PartType.objects.all().delete()
            Location.objects.all().delete()

            media_path = settings.MEDIA_ROOT
            if os.path.isdir(media_path):
                for item in os.listdir(media_path):
                    item_path = os.path.join(media_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
            
            return Response({'status': 'All data deleted'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ReminderViewSet(ReadOnlyViewSet):
    queryset = Printer.objects.exclude(maintenance_reminder_date__isnull=True, carbon_reminder_date__isnull=True)
    serializer_class = PrinterSerializer
    permission_classes = [AllowAny]

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]

class PartTypeViewSet(viewsets.ModelViewSet):
    queryset = PartType.objects.all().order_by('name')
    serializer_class = PartTypeSerializer
    permission_classes = [AllowAny]

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [AllowAny]

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all().order_by('name')
    serializer_class = MaterialSerializer
    permission_classes = [AllowAny]

class ModViewSet(viewsets.ModelViewSet):
    queryset = Mod.objects.all()
    serializer_class = ModSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['get'], url_path='download-files')
    def download_files(self, request, pk=None):
        mod = self.get_object()
        mod_files = mod.files.all()

        if not mod_files:
            return Response(status=status.HTTP_404_NOT_FOUND)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for mod_file in mod_files:
                file_path = mod_file.file.path
                if os.path.exists(file_path):
                    zf.write(file_path, os.path.basename(file_path))

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={mod.name}_files.zip'
        return response

class ModFileViewSet(viewsets.ModelViewSet):
    queryset = ModFile.objects.all()
    serializer_class = ModFileSerializer
    permission_classes = [AllowAny]

class ProjectLinkViewSet(viewsets.ModelViewSet):
    queryset = ProjectLink.objects.all()
    serializer_class = ProjectLinkSerializer
    permission_classes = [AllowAny]
    
class ProjectFileViewSet(viewsets.ModelViewSet):
    queryset = ProjectFile.objects.all()
    serializer_class = ProjectFileSerializer
    permission_classes = [AllowAny]

class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related('brand', 'part_type', 'location').prefetch_related('associated_projects').all().order_by('title')
    serializer_class = InventoryItemSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryItemFilter
    search_fields = ['title', 'brand__name', 'part_type__name', 'location__name', 'notes']
    ordering_fields = ['title', 'quantity', 'cost']

class PrinterViewSet(viewsets.ModelViewSet):
    queryset = Printer.objects.select_related('manufacturer').prefetch_related('mods__files', 'associated_projects').all().order_by('title')
    serializer_class = PrinterSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PrinterFilter
    search_fields = ['title', 'manufacturer__name', 'serial_number', 'status', 'notes']
    ordering_fields = ['title', 'manufacturer__name', 'status', 'purchase_date']

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related('associated_inventory_items__brand', 'associated_printers', 'links', 'files').all().order_by('project_name')
    serializer_class = ProjectSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ['project_name', 'description', 'status', 'notes']
    ordering_fields = ['project_name', 'status', 'start_date', 'end_date']

class ProjectInventoryViewSet(viewsets.ModelViewSet):
    queryset = ProjectInventory.objects.all()
    serializer_class = ProjectInventorySerializer
    permission_classes = [AllowAny]

class ProjectPrintersViewSet(viewsets.ModelViewSet):
    queryset = ProjectPrinters.objects.all()
    serializer_class = ProjectPrintersSerializer
    permission_classes = [AllowAny]

# --- New ViewSet for Low Stock Items ---
class LowStockItemsViewSet(ReadOnlyViewSet):
    """
    A viewset that returns a list of all inventory items that are
    marked as consumable and have a quantity at or below their
    low_stock_threshold.
    """
    serializer_class = InventoryItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return InventoryItem.objects.filter(
            is_consumable=True,
            low_stock_threshold__isnull=False,
            quantity__lte=F('low_stock_threshold')
        )


# ============================================================================
# PRINT TRACKER VIEWSETS
# ============================================================================

class TrackerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Print Trackers.
    
    Endpoints:
    - GET /api/trackers/ - List all trackers
    - POST /api/trackers/ - Create new tracker
    - GET /api/trackers/{id}/ - Get tracker detail
    - PUT/PATCH /api/trackers/{id}/ - Update tracker
    - DELETE /api/trackers/{id}/ - Delete tracker
    """
    queryset = Tracker.objects.all()
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'github_url']
    ordering_fields = ['name', 'created_date', 'updated_date']
    ordering = ['-created_date']
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return TrackerCreateSerializer
        elif self.action == 'list':
            return TrackerListSerializer
        return TrackerSerializer
    
    def get_queryset(self):
        """Allow filtering by project."""
        queryset = Tracker.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(project_id=project_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create a new tracker and optionally download files if storage_type is 'download'.
        
        Returns tracker data plus download_results if files were downloaded.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tracker = serializer.save()
        
        # Get tracker data for response
        response_serializer = TrackerSerializer(tracker)
        response_data = {
            'tracker': response_serializer.data
        }
        
        # Add download results if available (set by serializer during file downloads)
        if hasattr(tracker, '_download_results'):
            response_data['download_results'] = tracker._download_results
            
            # Add summary information
            successful_count = len(tracker._download_results.get('successful', []))
            failed_count = len(tracker._download_results.get('failed', []))
            total_count = successful_count + failed_count
            
            response_data['download_summary'] = {
                'total_files': total_count,
                'successful': successful_count,
                'failed': failed_count,
                'all_successful': failed_count == 0,
                'total_bytes': tracker._download_results.get('total_bytes', 0),
                'duration': tracker._download_results.get('duration', 0)
            }
        
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=False, methods=['post'], url_path='crawl-github')
    def crawl_github(self, request):
        """
        Crawl a GitHub repository and return printable files.
        
        POST /api/trackers/crawl-github/
        Body: {
            "github_url": "https://github.com/VoronDesign/Voron-0/tree/main/STLs",
            "force_refresh": false  // Optional
        }
        
        Returns file tree with all printable files, categorized by size.
        Results are cached for 1 hour unless force_refresh=true.
        """
        github_url = request.data.get('github_url')
        force_refresh = request.data.get('force_refresh', False)
        
        if not github_url:
            return Response(
                {
                    'success': False,
                    'error': 'github_url is required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = crawl_github_repository(github_url, force_refresh)
            return Response(result, status=status.HTTP_200_OK)
            
        except InvalidURLError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_type': 'invalid_url'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except RepositoryNotFoundError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_type': 'repo_not_found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except RateLimitError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_type': 'rate_limit'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
            
        except EmptyResultError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_type': 'empty_result'
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except NetworkError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_type': 'network_error'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        except GitHubCrawlerError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_type': 'unknown'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='fetch-url-metadata')
    def fetch_url_metadata(self, request):
        """
        Fetch metadata for a single URL (filename, size, source).
        
        POST /api/trackers/fetch-url-metadata/
        Body: {
            "url": "https://github.com/user/repo/file.stl"
        }
        
        Returns: {
            "filename": "file.stl",
            "size": 12345,
            "source": "GitHub"
        }
        """
        from urllib.parse import urlparse, unquote
        import requests
        
        url = request.data.get('url')
        if not url:
            return Response(
                {'error': 'url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Detect source
            if 'github.com' in domain:
                source = 'GitHub'
            elif 'printables.com' in domain:
                source = 'Printables'
            elif 'thingiverse.com' in domain:
                source = 'Thingiverse'
            else:
                source = 'URL'
            
            # Extract filename from URL and decode URL encoding
            filename = url.split('/')[-1].split('?')[0]
            filename = unquote(filename)  # Decode %5B to [, %5D to ], etc.
            if not filename:
                filename = 'unknown_file'
            
            # Try to get file size with HEAD request
            try:
                head_response = requests.head(url, timeout=5, allow_redirects=True)
                size = int(head_response.headers.get('Content-Length', 0))
            except:
                size = 0
            
            return Response({
                'filename': filename,
                'size': size,
                'source': source
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch metadata: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='create-manual')
    def create_manual(self, request):
        """
        Create a manual tracker with pre-defined files.
        Now supports automatic file downloads when storage_type='download'.
        
        POST /api/trackers/create-manual/
        Body: {
            "name": "Custom Build",
            "project": 1,  // Optional
            "storage_type": "download",  // 'download' or 'link'
            "files": [
                {
                    "name": "part.stl",
                    "url": "https://...",
                    "source": "GitHub",
                    "category": "Body",
                    "size": 12345
                }
            ]
        }
        """
        name = request.data.get('name')
        project_id = request.data.get('project')
        storage_type = request.data.get('storage_type', 'link')
        
        files = request.data.get('files', [])
        
        if not name:
            return Response(
                {'error': 'name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not files:
            return Response(
                {'error': 'at least one file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create tracker
            tracker = Tracker.objects.create(
                name=name,
                project_id=project_id if project_id else None,
                storage_type=storage_type,
                github_url='',  # No GitHub URL for manual trackers
                creation_mode='manual'
            )
            
            # Create tracker files
            created_files = []
            for file_data in files:
                tracker_file = TrackerFile.objects.create(
                    tracker=tracker,
                    filename=file_data.get('name', 'unknown'),
                    directory_path=file_data.get('category', ''),
                    github_url=file_data.get('url', ''),
                    file_size=file_data.get('size', 0),
                    is_selected=True,
                    status='pending',
                    color=file_data.get('color', 'Primary'),
                    material=file_data.get('material', 'PLA'),
                    quantity=file_data.get('quantity', 1),
                    printed_quantity=0
                )
                created_files.append(tracker_file)
            
            # If storage_type is 'local', download the files
            download_results = None
            if storage_type == 'local' and created_files:
                download_results = self._download_tracker_files_for_manual(tracker, created_files)
            
            # Get updated tracker data
            serializer = TrackerSerializer(tracker)
            response_data = {
                'success': True,
                'tracker': serializer.data
            }
            
            # Add download results if available
            if download_results:
                response_data['download_results'] = download_results
                
                successful_count = len(download_results.get('successful', []))
                failed_count = len(download_results.get('failed', []))
                
                response_data['download_summary'] = {
                    'total_files': len(created_files),
                    'successful': successful_count,
                    'failed': failed_count,
                    'all_successful': failed_count == 0,
                    'total_bytes': download_results.get('total_bytes', 0),
                    'duration': download_results.get('duration', 0)
                }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create tracker: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _download_tracker_files_for_manual(self, tracker, tracker_files):
        """
        Download files for a manually created tracker.
        Same logic as serializer's _download_tracker_files but for manual endpoint.
        """
        storage_manager = StorageManager()
        download_service = FileDownloadService()
        
        # Calculate total size needed
        total_size = sum(f.file_size for f in tracker_files if f.file_size)
        
        # Check available disk space
        try:
            space_check = storage_manager.check_available_space(total_size)
            if not space_check['sufficient']:
                for tf in tracker_files:
                    tf.download_status = 'failed'
                    tf.download_error = f"Insufficient disk space. Need {storage_manager._format_bytes(total_size)}, only {storage_manager._format_bytes(space_check['available'])} available."
                    tf.save()
                
                return {
                    'successful': [],
                    'failed': [{'file_id': tf.id, 'filename': tf.filename, 'error': tf.download_error} for tf in tracker_files],
                    'total_bytes': 0,
                    'error': 'Insufficient disk space'
                }
        except (InsufficientStorageError, StoragePermissionError) as e:
            for tf in tracker_files:
                tf.download_status = 'failed'
                tf.download_error = str(e)
                tf.save()
            
            return {
                'successful': [],
                'failed': [{'file_id': tf.id, 'filename': tf.filename, 'error': str(e)} for tf in tracker_files],
                'total_bytes': 0,
                'error': str(e)
            }
        
        # Get storage path for this tracker
        try:
            storage_path = storage_manager.get_tracker_storage_path(tracker.id, create=True)
            tracker.storage_path = storage_path
            tracker.save()
        except Exception as e:
            for tf in tracker_files:
                tf.download_status = 'failed'
                tf.download_error = f"Failed to create storage path: {str(e)}"
                tf.save()
            
            return {
                'successful': [],
                'failed': [{'file_id': tf.id, 'filename': tf.filename, 'error': f"Failed to create storage path: {str(e)}"} for tf in tracker_files],
                'total_bytes': 0,
                'error': f"Failed to create storage path: {str(e)}"
            }
        
        # Prepare file list for batch download
        # Also build a mapping of tracker_file_id to relative path for local_file field
        file_list = []
        file_path_mapping = {}  # Maps tracker_file_id to relative path from MEDIA_ROOT
        
        for tracker_file in tracker_files:
            category_path = storage_manager.get_category_path(
                tracker.id,
                tracker_file.directory_path or 'uncategorized',
                create=True
            )
            
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
            
            tracker_file.download_status = 'downloading'
            tracker_file.save()
        
        # Download files in batch
        results = download_service.download_files_batch(file_list)
        
        # Process results and update tracker files
        successful_downloads = []
        failed_downloads = []
        total_bytes_downloaded = 0
        
        for success_info in results['successful']:
            tracker_file = next((tf for tf in tracker_files if tf.id == success_info.get('tracker_file_id')), None)
            
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
            tracker_file = next((tf for tf in tracker_files if tf.id == fail_info.get('tracker_file_id')), None)
            
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
        tracker.files_downloaded = len(failed_downloads) == 0
        tracker.save()
        
        return {
            'successful': successful_downloads,
            'failed': failed_downloads,
            'total_bytes': total_bytes_downloaded,
            'duration': results.get('duration', 0)
        }
    
    @action(detail=True, methods=['post'], url_path='download-all-files')
    def download_all_files(self, request, pk=None):
        """
        Download all files for a tracker that have URLs but no local files.
        Useful when converting from 'link' storage to 'local' storage.
        
        POST /api/trackers/{id}/download-all-files/
        """
        tracker = self.get_object()
        
        # Get all files that have github_url but no local_file
        files_to_download = TrackerFile.objects.filter(
            tracker=tracker,
            github_url__isnull=False
        ).exclude(
            github_url=''
        ).filter(
            local_file=''
        )
        
        if not files_to_download.exists():
            return Response({
                'success': True,
                'message': 'No files need to be downloaded',
                'count': 0
            })
        
        # Download the files
        try:
            download_results = self._download_new_files(tracker, list(files_to_download))
            
            # Update tracker storage_type to 'local' if it isn't already
            if tracker.storage_type != 'local':
                tracker.storage_type = 'local'
                tracker.save()
            
            return Response({
                'success': True,
                'download_results': download_results,
                'downloaded_count': len(download_results.get('successful', [])),
                'failed_count': len(download_results.get('failed', [])),
                'total_files': len(files_to_download)
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to download files: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='download-zip')
    def download_zip(self, request, pk=None):
        """
        Download all tracker files as a ZIP archive.
        - For local files: include them from storage
        - For link files: download from URL and include
        
        GET /api/trackers/{id}/download-zip/
        """
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            tracker = self.get_object()
            
            # Create in-memory ZIP file
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Get all files for this tracker
                files = TrackerFile.objects.filter(tracker=tracker).order_by('directory_path', 'filename')
                
                if not files.exists():
                    return Response(
                        {'error': 'No files found for this tracker'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Track files added to avoid duplicates
                added_files = set()
                
                for file in files:
                    # Generate a unique filename with category prefix (using directory_path)
                    category_prefix = file.directory_path.replace('/', '_').replace('\\', '_') if file.directory_path else 'Uncategorized'
                    safe_filename = f"{category_prefix}/{file.filename}"
                    
                    # Avoid duplicate filenames
                    counter = 1
                    original_safe_filename = safe_filename
                    while safe_filename in added_files:
                        name, ext = os.path.splitext(original_safe_filename)
                        safe_filename = f"{name}_{counter}{ext}"
                        counter += 1
                    
                    try:
                        # Check if file exists locally
                        if file.local_file and os.path.exists(file.local_file.path):
                            # Add local file to ZIP
                            zip_file.write(file.local_file.path, safe_filename)
                            added_files.add(safe_filename)
                        elif file.github_url:
                            # Download from URL and add to ZIP
                            download_service = FileDownloadService()
                            
                            # Create temporary file
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.stl') as temp_file:
                                temp_path = temp_file.name
                            
                            try:
                                # Download to temp file
                                result = download_service.download_with_retry(
                                    file.github_url,
                                    temp_path,
                                    max_retries=2
                                )
                                
                                # Add to ZIP
                                zip_file.write(temp_path, safe_filename)
                                added_files.add(safe_filename)
                            except (DownloadError, DownloadTimeoutError, FileTooLargeError) as download_err:
                                # Add error note instead of failing completely
                                error_filename = f"{safe_filename}.error.txt"
                                error_msg = f"Failed to download: {file.github_url}\nError: {str(download_err)}\n"
                                zip_file.writestr(error_filename, error_msg)
                            finally:
                                # Clean up temp file
                                if os.path.exists(temp_path):
                                    try:
                                        os.remove(temp_path)
                                    except:
                                        pass  # Ignore cleanup errors
                    except Exception as e:
                        # Log error but continue with other files
                        logger.error(f"Error processing file {file.filename}: {str(e)}")
                        logger.error(traceback.format_exc())
                        error_filename = f"{safe_filename}.error.txt"
                        error_msg = f"Error processing file: {str(e)}\nURL: {file.github_url or 'N/A'}\n"
                        zip_file.writestr(error_filename, error_msg)
                        continue
            
            # Prepare response
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            safe_tracker_name = tracker.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            response['Content-Disposition'] = f'attachment; filename="{safe_tracker_name}_files.zip"'
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to create ZIP file: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'Failed to create ZIP file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='add-files')
    def add_files(self, request, pk=None):
        """
        Add new files to an existing tracker and optionally download them.
        
        POST /api/trackers/{id}/add-files/
        Body: {
            "files": [
                {
                    "name": "new_part.stl",
                    "url": "https://...",
                    "source": "GitHub",
                    "category": "Body",
                    "size": 12345,
                    "quantity": 1,
                    "color": "Primary",
                    "material": "ABS"
                }
            ]
        }
        """
        tracker = self.get_object()
        files = request.data.get('files', [])
        
        if not files:
            return Response(
                {'error': 'at least one file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            added_files = []
            updated_files = []
            
            for file_data in files:
                # Check if file already exists
                existing_file = TrackerFile.objects.filter(
                    tracker=tracker,
                    directory_path=file_data.get('category', ''),
                    filename=file_data.get('name', 'unknown')
                ).first()
                
                if existing_file:
                    # Update existing file
                    existing_file.github_url = file_data.get('url', existing_file.github_url)
                    existing_file.file_size = file_data.get('size', existing_file.file_size)
                    existing_file.quantity = file_data.get('quantity', existing_file.quantity)
                    existing_file.color = file_data.get('color', existing_file.color)
                    existing_file.material = file_data.get('material', existing_file.material)
                    existing_file.status = 'not_started'
                    existing_file.is_selected = True
                    existing_file.save()
                    updated_files.append(existing_file)
                    added_files.append(existing_file)  # Include in added_files for download
                else:
                    # Create new TrackerFile
                    tracker_file = TrackerFile.objects.create(
                        tracker=tracker,
                        filename=file_data.get('name', 'unknown'),
                        directory_path=file_data.get('category', ''),
                        github_url=file_data.get('url', ''),
                        file_size=file_data.get('size', 0),
                        quantity=file_data.get('quantity', 1),
                        color=file_data.get('color', 'Primary'),
                        material=file_data.get('material', 'ABS'),
                        status='not_started',
                        is_selected=True
                    )
                    added_files.append(tracker_file)
            
            # If tracker storage_type is 'local', download the new files
            download_results = None
            if tracker.storage_type == 'local' and added_files:
                download_results = self._download_new_files(tracker, added_files)
            
            # Serialize response
            file_serializer = TrackerFileSerializer(added_files, many=True)
            
            response_data = {
                'success': True,
                'added_files': file_serializer.data,
                'count': len(added_files),
                'created_count': len(added_files) - len(updated_files),
                'updated_count': len(updated_files)
            }
            
            # Add download results if available
            if download_results:
                response_data['download_results'] = download_results
                
                successful_count = len(download_results.get('successful', []))
                failed_count = len(download_results.get('failed', []))
                
                response_data['download_summary'] = {
                    'total_files': len(added_files),
                    'successful': successful_count,
                    'failed': failed_count,
                    'all_successful': failed_count == 0,
                    'total_bytes': download_results.get('total_bytes', 0),
                    'duration': download_results.get('duration', 0)
                }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to add files: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _download_new_files(self, tracker, tracker_files):
        """
        Download new files being added to an existing tracker.
        Similar to the serializer's _download_tracker_files but for add-files action.
        
        Returns:
            dict: Download results with successful/failed files
        """
        storage_manager = StorageManager()
        download_service = FileDownloadService()
        
        # Calculate total size needed for new files
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
        except (InsufficientStorageError, StoragePermissionError) as e:
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
        
        # Get storage path for this tracker (should already exist)
        try:
            if not tracker.storage_path:
                storage_path = storage_manager.get_tracker_storage_path(tracker.id, create=True)
                tracker.storage_path = storage_path
                tracker.save()
        except Exception as e:
            for tf in tracker_files:
                tf.download_status = 'failed'
                tf.download_error = f"Failed to access storage path: {str(e)}"
                tf.save()
            
            return {
                'successful': [],
                'failed': [
                    {
                        'file_id': tf.id,
                        'filename': tf.filename,
                        'error': f"Failed to access storage path: {str(e)}"
                    } for tf in tracker_files
                ],
                'total_bytes': 0,
                'error': f"Failed to access storage path: {str(e)}"
            }
        
        # Prepare file list for batch download
        # Also build a mapping of tracker_file_id to relative path for local_file field
        file_list = []
        file_path_mapping = {}  # Maps tracker_file_id to relative path from MEDIA_ROOT
        
        for tracker_file in tracker_files:
            # Get category path
            category_path = storage_manager.get_category_path(
                tracker.id,
                tracker_file.directory_path or 'uncategorized',
                create=True
            )
            
            # Sanitize filename
            safe_filename = storage_manager.sanitize_filename(tracker_file.filename)
            destination = f"{category_path}/{safe_filename}"
            
            # Build relative path for FileField (relative to MEDIA_ROOT)
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
        
        # Update tracker totals (add to existing storage used)
        tracker.total_storage_used = (tracker.total_storage_used or 0) + total_bytes_downloaded
        
        # Update files_downloaded flag: True only if ALL files (old + new) are downloaded
        all_files = TrackerFile.objects.filter(tracker=tracker)
        tracker.files_downloaded = all(
            f.download_status == 'completed' 
            for f in all_files 
            if tracker.storage_type == 'local'
        )
        tracker.save()
        
        return {
            'successful': successful_downloads,
            'failed': failed_downloads,
            'total_bytes': total_bytes_downloaded,
            'duration': results.get('duration', 0)
        }
    
    @action(detail=True, methods=['get'], url_path='download-files')
    def download_files(self, request, pk=None):
        """
        Download all tracker files as a ZIP archive.
        Only works for trackers with storage_type='local' that have downloaded files.
        
        GET /api/trackers/{id}/download-files/
        
        Returns:
            ZIP file with all tracker files
        """
        tracker = self.get_object()
        
        # Only allow download for trackers with local storage
        if tracker.storage_type != 'local':
            return Response(
                {'error': 'This tracker uses GitHub links only. No local files to download.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if tracker has any downloaded files
        if not tracker.files_downloaded:
            return Response(
                {'error': 'No files have been downloaded for this tracker yet.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all tracker files
        tracker_files = TrackerFile.objects.filter(tracker=tracker, download_status='completed')
        
        if not tracker_files.exists():
            return Response(
                {'error': 'No completed file downloads found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Create ZIP file in memory
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for tracker_file in tracker_files:
                    if tracker_file.local_file:
                        # Get the full file path from FileField
                        file_path = tracker_file.local_file.path
                        
                        if os.path.exists(file_path):
                            # Preserve directory structure in ZIP
                            # Use directory_path + filename for the archive path
                            if tracker_file.directory_path:
                                archive_name = f"{tracker_file.directory_path}/{tracker_file.filename}"
                            else:
                                archive_name = tracker_file.filename
                            
                            zip_file.write(file_path, archive_name)
            
            # Prepare response
            zip_buffer.seek(0)
            
            # Create a safe filename
            safe_tracker_name = "".join(c for c in tracker.name if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = f"{safe_tracker_name}_files.zip"
            
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create ZIP file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='download-progress')
    def download_progress(self, request, pk=None):
        """
        Get real-time download progress for a tracker.
        Used for polling during file downloads.
        
        GET /api/trackers/{id}/download-progress/
        
        Returns:
        {
            "status": "downloading" | "completed" | "failed",
            "total_files": 46,
            "downloaded_files": 12,
            "failed_files": 1,
            "current_file": "bracket.stl",
            "progress_percent": 26,
            "files": [
                {
                    "id": 1,
                    "filename": "base.stl",
                    "status": "completed",
                    "size": 12345
                },
                ...
            ]
        }
        """
        tracker = self.get_object()
        
        # Get all tracker files
        tracker_files = tracker.files.all()
        total_files = tracker_files.count()
        
        if total_files == 0:
            return Response({
                'status': 'completed',
                'total_files': 0,
                'downloaded_files': 0,
                'failed_files': 0,
                'current_file': None,
                'progress_percent': 100,
                'files': []
            })
        
        # Count by status
        completed = tracker_files.filter(download_status='completed').count()
        failed = tracker_files.filter(download_status='failed').count()
        downloading = tracker_files.filter(download_status='downloading').count()
        pending = tracker_files.filter(download_status='pending').count()
        
        # Determine overall status
        if completed + failed == total_files:
            # All files processed
            if failed > 0:
                status_value = 'completed_with_errors'
            else:
                status_value = 'completed'
        elif downloading > 0 or pending > 0:
            status_value = 'downloading'
        else:
            status_value = 'pending'
        
        # Get current file being downloaded
        current_file = tracker_files.filter(download_status='downloading').first()
        current_filename = current_file.filename if current_file else None
        
        # Calculate progress percentage
        progress_percent = int((completed / total_files) * 100) if total_files > 0 else 0
        
        # Build file list with statuses
        files_data = []
        for tf in tracker_files.order_by('id'):
            files_data.append({
                'id': tf.id,
                'filename': tf.filename,
                'status': tf.download_status,
                'size': tf.actual_file_size or tf.file_size,
                'error': tf.download_error if tf.download_status == 'failed' else None
            })
        
        return Response({
            'status': status_value,
            'total_files': total_files,
            'downloaded_files': completed,
            'failed_files': failed,
            'current_file': current_filename,
            'progress_percent': progress_percent,
            'files': files_data
        })
    
    @action(detail=True, methods=['post'], url_path='upload-files')
    def upload_files(self, request, pk=None):
        """
        Upload files directly to a tracker from local computer.
        
        POST /api/trackers/{id}/upload-files/
        
        Request (multipart/form-data):
        - files: Multiple file uploads (required)
        - category: Optional category/directory (default: 'Uploads')
        - color: Optional color configuration
        - material: Optional material configuration
        - quantity: Optional quantity (default: 1)
        
        Returns:
        {
            "success": true,
            "uploaded_files": [
                {"id": 1, "filename": "bracket.stl", ...},
                ...
            ],
            "total_files": 3,
            "total_bytes": 12345
        }
        """
        tracker = self.get_object()
        uploaded_files = request.FILES.getlist('files')
        
        if not uploaded_files:
            return Response(
                {
                    'success': False,
                    'error': 'No files provided'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get optional metadata
        category = request.data.get('category', 'Uploads')
        color = request.data.get('color', '')
        material = request.data.get('material', '')
        quantity = int(request.data.get('quantity', 1))
        
        # Use StorageManager to save files
        storage_manager = StorageManager()
        created_files = []
        updated_files = []
        skipped_files = []
        total_bytes = 0
        
        for uploaded_file in uploaded_files:
            try:
                # Build file path: trackers/{tracker_id}/files/{category}/{filename}
                if category:
                    file_path = f"trackers/{tracker.id}/files/{category}/{uploaded_file.name}"
                else:
                    file_path = f"trackers/{tracker.id}/files/{uploaded_file.name}"
                
                # Check if file already exists
                existing_file = TrackerFile.objects.filter(
                    tracker=tracker,
                    directory_path=category,
                    filename=uploaded_file.name
                ).first()
                
                # Save file using StorageManager
                saved_path = storage_manager.save_uploaded_file(uploaded_file, file_path)
                
                if existing_file:
                    # Update existing file
                    existing_file.local_file = saved_path
                    existing_file.file_size = uploaded_file.size
                    existing_file.actual_file_size = uploaded_file.size
                    existing_file.storage_type = 'local'
                    existing_file.download_status = 'completed'
                    existing_file.download_date = timezone.now()
                    
                    # Update metadata if provided
                    if color:
                        existing_file.color = color
                    if material:
                        existing_file.material = material
                    if quantity:
                        existing_file.quantity = quantity
                    
                    existing_file.save()
                    updated_files.append(existing_file)
                    total_bytes += uploaded_file.size
                else:
                    # Create new TrackerFile record
                    tracker_file = TrackerFile.objects.create(
                        tracker=tracker,
                        storage_type='local',  # Mark as locally uploaded/stored
                        filename=uploaded_file.name,
                        directory_path=category,
                        local_file=saved_path,
                        file_size=uploaded_file.size,
                        actual_file_size=uploaded_file.size,
                        color=color,
                        material=material,
                        quantity=quantity,
                        status='not_started',
                        is_selected=True,
                        download_status='completed',  # Already "downloaded" since uploaded
                        download_date=timezone.now()
                    )
                    
                    created_files.append(tracker_file)
                    total_bytes += uploaded_file.size
                
            except Exception as e:
                # If any file fails, continue with others but log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to upload {uploaded_file.name}: {str(e)}")
                skipped_files.append({
                    'filename': uploaded_file.name,
                    'error': str(e)
                })
                continue
        
        if not created_files and not updated_files:
            return Response(
                {
                    'success': False,
                    'error': 'All file uploads failed',
                    'skipped_files': skipped_files
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update tracker stats
        tracker.recalculate_stats()
        tracker.save()
        
        # Serialize created and updated files
        all_files = created_files + updated_files
        serializer = TrackerFileSerializer(all_files, many=True)
        
        return Response({
            'success': True,
            'uploaded_files': serializer.data,
            'created_count': len(created_files),
            'updated_count': len(updated_files),
            'skipped_count': len(skipped_files),
            'skipped_files': skipped_files,
            'total_bytes': total_bytes
        }, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to cleanup local files when deleting a tracker.
        Only deletes files if storage_type='local' (downloaded files).
        """
        tracker = self.get_object()
        tracker_id = tracker.id
        storage_type = tracker.storage_type
        
        # Delete the tracker (CASCADE will delete TrackerFile records)
        response = super().destroy(request, *args, **kwargs)
        
        # Cleanup local files if tracker had downloaded files
        if storage_type == 'local':
            from .services.storage_manager import StorageManager
            import logging
            logger = logging.getLogger(__name__)
            
            storage_manager = StorageManager()
            cleanup_result = storage_manager.cleanup_tracker_files(tracker_id)
            
            # Log cleanup result
            if cleanup_result['success']:
                logger.info(f"Successfully cleaned up {cleanup_result['deleted_files']} files ({cleanup_result['deleted_bytes']} bytes) for tracker {tracker_id}")
            else:
                logger.error(f"Failed to cleanup files for tracker {tracker_id}: {cleanup_result.get('error')}")
        
        return response


class TrackerFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Tracker Files.
    
    Endpoints:
    - GET /api/tracker-files/ - List all tracker files
    - POST /api/tracker-files/ - Create new tracker file
    - GET /api/tracker-files/{id}/ - Get file detail
    - PUT/PATCH /api/tracker-files/{id}/ - Update file (config, status)
    - DELETE /api/tracker-files/{id}/ - Delete file
    """
    queryset = TrackerFile.objects.all()
    serializer_class = TrackerFileSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['filename', 'directory_path']
    filterset_fields = ['tracker', 'status', 'color', 'material', 'is_selected']
    
    def get_queryset(self):
        """Allow filtering by tracker."""
        queryset = TrackerFile.objects.all()
        tracker_id = self.request.query_params.get('tracker', None)
        if tracker_id is not None:
            queryset = queryset.filter(tracker_id=tracker_id)
        return queryset
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Custom endpoint to update file status and printed quantity."""
        file = self.get_object()
        file.status = request.data.get('status', file.status)
        file.printed_quantity = request.data.get('printed_quantity', file.printed_quantity)
        file.save()
        serializer = self.get_serializer(file)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_configuration(self, request, pk=None):
        """Custom endpoint to update file configuration (color, material, quantity)."""
        file = self.get_object()
        file.color = request.data.get('color', file.color)
        file.material = request.data.get('material', file.material)
        file.quantity = request.data.get('quantity', file.quantity)
        file.save()
        serializer = self.get_serializer(file)
        return Response(serializer.data)