# printvault/inventory/views.py
import csv
import zipfile
import os
import shutil
from io import BytesIO, StringIO
from datetime import date, timedelta
from django.http import HttpResponse
from rest_framework import viewsets, filters, mixins
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from .models import (
    Brand, PartType, Location, Printer, Mod, ModFile,
    InventoryItem, Project, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters
)
from .serializers import (
    BrandSerializer, PartTypeSerializer, LocationSerializer, PrinterSerializer, ModSerializer, ModFileSerializer,
    InventoryItemSerializer, ProjectSerializer, ProjectLinkSerializer, ProjectFileSerializer,
    ProjectInventorySerializer, ProjectPrintersSerializer
)
from .filters import InventoryItemFilter, PrinterFilter, ProjectFilter

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

            # Add media files to zip
            media_root = settings.MEDIA_ROOT
            for root, dirs, files in os.walk(media_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, media_root)
                    zf.write(file_path, arcname)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=print-vault-backup.zip'
        return response

class ImportDataView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        backup_file = request.FILES.get('backup_file')
        if not backup_file:
            return Response({'error': 'No backup file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Clear all data in the correct order
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
                    # Only extract media files (folders) and CSVs
                    if member.startswith(('inventory_photos/', 'printer_photos/', 'project_photos/', 'mod_files/', 'project_files/')) and not member.endswith('/'):
                        target_path = os.path.join(media_root, member)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, 'wb') as f:
                            f.write(zf.read(member))
                    # Optionally, extract CSVs to media_root for easier reading (not strictly necessary)
                    elif member.endswith('.csv'):
                        target_path = os.path.join(media_root, member)
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
            
            # Add a print statement for debugging
            print("--- Import process completed successfully ---")

            return Response({'success': 'Data restored successfully.'}, status=status.HTTP_200_OK)
        except Exception as e:
            # Also print the error to the console for debugging
            print(f"--- AN ERROR OCCURRED DURING IMPORT: {e} ---")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteAllData(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        try:
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

class ModViewSet(viewsets.ModelViewSet):
    queryset = Mod.objects.all()
    serializer_class = ModSerializer
    permission_classes = [AllowAny]

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