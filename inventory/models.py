# printvault/inventory/models.py
import os
from datetime import timedelta
from django.db import models
from django.db.models.signals import post_delete, post_save
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

class Material(models.Model):
    name = models.CharField(max_length=255, unique=True, null=False)
    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materials"
        ordering = ['name']
    def __str__(self):
        return self.name

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
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(0)])
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
        help_text='Hex color code for primary color (e.g., #1E40AF)'
    )
    accent_color = models.CharField(
        max_length=7, 
        default='#DC2626',
        help_text='Hex color code for accent color (e.g., #DC2626)'
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
        help_text='Material type (e.g., ABS, PLA, PETG)'
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