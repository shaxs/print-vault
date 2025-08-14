# printvault/inventory/views.py
import csv
import zipfile
import os
import shutil
from io import BytesIO, StringIO
from datetime import date, timedelta
from django.http import HttpResponse
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
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

class ExportDataView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            inv_buffer = StringIO()
            inv_writer = csv.writer(inv_buffer)
            inv_writer.writerow(['id', 'title', 'brand', 'part_type', 'location', 'quantity', 'cost', 'notes', 'photo'])
            for item in InventoryItem.objects.all():
                inv_writer.writerow([item.id, item.title, item.brand.name if item.brand else '', item.part_type.name if item.part_type else '', item.location.name if item.location else '', item.quantity, item.cost, item.notes, os.path.basename(item.photo.name) if item.photo else ''])
            zf.writestr('inventory.csv', inv_buffer.getvalue())
            printer_buffer = StringIO()
            printer_writer = csv.writer(printer_buffer)
            printer_writer.writerow(['id', 'title', 'manufacturer', 'serial_number', 'status', 'notes', 'purchase_price', 'purchase_date', 'build_size_x', 'build_size_y', 'build_size_z', 'last_maintained_date', 'maintenance_reminder_date', 'last_carbon_replacement_date', 'carbon_reminder_date', 'maintenance_notes', 'photo'])
            for printer in Printer.objects.all():
                printer_writer.writerow([printer.id, printer.title, printer.manufacturer.name if printer.manufacturer else '', printer.serial_number, printer.status, printer.notes, printer.purchase_price, printer.purchase_date, printer.build_size_x, printer.build_size_y, printer.build_size_z, printer.last_maintained_date, printer.maintenance_reminder_date, printer.last_carbon_replacement_date, printer.carbon_reminder_date, printer.maintenance_notes, os.path.basename(printer.photo.name) if printer.photo else ''])
            zf.writestr('printers.csv', printer_buffer.getvalue())
            project_buffer = StringIO()
            project_writer = csv.writer(project_buffer)
            project_writer.writerow(['id', 'project_name', 'description', 'status', 'start_date', 'end_date', 'notes', 'photo'])
            for project in Project.objects.all():
                project_writer.writerow([project.id, project.project_name, project.description, project.status, project.start_date, project.end_date, project.notes, os.path.basename(project.photo.name) if project.photo else ''])
            zf.writestr('projects.csv', project_buffer.getvalue())
            mod_buffer = StringIO()
            mod_writer = csv.writer(mod_buffer)
            mod_writer.writerow(['id', 'printer_id', 'name', 'link', 'status'])
            for mod in Mod.objects.all():
                mod_writer.writerow([mod.id, mod.printer_id, mod.name, mod.link, mod.status])
            zf.writestr('mods.csv', mod_buffer.getvalue())
            modfile_buffer = StringIO()
            modfile_writer = csv.writer(modfile_buffer)
            modfile_writer.writerow(['id', 'mod_id', 'file'])
            for modfile in ModFile.objects.all():
                modfile_writer.writerow([modfile.id, modfile.mod_id, os.path.basename(modfile.file.name) if modfile.file else ''])
            zf.writestr('modfiles.csv', modfile_buffer.getvalue())
            plink_buffer = StringIO()
            plink_writer = csv.writer(plink_buffer)
            plink_writer.writerow(['id', 'project_id', 'name', 'url'])
            for link in ProjectLink.objects.all():
                plink_writer.writerow([link.id, link.project_id, link.name, link.url])
            zf.writestr('project_links.csv', plink_buffer.getvalue())
            pfile_buffer = StringIO()
            pfile_writer = csv.writer(pfile_buffer)
            pfile_writer.writerow(['id', 'project_id', 'file'])
            for pfile in ProjectFile.objects.all():
                pfile_writer.writerow([pfile.id, pfile.project_id, os.path.basename(pfile.file.name) if pfile.file else ''])
            zf.writestr('project_files.csv', pfile_buffer.getvalue())
            proj_inv_buffer = StringIO()
            proj_inv_writer = csv.writer(proj_inv_buffer)
            proj_inv_writer.writerow(['project_id', 'inventory_item_id'])
            for rel in ProjectInventory.objects.all():
                proj_inv_writer.writerow([rel.project_id, rel.inventory_item_id])
            zf.writestr('project_inventory.csv', proj_inv_buffer.getvalue())
            proj_printer_buffer = StringIO()
            proj_printer_writer = csv.writer(proj_printer_buffer)
            proj_printer_writer.writerow(['project_id', 'printer_id'])
            for rel in ProjectPrinters.objects.all():
                proj_printer_writer.writerow([rel.project_id, rel.printer_id])
            zf.writestr('project_printers.csv', proj_printer_buffer.getvalue())
            media_root = settings.MEDIA_ROOT
            if os.path.isdir(media_root):
                for root, _, files in os.walk(media_root):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, media_root)
                        zf.write(file_path, arcname)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="print_vault_backup.zip"'
        return response

class DeleteAllData(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        for model in [ModFile, Mod, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters, InventoryItem, Printer, Project, Brand, PartType, Location]:
            model.objects.all().delete()
        media_root = settings.MEDIA_ROOT
        if os.path.isdir(media_root):
            for item in os.listdir(media_root):
                item_path = os.path.join(media_root, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ImportDataView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        zip_file = request.FILES.get('backup_file')
        if not zip_file:
            return Response({'error': 'Backup ZIP file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                if 'inventory.csv' not in zf.namelist():
                    return Response({'error': 'Backup is missing the required inventory.csv file.'}, status=status.HTTP_400_BAD_REQUEST)
                
                for model in [ModFile, Mod, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters, InventoryItem, Printer, Project, Brand, PartType, Location]:
                    model.objects.all().delete()
                media_root = settings.MEDIA_ROOT
                if os.path.isdir(media_root):
                    for item in os.listdir(media_root):
                        item_path = os.path.join(media_root, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                
                zf.extractall(media_root)

                def read_csv_from_zip(zipfile_obj, filename):
                    with zipfile_obj.open(filename, 'r') as f:
                        reader = csv.reader(StringIO(f.read().decode('utf-8')))
                        next(reader)
                        return list(reader)

                all_brands, all_part_types, all_locations = set(), set(), set()
                inventory_data = read_csv_from_zip(zf, 'inventory.csv')
                for row in inventory_data:
                    if len(row) > 4 and row[2]: all_brands.add(row[2])
                    if len(row) > 4 and row[3]: all_part_types.add(row[3])
                    if len(row) > 4 and row[4]: all_locations.add(row[4])
                
                printers_data = read_csv_from_zip(zf, 'printers.csv')
                for row in printers_data:
                    if len(row) > 2 and row[2]: all_brands.add(row[2])

                for name in all_brands: Brand.objects.get_or_create(name=name)
                for name in all_part_types: PartType.objects.get_or_create(name=name)
                for name in all_locations: Location.objects.get_or_create(name=name)
                
                for row in printers_data:
                    manufacturer = Brand.objects.get(name=row[2]) if row[2] else None
                    serial = row[3] if row[3] else None
                    p = Printer(id=row[0], title=row[1], manufacturer=manufacturer, serial_number=serial, status=row[4], notes=row[5], purchase_price=row[6] if row[6] else None, purchase_date=row[7] if row[7] else None, build_size_x=row[8] if row[8] else None, build_size_y=row[9] if row[9] else None, build_size_z=row[10] if row[10] else None, last_maintained_date=row[11] if row[11] else None, maintenance_reminder_date=row[12] if row[12] else None, last_carbon_replacement_date=row[13] if row[13] else None, carbon_reminder_date=row[14] if row[14] else None, maintenance_notes=row[15])
                    if len(row) > 16 and row[16]: p.photo.name = f'printer_photos/{row[16]}'
                    p.save()
                
                for row in inventory_data:
                    brand = Brand.objects.get(name=row[2]) if row[2] else None
                    part_type = PartType.objects.get(name=row[3]) if row[3] else None
                    location = Location.objects.get(name=row[4]) if row[4] else None
                    quantity_val = int(float(row[5])) if row[5] else 1
                    item = InventoryItem(id=row[0], title=row[1], brand=brand, part_type=part_type, location=location, quantity=quantity_val, cost=row[6] if row[6] else None, notes=row[7])
                    if len(row) > 8 and row[8]: item.photo.name = f'inventory_photos/{row[8]}'
                    item.save()

                projects_data = read_csv_from_zip(zf, 'projects.csv')
                for row in projects_data:
                    proj = Project(id=row[0], project_name=row[1], description=row[2], status=row[3], start_date=row[4] if row[4] else None, end_date=row[5] if row[5] else None, notes=row[6])
                    if len(row) > 7 and row[7]: proj.photo.name = f'project_photos/{row[7]}'
                    proj.save()
                
                if 'mods.csv' in zf.namelist():
                    mods_data = read_csv_from_zip(zf, 'mods.csv')
                    for row in mods_data: Mod.objects.create(id=row[0], printer_id=row[1], name=row[2], link=row[3], status=row[4])
                
                if 'modfiles.csv' in zf.namelist():
                    modfiles_data = read_csv_from_zip(zf, 'modfiles.csv')
                    for row in modfiles_data:
                        mf = ModFile(id=row[0], mod_id=row[1])
                        if row[2]: mf.file.name = f'mod_files/{row[2]}'
                        mf.save()
                
                if 'project_links.csv' in zf.namelist():
                    links_data = read_csv_from_zip(zf, 'project_links.csv')
                    for row in links_data: ProjectLink.objects.create(id=row[0], project_id=row[1], name=row[2], url=row[3])
                
                if 'project_files.csv' in zf.namelist():
                    files_data = read_csv_from_zip(zf, 'project_files.csv')
                    for row in files_data:
                        pf = ProjectFile(id=row[0], project_id=row[1])
                        if row[2]: pf.file.name = f'project_files/{row[2]}'
                        pf.save()

                if 'project_inventory.csv' in zf.namelist():
                    proj_inv_data = read_csv_from_zip(zf, 'project_inventory.csv')
                    for row in proj_inv_data: ProjectInventory.objects.create(project_id=row[0], inventory_item_id=row[1])

                if 'project_printers.csv' in zf.namelist():
                    proj_printer_data = read_csv_from_zip(zf, 'project_printers.csv')
                    for row in proj_printer_data: ProjectPrinters.objects.create(project_id=row[0], printer_id=row[1])

                for csv_file in zf.namelist():
                    if csv_file.endswith('.csv'):
                        os.remove(os.path.join(media_root, csv_file))
        except zipfile.BadZipFile:
            return Response({'error': 'Malformed ZIP file.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred during import: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_204_NO_CONTENT)

class MaintenanceRemindersView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        reminder_threshold = date.today() + timedelta(days=7)
        reminders_queryset = Printer.objects.filter(
            Q(maintenance_reminder_date__isnull=False, maintenance_reminder_date__lte=reminder_threshold) |
            Q(carbon_reminder_date__isnull=False, carbon_reminder_date__lte=reminder_threshold)
        ).distinct()
        serializer = PrinterSerializer(reminders_queryset, many=True)
        return Response(serializer.data)

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
class PartTypeViewSet(viewsets.ModelViewSet):
    queryset = PartType.objects.all()
    serializer_class = PartTypeSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
class ModViewSet(viewsets.ModelViewSet):
    queryset = Mod.objects.all()
    serializer_class = ModSerializer
    permission_classes = [AllowAny]
class ModFileViewSet(viewsets.ModelViewSet):
    queryset = ModFile.objects.all()
    serializer_class = ModFileSerializer
    permission_classes = [AllowAny]
    def create(self, request, *args, **kwargs):
        mod_id = request.data.get('mod')
        files = request.FILES.getlist('file')
        if not mod_id or not files:
            return Response({'error': 'Mod ID and files are required.'}, status=status.HTTP_400_BAD_REQUEST)
        created_files = []
        for file in files:
            file_data = {'mod': mod_id, 'file': file}
            serializer = self.get_serializer(data=file_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            created_files.append(serializer.data)
        headers = self.get_success_headers(created_files[0])
        return Response(created_files, status=status.HTTP_201_CREATED, headers=headers)
class ProjectLinkViewSet(viewsets.ModelViewSet):
    queryset = ProjectLink.objects.all()
    serializer_class = ProjectLinkSerializer
    permission_classes = [AllowAny]
class ProjectFileViewSet(viewsets.ModelViewSet):
    queryset = ProjectFile.objects.all()
    serializer_class = ProjectFileSerializer
    permission_classes = [AllowAny]
    def create(self, request, *args, **kwargs):
        project_id = request.data.get('project')
        files = request.FILES.getlist('file')
        if not project_id or not files:
            return Response({'error': 'Project ID and files are required.'}, status=status.HTTP_400_BAD_REQUEST)
        created_files = []
        for file in files:
            file_data = {'project': project_id, 'file': file}
            serializer = self.get_serializer(data=file_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            created_files.append(serializer.data)
        headers = self.get_success_headers(created_files[0])
        return Response(created_files, status=status.HTTP_201_CREATED, headers=headers)
class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related('brand', 'part_type', 'location').prefetch_related('associated_projects').all().order_by('title')
    serializer_class = InventoryItemSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryItemFilter
    search_fields = ['title', 'brand__name', 'part_type__name', 'location__name', 'notes']
    ordering_fields = ['title', 'brand__name', 'part_type__name', 'location__name', 'quantity', 'cost']
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            print("--- SERIALIZER ERRORS ---")
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)
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