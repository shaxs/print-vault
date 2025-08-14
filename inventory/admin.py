# printvault/inventory/admin.py
from django.contrib import admin
from .models import (
    Brand, PartType, Location, Printer,
    InventoryItem, Project, ProjectInventory, ProjectPrinters
)

# Register your models here so they appear in the Django admin site.
admin.site.register(Brand)
admin.site.register(PartType)
admin.site.register(Location)
admin.site.register(Printer)
admin.site.register(InventoryItem)
admin.site.register(Project)
admin.site.register(ProjectInventory)
admin.site.register(ProjectPrinters)