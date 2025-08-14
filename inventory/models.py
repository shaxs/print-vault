# printvault/inventory/models.py
import os
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.validators import MinValueValidator

class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True, null=False)
    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ['name']
    def __str__(self):
        return self.name

class PartType(models.Model):
    name = models.CharField(max_length=255, unique=True, null=False)
    class Meta:
        verbose_name = "Part Type"
        verbose_name_plural = "Part Types"
        ordering = ['name']
    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=255, unique=True, null=False)
    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ['name']
    def __str__(self):
        return self.name

class Printer(models.Model):
    title = models.CharField(max_length=255, null=False)
    manufacturer = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    serial_number = models.CharField(max_length=255, unique=True, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Active', choices=[
        ('Active', 'Active'),
        ('Under Repair', 'Under Repair'),
        ('Sold', 'Sold'),
        ('Archived', 'Archived'),
        ('Planned', 'Planned')
    ])
    notes = models.TextField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    build_size_x = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    build_size_y = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    build_size_z = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    photo = models.ImageField(upload_to='printer_photos/', null=True, blank=True)
    last_maintained_date = models.DateField(null=True, blank=True)
    maintenance_reminder_date = models.DateField(null=True, blank=True)
    last_carbon_replacement_date = models.DateField(null=True, blank=True)
    carbon_reminder_date = models.DateField(null=True, blank=True)
    maintenance_notes = models.TextField(null=True, blank=True)
    class Meta:
        verbose_name = "Printer"
        verbose_name_plural = "Printers"
        ordering = ['title']
    def __str__(self):
        return self.title

class Mod(models.Model):
    printer = models.ForeignKey(Printer, related_name='mods', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    link = models.URLField(max_length=512, null=True, blank=True)
    status = models.CharField(max_length=50, default='Planned', choices=[
        ('Planned', 'Planned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed')
    ])
    def __str__(self):
        return self.name

class ModFile(models.Model):
    mod = models.ForeignKey(Mod, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='mod_files/')
    def __str__(self):
        return os.path.basename(self.file.name)

@receiver(post_delete, sender=ModFile)
def submission_delete(sender, instance, **kwargs):
    instance.file.delete(False)

class InventoryItem(models.Model):
    title = models.CharField(max_length=255, null=False)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    part_type = models.ForeignKey(PartType, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    photo = models.ImageField(upload_to='inventory_photos/', null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ['title']
    def __str__(self):
        return self.title

class Project(models.Model):
    project_name = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Planning', choices=[('Planning', 'Planning'), ('In Progress', 'In Progress'), ('Completed', 'Completed'), ('Canceled', 'Canceled'), ('On Hold', 'On Hold')])
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to='project_photos/', null=True, blank=True)
    associated_inventory_items = models.ManyToManyField(InventoryItem, through='ProjectInventory', related_name='associated_projects')
    associated_printers = models.ManyToManyField(Printer, through='ProjectPrinters', related_name='associated_projects')
    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ['project_name']
    def __str__(self):
        return self.project_name

class ProjectLink(models.Model):
    project = models.ForeignKey(Project, related_name='links', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=512)
    def __str__(self):
        return self.name

class ProjectFile(models.Model):
    project = models.ForeignKey(Project, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='project_files/')
    def __str__(self):
        return os.path.basename(self.file.name)

@receiver(post_delete, sender=ProjectFile)
def delete_project_file_on_disk(sender, instance, **kwargs):
    instance.file.delete(False)

class ProjectInventory(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    class Meta:
        unique_together = ('project', 'inventory_item')
        verbose_name = "Project Inventory Link"
        verbose_name_plural = "Project Inventory Links"
    def __str__(self):
        return f"{self.project.project_name} - {self.inventory_item.title}"

class ProjectPrinters(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    printer = models.ForeignKey(Printer, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('project', 'printer')
        verbose_name = "Project Printer Link"
        verbose_name_plural = "Project Printer Links"
    def __str__(self):
        return f"{self.project.project_name} - {self.printer.title}"