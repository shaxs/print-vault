# printvault/inventory/filters.py
from django_filters import rest_framework as filters
from .models import InventoryItem, Printer, Project, Material

class MaterialFilter(filters.FilterSet):
    class Meta:
        model = Material
        fields = {
            'brand': ['exact'],
            'base_material': ['exact'],
            'color_family': ['exact'],
        }

class InventoryItemFilter(filters.FilterSet):
    class Meta:
        model = InventoryItem
        fields = {
            'brand__name': ['exact', 'icontains'],
            'part_type__name': ['exact', 'icontains'],
            'location__name': ['exact', 'icontains'],
        }

class PrinterFilter(filters.FilterSet):
    class Meta:
        model = Printer
        fields = {
            'manufacturer__name': ['exact', 'icontains'],
            'status': ['exact'],
        }

class ProjectFilter(filters.FilterSet):
    class Meta:
        model = Project
        fields = {
            'status': ['exact'],
        }