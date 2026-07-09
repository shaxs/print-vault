# printvault/inventory/models.py
import os
from datetime import timedelta
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator

def get_project_upload_path(instance, filename):
    """Generates the upload path for a project file."""
    return os.path.join('project_files', str(instance.project.id), filename)

def get_mod_upload_path(instance, filename):
    """Generates the upload path for a mod file."""
    return os.path.join('mod_files', str(instance.mod.id), filename)

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


class MaterialFeature(models.Model):
    """
    Reusable features for Material blueprints (Matte, Glitter, High Speed, Carbon Filled, etc.)
    Once created, becomes available as an option across all filament blueprints.
    """
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Material Feature"
        verbose_name_plural = "Material Features"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Material(models.Model):
    """
    Unified model for both generic materials (PLA, PETG) and 
    specific filament blueprints (brand + material + specs).
    Generic materials are used for categorization, while blueprints
    represent specific products you can purchase and track.
    """
    
    # Core identification
    name = models.CharField(max_length=255, null=False)
    is_generic = models.BooleanField(
        default=True,
        help_text="True for generic types (PLA, PETG), False for specific products"
    )
    
    # Blueprint-specific fields (null for generics)
    brand = models.ForeignKey(
        'Brand',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Manufacturer (e.g., Sunlu, eSun)"
    )
    base_material = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_generic': True},
        related_name='blueprints',
        help_text="Generic material type (PLA, PETG, etc.)"
    )
    
    # Features (Matte, Glitter, High Speed, Carbon Filled, etc.)
    features = models.ManyToManyField(
        'MaterialFeature',
        blank=True,
        related_name='materials',
        help_text="Special features of this filament (e.g., Matte, High Speed, Carbon Filled)"
    )
    
    # Specifications
    diameter = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Filament diameter in mm (typically 1.75 or 2.85)"
    )
    spool_weight = models.IntegerField(
        null=True,
        blank=True,
        help_text="Typical spool weight in grams (e.g., 1000 for 1kg)"
    )
    empty_spool_weight = models.IntegerField(
        null=True,
        blank=True,
        help_text="Weight of the empty spool in grams (used for accurate remaining filament calculations)"
    )
    
    # Visual
    photo = models.ImageField(
        upload_to='filament_photos/',
        blank=True,
        null=True,
        help_text="Product photo, shown for all spools using this blueprint"
    )
    
    # Purchasing
    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    vendor_link = models.URLField(
        blank=True,
        help_text="Direct link to product page for reordering"
    )
    price_per_spool = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price in USD (or user's currency)"
    )
    
    # Favorites system
    is_favorite = models.BooleanField(
        default=False,
        help_text="Mark as favorite (max 5)"
    )
    favorite_order = models.IntegerField(
        null=True,
        blank=True,
        help_text="Display order in favorites list (1-5)"
    )
    
    # Color information (blueprint-specific, supports unlimited colors for gradients)
    colors = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of hex color codes: ['#1a1a1a', '#c0c0c0', ...]. Material name provides color identity."
    )
    color_family = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('red', 'Red'),
            ('orange', 'Orange'),
            ('yellow', 'Yellow'),
            ('green', 'Green'),
            ('blue', 'Blue'),
            ('purple', 'Purple'),
            ('pink', 'Pink'),
            ('brown', 'Brown'),
            ('black', 'Black'),
            ('white', 'White'),
            ('gray', 'Gray'),
            ('clear', 'Clear/Natural'),
            ('multi', 'Multi-Color'),
        ],
        help_text="Primary color family for filtering (helps with searching)"
    )
    
    # Print settings (Spoolman-compatible temperature ranges)
    nozzle_temp_min = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum recommended nozzle temperature (°C)"
    )
    nozzle_temp_max = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum recommended nozzle temperature (°C)"
    )
    bed_temp_min = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum recommended bed temperature (°C)"
    )
    bed_temp_max = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum recommended bed temperature (°C)"
    )
    
    # Material properties
    density = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Material density in g/cm³ (e.g., 1.24 for PLA) - used for volume calculations"
    )
    
    # Special properties
    tds_value = models.IntegerField(
        null=True,
        blank=True,
        help_text="Translucency (TDS) value for HueForge lithophanes"
    )
    low_stock_threshold = models.IntegerField(
        null=True,
        blank=True,
        help_text="Alert when total grams falls below this value"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        default='',
        help_text="User notes/comments about this material (printing tips, quirks, etc.)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materials"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_generic']),
            models.Index(fields=['is_favorite']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'brand'],
                condition=models.Q(is_generic=False),
                name='unique_material_brand_for_blueprints'
            ),
            models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_generic=True),
                name='unique_name_for_generic_materials'
            ),
        ]
    
    def __str__(self):
        if self.is_generic:
            return f"{self.name} (Generic)"
        if self.brand:
            return f"{self.brand.name} - {self.name}"
        return self.name
    
    def clean(self):
        """Validation rules"""
        from django.core.exceptions import ValidationError
        
        # Enforce max 5 favorites
        if self.is_favorite:
            existing_favorites = Material.objects.filter(
                is_favorite=True
            ).exclude(pk=self.pk).count()
            
            if existing_favorites >= 5:
                raise ValidationError("Cannot have more than 5 favorite filament types")
        
        # Blueprint-specific validation
        if not self.is_generic:
            if not self.brand:
                raise ValidationError("Blueprints must have a brand")
            if not self.base_material:
                raise ValidationError("Blueprints must link to a generic material")
    
    @property
    def total_available_grams(self):
        """
        Calculate total grams available across all active spools.
        Used for low stock alerts.
        """
        from django.db.models import Sum
        
        total = self.filamentspool_set.filter(
            status__in=['new', 'opened', 'in_use']
        ).aggregate(total=Sum('current_weight'))['total']
        
        return total or 0
    
    @property
    def is_low_stock(self):
        """Check if current inventory is below threshold"""
        if not self.low_stock_threshold:
            return False
        return self.total_available_grams <= self.low_stock_threshold
    
    @property
    def total_spool_count(self):
        """Count of all spools (including quantity field)"""
        from django.db.models import Sum
        
        total = self.filamentspool_set.filter(
            status__in=['new', 'opened', 'in_use']
        ).aggregate(total=Sum('quantity'))['total']
        
        return total or 0
    
    @property
    def total_inventory_value(self):
        """Calculate total value of inventory for this material"""
        if not self.price_per_spool or not self.spool_weight:
            return None
        
        cost_per_gram = self.price_per_spool / self.spool_weight
        return cost_per_gram * self.total_available_grams


class MaterialPhoto(models.Model):
    """
    Additional photos for a Material blueprint.
    Each Material can have unlimited additional photos beyond the main photo.
    Photos are saved immediately on upload (not batched with form submit).
    """
    material = models.ForeignKey(
        'Material',
        on_delete=models.CASCADE,
        related_name='additional_photos',
        help_text="The material blueprint this photo belongs to"
    )
    image = models.ImageField(
        upload_to='material_additional_photos/',
        help_text="Additional photo for the material"
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional caption for this photo"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers shown first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Material Photo'
        verbose_name_plural = 'Material Photos'

    def __str__(self):
        caption_text = self.caption or "No caption"
        return f"{self.material.name} - {caption_text}"


class FilamentSpool(models.Model):
    """
    Represents a physical filament spool or group of unopened spools.
    Tracks location, weight, and consumption.
    
    Supports two modes:
    1. Blueprint-based: filament_type links to a Material blueprint (standard workflow)
    2. Quick Add: filament_type is null, standalone fields store spool info (for one-offs)
    """
    
    STATUS_CHOICES = [
        ('new', 'New/Unopened'),
        ('opened', 'Opened'),
        ('in_use', 'In Use (On Printer)'),
        ('low', 'Low Stock'),
        ('empty', 'Empty'),
        ('archived', 'Archived'),
    ]
    
    # Link to blueprint (nullable for Quick Add spools)
    filament_type = models.ForeignKey(
        'Material',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'is_generic': False},
        help_text="Which filament blueprint (product) is this? Null for Quick Add spools."
    )
    
    # ============ Quick Add / Standalone Fields ============
    # These are used when filament_type is null (one-off spools without a blueprint)
    standalone_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Custom name for Quick Add spools (e.g., 'Convention Metallic Blue')"
    )
    standalone_brand = models.ForeignKey(
        'Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='standalone_spools',
        help_text="Brand for Quick Add spools (uses same brands as blueprints)"
    )
    standalone_material_type = models.ForeignKey(
        'Material',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='standalone_spools',
        limit_choices_to={'is_generic': True},
        help_text="Generic material type for Quick Add spools (PLA, PETG, etc.)"
    )
    standalone_colors = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of hex color codes for Quick Add spools: ['#1a1a1a', '#c0c0c0', ...]. Supports gradients/multi-color filaments."
    )
    standalone_color_family = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('red', 'Red'),
            ('orange', 'Orange'),
            ('yellow', 'Yellow'),
            ('green', 'Green'),
            ('blue', 'Blue'),
            ('purple', 'Purple'),
            ('pink', 'Pink'),
            ('brown', 'Brown'),
            ('black', 'Black'),
            ('white', 'White'),
            ('gray', 'Gray'),
            ('clear', 'Clear/Natural'),
            ('multi', 'Multi-Color'),
        ],
        help_text="Color family for filtering Quick Add spools"
    )
    standalone_photo = models.ImageField(
        upload_to='filament_photos/',
        blank=True,
        null=True,
        help_text="Photo for Quick Add spools"
    )
    # Print settings for Quick Add spools
    standalone_nozzle_temp_min = models.IntegerField(null=True, blank=True)
    standalone_nozzle_temp_max = models.IntegerField(null=True, blank=True)
    standalone_bed_temp_min = models.IntegerField(null=True, blank=True)
    standalone_bed_temp_max = models.IntegerField(null=True, blank=True)
    standalone_density = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    # ============ End Quick Add Fields ============
    
    # Quantity tracking for unopened spools
    quantity = models.IntegerField(
        default=1,
        help_text="Number of identical unopened spools (default: 1)"
    )
    is_opened = models.BooleanField(
        default=False,
        help_text="True if spool is opened/in use (locks quantity to 1)"
    )
    
    # Weight tracking (for opened spools)
    initial_weight = models.IntegerField(
        help_text="Starting weight in grams"
    )
    current_weight = models.IntegerField(
        help_text="Current weight in grams (updated as filament is used)"
    )
    
    # Location assignment
    location = models.ForeignKey(
        'Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Storage location (e.g., 'Storage Rack A')"
    )
    assigned_printer = models.ForeignKey(
        'Printer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Printer this spool is currently loaded on"
    )
    
    # Project assignment (optional)
    project = models.ForeignKey(
        'Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='filaments_used',
        help_text="Assign to specific project (optional)"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    
    # Date tracking
    date_added = models.DateTimeField(auto_now_add=True)
    date_opened = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When spool was first opened/used"
    )
    date_emptied = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When spool was marked empty"
    )
    date_archived = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When spool was archived"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="User notes about this spool"
    )
    
    # Price tracking (can override blueprint price for sales/deals)
    price_paid = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual price paid for this spool (overrides blueprint list price if set)"
    )
    
    # Future: NFC tag support
    nfc_tag_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="NFC tag identifier (optional)"
    )
    
    class Meta:
        verbose_name = "Filament Spool"
        verbose_name_plural = "Filament Spools"
        ordering = ['-date_added']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['assigned_printer']),
            models.Index(fields=['project']),
        ]
    
    def __str__(self):
        if self.is_quick_add:
            return f"{self.standalone_name or 'Quick Add Spool'} (Spool #{self.pk})"
        return f"{self.filament_type} (Spool #{self.pk})"
    
    @property
    def is_quick_add(self):
        """Returns True if this is a Quick Add spool (no blueprint attached)"""
        return self.filament_type is None
    
    @property
    def display_name(self):
        """Returns the display name for the spool"""
        if self.is_quick_add:
            return self.standalone_name or 'Quick Add Spool'
        return str(self.filament_type)
    
    def clean(self):
        """Validation rules"""
        from django.core.exceptions import ValidationError
        
        # Quick Add spools must have a name and material type
        if self.is_quick_add:
            if not self.standalone_name:
                raise ValidationError("Quick Add spools must have a name")
            if not self.standalone_material_type:
                raise ValidationError("Quick Add spools must have a material type")
        
        # If opened, quantity must be 1
        if self.is_opened and self.quantity > 1:
            raise ValidationError("Opened spools must have quantity = 1")
        
        # If unopened, current_weight should equal initial_weight
        if not self.is_opened and self.current_weight != self.initial_weight:
            self.current_weight = self.initial_weight
        
        # Can't assign to both storage location AND printer
        if self.location and self.assigned_printer:
            raise ValidationError("Spool can be in storage OR on printer, not both")
    
    @property
    def weight_remaining_percent(self):
        """Calculate percentage of filament remaining"""
        if self.initial_weight == 0:
            return 0
        return (self.current_weight / self.initial_weight) * 100
    
    @property
    def weight_used_grams(self):
        """Calculate how much filament has been consumed"""
        return self.initial_weight - self.current_weight
    
    @property
    def estimated_value(self):
        """Calculate current value based on remaining weight"""
        # Quick Add spools don't have price tracking
        if self.is_quick_add:
            return None
        if not self.filament_type.price_per_spool or not self.filament_type.spool_weight:
            return None
        
        cost_per_gram = self.filament_type.price_per_spool / self.filament_type.spool_weight
        return cost_per_gram * self.current_weight
    
    def mark_opened(self):
        """Mark spool as opened (called when assigned to printer or first use)"""
        from django.utils import timezone
        if not self.is_opened:
            self.is_opened = True
            self.date_opened = timezone.now()
            if self.status == 'new':
                self.status = 'opened'
            self.save()
    
    def mark_empty(self):
        """Mark spool as empty"""
        from django.utils import timezone
        self.status = 'empty'
        self.current_weight = 0
        self.date_emptied = timezone.now()
        # Clear printer assignment
        self.assigned_printer = None
        self.save()
    
    def archive(self):
        """Move spool to archived status"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.status != 'empty':
            raise ValidationError("Only empty spools can be archived")
        
        self.status = 'archived'
        self.date_archived = timezone.now()
        self.save()


class Vendor(models.Model):
    name = models.CharField(max_length=255, unique=True, null=False)
    class Meta:
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
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
    moonraker_url = models.URLField(blank=True, null=True)
    
    # Filament tracking fields
    primary_filament_custom = models.CharField(max_length=255, null=True, blank=True, help_text="Custom primary filament description")
    primary_filament_blueprint = models.ForeignKey('Material', on_delete=models.SET_NULL, null=True, blank=True, related_name='printers_using_as_primary', help_text="Material blueprint for primary filament")
    accent_filament_custom = models.CharField(max_length=255, null=True, blank=True, help_text="Custom accent filament description")
    accent_filament_blueprint = models.ForeignKey('Material', on_delete=models.SET_NULL, null=True, blank=True, related_name='printers_using_as_accent', help_text="Material blueprint for accent filament")
    additional_filaments = models.JSONField(default=list, blank=True, help_text="Additional filaments: [{'type': 'Top Hat', 'custom': 'Red PLA', 'blueprint_id': null}, ...]")
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
    file = models.FileField(upload_to=get_mod_upload_path)
    def __str__(self):
        return os.path.basename(self.file.name)

@receiver(post_delete, sender=ModFile)
def submission_delete(sender, instance, **kwargs):
    instance.file.delete(False)

class InventoryItem(models.Model):
    title = models.CharField(max_length=255, null=False)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    part_type = models.ForeignKey(PartType, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1)  # Can be negative when over-reserved by active project BOMs
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    photo = models.ImageField(upload_to='inventory_photos/', null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # --- New Fields for Consumables ---
    is_consumable = models.BooleanField(default=False)
    low_stock_threshold = models.IntegerField(null=True, blank=True)
    
    # --- Vendor and Model Fields ---
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    vendor_link = models.URLField(max_length=512, null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)

    # --- Ordering State ---
    is_ordered = models.BooleanField(
        default=False,
        help_text="True when a replacement/restock order has been placed but not yet received"
    )

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
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text='Project deadline/due date for tracking purposes'
    )
    notes = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to='project_photos/', null=True, blank=True)
    associated_inventory_items = models.ManyToManyField(InventoryItem, through='ProjectInventory', related_name='associated_projects')
    associated_printers = models.ManyToManyField(Printer, through='ProjectPrinters', related_name='associated_projects')
    materials = models.JSONField(
        default=list,
        blank=True,
        help_text='Array of material objects with label, custom_color, and blueprint_id fields'
    )
    
    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ['project_name']
    
    def __str__(self):
        return self.project_name
    
    @property
    def days_until_due(self):
        """Calculate days until due date (negative if overdue)."""
        if self.due_date:
            from datetime import date
            delta = self.due_date - date.today()
            return delta.days
        return None

class ProjectLink(models.Model):
    project = models.ForeignKey(Project, related_name='links', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=512)
    def __str__(self):
        return self.name

class ProjectFile(models.Model):
    project = models.ForeignKey(Project, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_project_upload_path)
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


# ============================================================================
# BILL OF MATERIALS MODELS
# ============================================================================

class ProjectBOMItem(models.Model):
    """
    A single line item in a project's Bill of Materials.
    Represents a hardware/purchased part needed for a project build.
    May be linked to an existing InventoryItem, marked as needs_purchase,
    or left unlinked until the user associates it with inventory.
    """
    STATUS_CHOICES = [
        ('linked', 'Linked'),
        ('unlinked', 'Unlinked'),
        ('needs_purchase', 'Needs Purchase'),
    ]

    project = models.ForeignKey(
        Project, related_name='bom_items', on_delete=models.CASCADE
    )
    description = models.CharField(
        max_length=255,
        help_text="Part description as written in the creator's BOM (e.g., 'M3x8 SHCS')"
    )
    quantity_needed = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Quantity required for this build"
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bom_items',
        help_text="Optional link to an existing inventory item"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unlinked',
        help_text="linked=associated to inventory / unlinked=not yet matched / needs_purchase=flag to buy"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Optional notes for this BOM item (e.g., variant notes from creator)"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the project BOM"
    )
    is_ordered = models.BooleanField(
        default=False,
        help_text="True when the item has been ordered but not yet received/linked to inventory"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project BOM Item"
        verbose_name_plural = "Project BOM Items"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.project.project_name} — {self.description}"


# ============================================================================
# PRINT TRACKER MODELS
# ============================================================================

def get_tracker_upload_path(instance, filename):
    """Generates the upload path for tracker files stored locally."""
    return os.path.join('tracker_files', str(instance.tracker.id), instance.directory_path, filename)


class Tracker(models.Model):
    """Print Tracker for managing multi-part 3D printing projects."""
    name = models.CharField(max_length=255, null=False)
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='trackers',
        help_text='Optional: Associate this tracker with a project'
    )
    
    # Filament tracking (NEW)
    primary_filament = models.ForeignKey(
        'FilamentSpool',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_prints',
        help_text="Primary filament used for this print"
    )
    secondary_filament = models.ForeignKey(
        'FilamentSpool',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='secondary_prints',
        help_text="Secondary filament (for multi-material prints)"
    )
    
    # Consumption tracking
    primary_filament_used_grams = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated or measured grams of primary filament used"
    )
    secondary_filament_used_grams = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated or measured grams of secondary filament used"
    )
    
    # Using TextField instead of URLField to avoid automatic URL encoding
    github_url = models.TextField(
        blank=True,
        default='',
        help_text='GitHub repository URL where files are located'
    )
    storage_type = models.CharField(
        max_length=10,
        choices=[
            ('link', 'Store GitHub Links'),
            ('local', 'Download and Store Locally')
        ],
        help_text='How to store the STL files'
    )
    creation_mode = models.CharField(
        max_length=10,
        choices=[
            ('github', 'GitHub Wizard'),
            ('manual', 'Manual Creation')
        ],
        default='github',
        help_text='How this tracker was created'
    )
    
    # Color configuration
    primary_color = models.CharField(
        max_length=7, 
        default='#1E40AF',
        blank=True,
        help_text='Hex color code for primary color (e.g., #1E40AF) - DEPRECATED: Use primary_material instead'
    )
    accent_color = models.CharField(
        max_length=7, 
        default='',
        blank=True,
        help_text='Hex color code for accent color (e.g., #DC2626) - DEPRECATED: Use accent_material instead'
    )
    
    # Material-based color configuration (NEW - replaces hex colors)
    primary_material = models.ForeignKey(
        'Material',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trackers_as_primary',
        help_text='Material blueprint for primary color files'
    )
    accent_material = models.ForeignKey(
        'Material',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trackers_as_accent',
        help_text='Material blueprint for accent color files'
    )
    
    # Timestamps
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    # Cached progress statistics (updated via signals)
    total_quantity = models.IntegerField(default=0, help_text='Total quantity of all parts')
    printed_quantity_total = models.IntegerField(default=0, help_text='Total quantity of printed parts')
    progress_percentage = models.IntegerField(default=0, help_text='Completion percentage (0-100)')
    
    # Dashboard display
    show_on_dashboard = models.BooleanField(
        default=False,
        help_text='Display this tracker in the dashboard featured section'
    )
    
    # File storage tracking
    storage_path = models.CharField(
        max_length=500,
        blank=True,
        help_text='Base storage path for this tracker\'s files'
    )
    total_storage_used = models.BigIntegerField(
        default=0,
        help_text='Total bytes used by all downloaded files'
    )
    files_downloaded = models.BooleanField(
        default=False,
        help_text='Whether all files have been successfully downloaded'
    )
    
    # Notes field
    notes = models.TextField(
        null=True,
        blank=True,
        help_text='Optional notes about this tracker'
    )

    # Auto-thumbnail generation settings
    generate_thumbnails_for_linked_files = models.BooleanField(
        default=False,
        help_text='Auto-generate thumbnails for GitHub-linked files by temporarily '
                   'downloading each one (no local copy is kept). Off by default '
                   'since it can be slow for large trackers.'
    )
    viewer_background = models.CharField(
        max_length=5,
        choices=[
            ('dark', 'Dark'),
            ('light', 'Light'),
        ],
        default='dark',
        help_text='Background color for the 3D model viewer for files in this tracker'
    )

    class Meta:
        verbose_name = "Print Tracker"
        verbose_name_plural = "Print Trackers"
        ordering = ['-created_date']
    
    def __str__(self):
        return self.name
    
    def recalculate_stats(self):
        """Recalculate and update cached statistics from files."""
        from django.db.models import Sum
        
        # Calculate totals
        quantity_result = self.files.aggregate(total=Sum('quantity'))
        printed_result = self.files.aggregate(total=Sum('printed_quantity'))
        
        self.total_quantity = quantity_result['total'] or 0
        self.printed_quantity_total = printed_result['total'] or 0
        
        # Calculate percentage
        if self.total_quantity == 0:
            self.progress_percentage = 0
        else:
            self.progress_percentage = round((self.printed_quantity_total / self.total_quantity) * 100)
    
    @property
    def total_count(self):
        """Total number of files in this tracker."""
        return self.files.count()
    
    @property
    def completed_count(self):
        """Number of files marked as completed."""
        return self.files.filter(status='completed').count()
    
    @property
    def in_progress_count(self):
        """Number of files currently in progress."""
        return self.files.filter(status='in_progress').count()
    
    @property
    def not_started_count(self):
        """Number of files not yet started."""
        return self.files.filter(status='not_started').count()
    
    @property
    def pending_quantity(self):
        """Quantity of parts not yet printed (total - printed)."""
        return self.total_quantity - self.printed_quantity_total
    
    @property
    def filament_cost(self):
        """Calculate total filament cost for this print"""
        cost = 0
        
        # Primary filament cost
        if self.primary_filament and self.primary_filament_used_grams:
            ft = self.primary_filament.filament_type
            if ft.price_per_spool and ft.spool_weight:
                cost_per_gram = ft.price_per_spool / ft.spool_weight
                cost += cost_per_gram * self.primary_filament_used_grams
        
        # Secondary filament cost
        if self.secondary_filament and self.secondary_filament_used_grams:
            ft = self.secondary_filament.filament_type
            if ft.price_per_spool and ft.spool_weight:
                cost_per_gram = ft.price_per_spool / ft.spool_weight
                cost += cost_per_gram * self.secondary_filament_used_grams
        
        return cost if cost > 0 else None


class TrackerFile(models.Model):
    """Individual file tracked within a Print Tracker."""
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    tracker = models.ForeignKey(
        Tracker, 
        on_delete=models.CASCADE, 
        related_name='files'
    )
    
    # Storage type - how this file is stored
    storage_type = models.CharField(
        max_length=10,
        choices=[
            ('link', 'Link Only'),
            ('local', 'Downloaded/Uploaded')
        ],
        default='link',
        help_text='Storage method: link (GitHub URL only) or local (file on server)'
    )
    
    # File identification
    filename = models.CharField(max_length=255, null=False)
    directory_path = models.CharField(
        max_length=500, 
        blank=True,
        help_text='Relative directory path (e.g., "Frame/extrusions")'
    )
    
    # GitHub reference (always stored)
    # Using TextField instead of URLField to avoid automatic URL encoding
    github_url = models.TextField(
        blank=True,
        default='',
        help_text='Direct URL to the file on GitHub'
    )
    
    # Local storage (only if tracker.storage_type == 'local')
    local_file = models.FileField(
        upload_to=get_tracker_upload_path, 
        max_length=500,  # Increased from default 100 to handle deep directory structures
        null=True, 
        blank=True,
        help_text='Local copy of the file (if downloaded)'
    )
    
    # File metadata
    file_size = models.BigIntegerField(
        default=0,
        help_text='File size in bytes'
    )
    sha = models.CharField(
        max_length=40, 
        blank=True,
        help_text='GitHub file SHA hash for verification'
    )
    
    # Print configuration
    color = models.CharField(
        max_length=50, 
        blank=True,
        help_text='Color name (e.g., Primary, Accent, Multicolor)'
    )
    material = models.CharField(
        max_length=50, 
        blank=True,
        help_text='Material name(s) for display (legacy field, use material_ids instead)'
    )
    material_ids = models.JSONField(
        default=list,
        blank=True,
        help_text='Array of Material IDs (e.g., [1, 5, 13] for multicolor)'
    )
    material_override = models.BooleanField(
        default=False,
        help_text='If True, this file has custom materials and won\'t be updated by tracker-level material changes'
    )
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Number of copies needed'
    )
    
    # Selection state (from wizard)
    is_selected = models.BooleanField(
        default=True,
        help_text='Whether this file is included in the tracker'
    )
    
    # Progress tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    printed_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of copies already printed'
    )
    
    # Timestamps
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    download_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='When the file was downloaded (if local storage)'
    )
    
    # Download tracking
    download_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('downloading', 'Downloading'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending',
        help_text='Current download status of this file'
    )
    download_error = models.TextField(
        blank=True,
        help_text='Error message if download failed'
    )
    downloaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When file was successfully downloaded'
    )
    file_checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text='SHA256 checksum of downloaded file for integrity verification'
    )
    actual_file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Actual size of downloaded file (may differ from estimate)'
    )
    
    class Meta:
        verbose_name = "Tracker File"
        verbose_name_plural = "Tracker Files"
        ordering = ['directory_path', 'filename']
        unique_together = ('tracker', 'directory_path', 'filename')
    
    def __str__(self):
        if self.directory_path:
            return f"{self.directory_path}/{self.filename}"
        return self.filename
    
    @property
    def remaining_quantity(self):
        """Calculate how many more copies need to be printed."""
        return max(0, self.quantity - self.printed_quantity)
    
    @property
    def is_complete(self):
        """Check if all required copies have been printed."""
        return self.printed_quantity >= self.quantity


# Clean up local file when TrackerFile is deleted
@receiver(post_delete, sender=TrackerFile)
def delete_tracker_file_on_disk(sender, instance, **kwargs):
    """Delete the local file from disk when TrackerFile is deleted."""
    if instance.local_file:
        instance.local_file.delete(False)


# Update tracker statistics when TrackerFile is saved or deleted
@receiver(post_save, sender=TrackerFile)
def update_tracker_stats_on_save(sender, instance, **kwargs):
    """Automatically update tracker cached statistics when a file is modified."""
    tracker = instance.tracker
    tracker.recalculate_stats()
    tracker.save(update_fields=['total_quantity', 'printed_quantity_total', 'progress_percentage', 'updated_date'])


@receiver(pre_save, sender=TrackerFile)
def clear_stale_auto_thumbnail_on_color_change(sender, instance, **kwargs):
    """
    A file's auto-generated thumbnail is rendered in its color/material at
    the time of generation. If color or material_ids changes afterward, that
    thumbnail is stale — delete it so the post_save signal below sees zero
    images and regenerates fresh, in the new color.

    Skips files with a manually-uploaded image (same "never touch a manual
    upload" convention as the regenerate-all action) — only the
    is_auto_generated image is ever deleted here.
    """
    if not instance.pk:
        return  # new file being created, nothing to compare against

    try:
        previous = TrackerFile.objects.get(pk=instance.pk)
    except TrackerFile.DoesNotExist:
        return

    if previous.color == instance.color and previous.material_ids == instance.material_ids:
        return

    if instance.images.filter(is_auto_generated=False).exists():
        return

    instance.images.filter(is_auto_generated=True).delete()


@receiver(post_save, sender=TrackerFile)
def queue_auto_thumbnail_generation(sender, instance, **kwargs):
    """
    Queue background thumbnail generation for STL/3MF tracker files.

    Fires on every save, not just creation, so a file that starts out as
    storage_type='link' and is later downloaded to 'local' becomes eligible
    at that point too. This is a cheap pre-filter only — the real guards
    (existing image, file type, storage type vs. tracker setting) live in
    generate_auto_thumbnail() itself, so calling it directly is always safe
    even if this signal's pre-filter is ever loosened.

    Deliberately queries TrackerFileImage.objects directly rather than
    instance.images.exists() -- TrackerFileViewSet's queryset uses
    prefetch_related('images'), and a bare .exists()/.all() on an instance
    with a populated prefetch cache reuses that cache instead of re-querying,
    even after the pre_save signal above just deleted a row moments earlier
    in the same request. Filtering first (as that signal does) resets
    Django's internal result cache and forces a fresh query; a bare
    .exists() does not. Bypassing instance.images here sidesteps the
    ambiguity entirely instead of relying on that subtlety.
    """
    if not instance.filename.lower().endswith(('.stl', '.3mf')):
        return
    if TrackerFileImage.objects.filter(tracker_file_id=instance.pk).exists():
        return
    if instance.storage_type == 'link' and not instance.tracker.generate_thumbnails_for_linked_files:
        return

    from django_q.tasks import async_task
    async_task('inventory.tasks.generate_auto_thumbnail_task', instance.id)


@receiver(pre_save, sender=Tracker)
def detect_manual_color_change(sender, instance, **kwargs):
    """
    Tracker.primary_color/accent_color (the "Manual Color" mode in Edit
    Tracker settings, as opposed to a Material Blueprint) feed
    _resolve_file_hex_color's rendering of every Primary/Accent file's
    auto-thumbnail directly -- but changing them never touches a single
    TrackerFile row, so TrackerFile's own color-change signal above never
    gets a chance to fire for this path.

    Deliberately does NOT fire when a color changes together with its paired
    material_id (primary_color + primary_material, or accent_color +
    accent_material) -- that combination is update_materials's own
    signature (it keeps primary_color in sync with the selected material
    "for backwards compatibility"), and that view already cascades to every
    affected file with its own .save() loop, which already triggers the
    TrackerFile-level signal above. Reacting here too would queue the same
    files a second time -- confirmed by an actual test failure during
    development (async_task called twice for one file) before this
    condition was added. Only a color change with its material_id
    unchanged is the real signature of a standalone Manual Color edit.

    Stashes which color categories changed on the instance for the
    post_save signal below to act on (pre_save is the only place with
    access to both the old DB row and the new in-memory values).
    """
    if not instance.pk:
        instance._manual_color_change = []
        return

    try:
        previous = Tracker.objects.get(pk=instance.pk)
    except Tracker.DoesNotExist:
        instance._manual_color_change = []
        return

    changed = []
    if previous.primary_color != instance.primary_color and previous.primary_material_id == instance.primary_material_id:
        changed.append('Primary')
    if previous.accent_color != instance.accent_color and previous.accent_material_id == instance.accent_material_id:
        changed.append('Accent')
    instance._manual_color_change = changed


@receiver(post_save, sender=Tracker)
def requeue_thumbnails_on_manual_color_change(sender, instance, created, **kwargs):
    """
    Companion to detect_manual_color_change above: for each color category
    that changed, clear and re-queue the auto-generated thumbnail (never a
    manual one) for every file in that category.

    Queries TrackerFileImage.objects directly rather than
    tracker_file.images -- same prefetch-cache reasoning as
    queue_auto_thumbnail_generation. instance.files.filter(color=...) is
    safe despite TrackerViewSet's prefetch_related('files__images'), since
    chaining .filter() (unlike a bare .exists()/.all()) always resets
    Django's result cache and forces a fresh query.
    """
    if created:
        return

    changed = getattr(instance, '_manual_color_change', [])
    if not changed:
        return

    from django_q.tasks import async_task

    for color in changed:
        for tracker_file in instance.files.filter(color=color):
            if not tracker_file.filename.lower().endswith(('.stl', '.3mf')):
                continue
            if TrackerFileImage.objects.filter(
                tracker_file_id=tracker_file.pk, is_auto_generated=False
            ).exists():
                continue  # manual image present -- never touch

            TrackerFileImage.objects.filter(
                tracker_file_id=tracker_file.pk, is_auto_generated=True
            ).delete()

            if tracker_file.storage_type == 'link' and not instance.generate_thumbnails_for_linked_files:
                continue

            async_task('inventory.tasks.generate_auto_thumbnail_task', tracker_file.id)


@receiver(post_delete, sender=TrackerFile)
def update_tracker_stats_on_delete(sender, instance, **kwargs):
    """Automatically update tracker cached statistics when a file is deleted."""
    tracker = instance.tracker
    tracker.recalculate_stats()
    tracker.save(update_fields=['total_quantity', 'printed_quantity_total', 'progress_percentage', 'updated_date'])


@receiver(post_save, sender=Printer)
def cleanup_printer_dismissals(sender, instance, **kwargs):
    """Clean up alert dismissals when printer state changes."""
    from datetime import date
    
    # Clean up printer_repair dismissals if printer is no longer under repair
    if instance.status != 'Under Repair':
        AlertDismissal.objects.filter(
            alert_type='printer_repair',
            alert_id=f'printer_repair_{instance.id}'
        ).delete()
    
    # Clean up maintenance_overdue dismissals if maintenance is no longer overdue
    if instance.maintenance_reminder_date is None or instance.maintenance_reminder_date >= date.today():
        AlertDismissal.objects.filter(
            alert_type='maintenance_overdue',
            alert_id=f'maintenance_overdue_{instance.id}'
        ).delete()
    
    # Clean up carbon_overdue dismissals if carbon filter is no longer overdue
    if instance.carbon_reminder_date is None or instance.carbon_reminder_date >= date.today():
        AlertDismissal.objects.filter(
            alert_type='carbon_overdue',
            alert_id=f'carbon_overdue_{instance.id}'
        ).delete()
    
    # Clean up carbon_soon dismissals if carbon filter is no longer due soon
    if instance.carbon_reminder_date is None or \
       instance.carbon_reminder_date < date.today() or \
       instance.carbon_reminder_date >= date.today() + timedelta(days=7):
        AlertDismissal.objects.filter(
            alert_type='carbon_soon',
            alert_id=f'carbon_soon_{instance.id}'
        ).delete()
    
    # Clean up project_blocked dismissals for any projects using this printer
    # If printer status changes to/from unavailable, re-check project_blocked alerts
    if instance.status in ['Under Repair', 'Sold', 'Archived', 'Active']:
        # Get all projects associated with this printer
        for project in instance.associated_projects.filter(status='In Progress'):
            # Check if project still has unavailable printers
            unavailable_printers = project.associated_printers.filter(
                status__in=['Under Repair', 'Sold', 'Archived']
            )
            # If no unavailable printers, delete the dismissal so alert can reappear
            if not unavailable_printers.exists():
                AlertDismissal.objects.filter(
                    alert_type='project_blocked',
                    alert_id=f'project_blocked_{project.id}'
                ).delete()


@receiver(post_save, sender=InventoryItem)
def cleanup_inventory_dismissals(sender, instance, **kwargs):
    """Clean up alert dismissals when inventory item state changes."""
    
    # Clean up low_stock dismissals if alert is disabled or item is no longer low stock
    if not instance.is_consumable or \
       instance.low_stock_threshold is None or \
       instance.quantity > instance.low_stock_threshold:
        AlertDismissal.objects.filter(
            alert_type='low_stock',
            alert_id=f'low_stock_{instance.id}'
        ).delete()


@receiver(post_save, sender=Project)
def cleanup_project_dismissals(sender, instance, **kwargs):
    """Clean up alert dismissals when project state changes."""
    from datetime import date
    
    # Clean up project_overdue dismissals if project is completed or due date is today or future
    if instance.status == 'Completed' or \
       instance.due_date is None or \
       instance.due_date >= date.today():
        AlertDismissal.objects.filter(
            alert_type='project_overdue',
            alert_id=f'project_overdue_{instance.id}'
        ).delete()
    
    # Clean up project_due_soon dismissals if project is completed or no longer due soon
    if instance.status == 'Completed' or \
       instance.due_date is None or \
       instance.due_date < date.today() or \
       instance.due_date >= date.today() + timedelta(days=7):
        AlertDismissal.objects.filter(
            alert_type='project_due_soon',
            alert_id=f'project_due_soon_{instance.id}'
        ).delete()
    
    # Clean up project_blocked dismissals if project is not in progress or no unavailable printers
    if instance.status != 'In Progress':
        AlertDismissal.objects.filter(
            alert_type='project_blocked',
            alert_id=f'project_blocked_{instance.id}'
        ).delete()
    else:
        # Check if all associated printers are available
        unavailable_printers = instance.associated_printers.filter(
            status__in=['Under Repair', 'Sold', 'Archived']
        )
        if not unavailable_printers.exists():
            AlertDismissal.objects.filter(
                alert_type='project_blocked',
                alert_id=f'project_blocked_{instance.id}'
            ).delete()


class TrackerFileImage(models.Model):
    """
    Images attached to a TrackerFile (screenshots, renders, stl-thumb output, etc.).
    Each TrackerFile can have multiple images. The first image (by order) is used
    as a thumbnail in the file list.
    """
    tracker_file = models.ForeignKey(
        'TrackerFile',
        on_delete=models.CASCADE,
        related_name='images',
        help_text="The tracker file this image belongs to"
    )
    image = models.ImageField(
        upload_to='tracker_file_images/',
        help_text="Image file"
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional caption for this image"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers shown first)"
    )
    is_auto_generated = models.BooleanField(
        default=False,
        help_text="True if this image was auto-generated from the STL/3MF geometry, "
                   "rather than manually uploaded. Auto-generated images are safe to "
                   "replace/regenerate; manually uploaded ones are never touched by "
                   "regeneration actions."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Tracker File Image'
        verbose_name_plural = 'Tracker File Images'

    def __str__(self):
        caption_text = self.caption or "No caption"
        return f"{self.tracker_file.filename} - {caption_text}"


class AlertDismissal(models.Model):
    """
    Track dismissed alerts (dashboard alerts, notifications, etc.).
    Used to prevent showing the same alert after user dismisses it.

    State-based invalidation: When the underlying state changes (e.g., printer
    status changes from 'Under Repair' to 'Active' and back), the dismissal
    becomes invalid and the alert will reappear.
    """
    alert_type = models.CharField(
        max_length=50,
        help_text='Type of alert (e.g., maintenance_overdue, low_stock, etc.)'
    )
    alert_id = models.CharField(
        max_length=100,
        help_text='Unique identifier for the specific alert instance'
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)
    state_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text='SHA256 hash of the state that caused this alert (for invalidation detection)'
    )
    
    class Meta:
        verbose_name = "Alert Dismissal"
        verbose_name_plural = "Alert Dismissals"
        unique_together = ['alert_type', 'alert_id']
        indexes = [
            models.Index(fields=['alert_type', 'alert_id']),
        ]
    
    def __str__(self):
        return f"{self.alert_type}: {self.alert_id}"


@receiver(post_delete, sender=TrackerFile)
def update_tracker_stats_on_delete(sender, instance, **kwargs):
    """Automatically update tracker cached statistics when a file is deleted."""
    tracker = instance.tracker
    tracker.recalculate_stats()
    tracker.save(update_fields=['total_quantity', 'printed_quantity_total', 'progress_percentage', 'updated_date'])

# =============================================================================
# STL/3MF Library — network-share file index
# (see chat_docs/planning/STL_LIBRARY_FEATURE_PLAN.md)
# =============================================================================

class LibraryRoot(models.Model):
    """
    An admin-configured directory (e.g. a bind-mounted network share) whose
    STL/3MF contents are indexed into a browsable library. Files are indexed
    in place — metadata plus a generated thumbnail — never copied into Print
    Vault's own storage. Multiple roots are supported; the API rejects only
    roots whose paths duplicate or overlap (nest inside/contain) another
    enabled root's path, since overlapping trees would double-index files.
    """
    name = models.CharField(max_length=255)
    path = models.CharField(
        max_length=1024,
        help_text="Absolute path as visible to this app (e.g. the bind-mount point inside the container)"
    )
    enabled = models.BooleanField(default=True)
    rescan_interval_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Periodic rescan interval in hours; NULL = manual rescans only"
    )
    thumbnail_color = models.CharField(
        max_length=7,
        default='#94a3b8',
        help_text="Hex color used for rendered thumbnails and the 3D viewer "
                  "(library files have no material context to derive one from)"
    )
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    last_scan_status = models.CharField(
        max_length=16,
        choices=[('idle', 'Idle'), ('running', 'Running'), ('success', 'Success'), ('error', 'Error')],
        default='idle',
    )
    last_scan_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Library Root"
        verbose_name_plural = "Library Roots"

    def __str__(self):
        return f"{self.name} ({self.path})"


class LibraryFolder(models.Model):
    """
    A first-class mirror of one real directory under a LibraryRoot.
    Explicit rows (rather than deriving the tree from file path strings) keep
    empty folders navigable and make breadcrumbs/contents indexed FK lookups.
    """
    root = models.ForeignKey(LibraryRoot, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='children',
        help_text="NULL for the root directory itself"
    )
    name = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=1024, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=[('active', 'Active'), ('deleted', 'Deleted')],
        default='active',
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Library Folder"
        verbose_name_plural = "Library Folders"
        unique_together = ('root', 'relative_path')

    def __str__(self):
        return f"{self.root.name}/{self.relative_path}" if self.relative_path else self.root.name


class LibraryFile(models.Model):
    """
    One indexed STL/3MF file on the share. Holds derived metadata only —
    the real bytes stay on the share and are streamed on demand.
    """
    # Denormalized alongside `folder` (which already implies the root) purely so
    # "all files under this root" queries don't need a join through folder.
    root = models.ForeignKey(LibraryRoot, on_delete=models.CASCADE, related_name='files')
    folder = models.ForeignKey(LibraryFolder, on_delete=models.CASCADE, related_name='files')
    filename = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=1024, db_index=True)
    extension = models.CharField(max_length=8)  # 'stl' or '3mf', lowercase, no dot
    size_bytes = models.PositiveBigIntegerField()
    modified_time = models.DateTimeField()
    sha256_hash = models.CharField(
        max_length=64, null=True, blank=True, db_index=True,
        help_text="NULL until first hash pass; NOT unique — legitimate duplicate files share a hash"
    )
    status = models.CharField(
        max_length=16,
        choices=[('active', 'Active'), ('deleted', 'Deleted')],
        default='active',
    )
    thumbnail = models.ImageField(upload_to='library_file_thumbnails/', null=True, blank=True)
    thumbnail_status = models.CharField(
        max_length=16,
        choices=[
            ('pending', 'Pending'),       # not yet processed
            ('rendered', 'Rendered'),     # thumbnail generated successfully
            ('too_large', 'Too large'),   # over the render size cap — skipped by design
            ('unrenderable', 'Unrenderable'),  # mesh could not be read (corrupt / empty geometry)
        ],
        default='pending',
        db_index=True,
        help_text="Why a file does or doesn't have a preview, so the UI can explain a missing thumbnail",
    )
    bounding_box_x = models.FloatField(null=True, blank=True)  # mm
    bounding_box_y = models.FloatField(null=True, blank=True)  # mm
    bounding_box_z = models.FloatField(null=True, blank=True)  # mm
    embedded_metadata = models.JSONField(
        default=dict, blank=True,
        help_text="Embedded 3MF slicer metadata; empty dict for .stl files"
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Library File"
        verbose_name_plural = "Library Files"
        unique_together = ('root', 'relative_path')

    def __str__(self):
        return self.relative_path


class LibraryScan(models.Model):
    """
    One scan job (full-root or scoped to a folder subtree). Backs the
    scan-status polling endpoint and doubles as the per-root concurrency
    guard: a new scan is refused while another scan of the same root is
    still pending/running.
    """
    root = models.ForeignKey(LibraryRoot, on_delete=models.CASCADE, related_name='scans')
    folder = models.ForeignKey(
        LibraryFolder, null=True, blank=True, on_delete=models.CASCADE, related_name='scans',
        help_text="Subtree scope for a scoped rescan; NULL = full-root scan"
    )
    kind = models.CharField(
        max_length=16,
        choices=[('scan', 'Scan'), ('thumbnails', 'Thumbnails')],
        default='scan',
        help_text="What this job does — a directory scan or a thumbnail regeneration; "
                  "lets a re-attached progress banner label the job correctly",
    )
    status = models.CharField(
        max_length=16,
        choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('error', 'Error')],
        default='pending',
    )
    error = models.TextField(blank=True)
    files_seen = models.PositiveIntegerField(default=0)
    files_queued = models.PositiveIntegerField(
        default=0, help_text="Files needing expensive processing (hash/render/parse)"
    )
    files_processed = models.PositiveIntegerField(default=0)
    # Per-scan result breakdown (walk-level), so the UI can show "what the last
    # scan found". A moved file counts as one new + one removed here (its old
    # path is swept and a fresh row appears at the new path); processing later
    # re-links it, but these walk counts are a fair filesystem-diff summary and
    # aren't retro-adjusted. Always 0 for kind='thumbnails' regeneration jobs.
    files_new = models.PositiveIntegerField(
        default=0, help_text="New files discovered by this scan"
    )
    files_updated = models.PositiveIntegerField(
        default=0, help_text="Changed files reprocessed (stat mismatch)"
    )
    files_deleted = models.PositiveIntegerField(
        default=0, help_text="Files soft-deleted by this scan's deletion sweep"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Library Scan"
        verbose_name_plural = "Library Scans"
        ordering = ['-created_at']

    def __str__(self):
        scope = self.folder.relative_path if self.folder_id else 'full root'
        return f"Scan of {self.root.name} ({scope}): {self.status}"


@receiver(post_delete, sender=LibraryFile)
def delete_library_file_thumbnail(sender, instance, **kwargs):
    """Remove the generated thumbnail from disk when its row is hard-deleted
    (same convention as ModFile/ProjectFile file cleanup)."""
    if instance.thumbnail:
        instance.thumbnail.delete(False)


@receiver(post_save, sender=LibraryRoot)
def sync_library_root_schedule(sender, instance, **kwargs):
    """Keep the per-root periodic-rescan Schedule in step with the root's
    settings on every save path (API edits, backup restore, admin)."""
    from inventory.library_tasks import sync_root_schedule
    sync_root_schedule(instance)


@receiver(post_delete, sender=LibraryRoot)
def delete_library_root_schedule(sender, instance, **kwargs):
    """Remove the periodic-rescan Schedule when its root goes away."""
    from inventory.library_tasks import delete_root_schedule
    delete_root_schedule(instance.pk)


class TrackerThumbnailJob(models.Model):
    """
    One tracker-scoped thumbnail (re)generation job. Mirrors LibraryScan:
    it backs the tracker page's progress banner ("N of M rendered") and
    doubles as the per-tracker concurrency guard — a new job is refused while
    another for the same tracker is still pending/running. The heavy rendering
    runs in time-budgeted Django-Q chunks (see services/tracker_thumbnail_jobs)
    so no single worker task can exceed the cluster timeout, however many files
    the tracker has.
    """
    tracker = models.ForeignKey(Tracker, on_delete=models.CASCADE, related_name='thumbnail_jobs')
    include_linked = models.BooleanField(
        default=False,
        help_text="Also (re)render storage_type='link' files for this run",
    )
    status = models.CharField(
        max_length=16,
        choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('error', 'Error')],
        default='pending',
    )
    error = models.TextField(blank=True)
    files_queued = models.PositiveIntegerField(
        default=0,
        help_text="Eligible files needing a render (excludes manual-image and non-STL/3MF files)",
    )
    files_processed = models.PositiveIntegerField(default=0)
    files_generated = models.PositiveIntegerField(
        default=0, help_text="Of the processed files, how many produced a thumbnail"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tracker Thumbnail Job"
        verbose_name_plural = "Tracker Thumbnail Jobs"
        ordering = ['-created_at']

    def __str__(self):
        return f"Thumbnail job for {self.tracker.name}: {self.status}"
