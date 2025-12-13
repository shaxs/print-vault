"""
Factory Boy factories for creating test data.

Provides convenient factory classes for generating model instances
in tests without repetitive boilerplate code.
"""
import factory
from factory import fuzzy
from factory.django import DjangoModelFactory
from faker import Faker
from inventory.models import (
    Brand, PartType, Location, Material, MaterialFeature, Vendor, Printer, Mod, ModFile,
    InventoryItem, Project, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters,
    Tracker, TrackerFile, FilamentSpool
)

fake = Faker()


# ============================================================================
# LOOKUP MODEL FACTORIES
# ============================================================================

class BrandFactory(DjangoModelFactory):
    """Factory for Brand model."""
    class Meta:
        model = Brand
    
    name = factory.Sequence(lambda n: f"Brand {n}")


class PartTypeFactory(DjangoModelFactory):
    """Factory for PartType model."""
    class Meta:
        model = PartType
    
    name = factory.Sequence(lambda n: f"Part Type {n}")


class LocationFactory(DjangoModelFactory):
    """Factory for Location model."""
    class Meta:
        model = Location
    
    name = factory.Sequence(lambda n: f"Location {n}")


class MaterialFactory(DjangoModelFactory):
    """Factory for Material model."""
    class Meta:
        model = Material
    
    name = factory.Sequence(lambda n: f"Material {n}")


class VendorFactory(DjangoModelFactory):
    """Factory for Vendor model."""
    class Meta:
        model = Vendor
    
    name = factory.Sequence(lambda n: f"Vendor {n}")


class MaterialFeatureFactory(DjangoModelFactory):
    """Factory for MaterialFeature model."""
    class Meta:
        model = MaterialFeature
    
    name = factory.Sequence(lambda n: f"Feature {n}")


# ============================================================================
# PRINTER FACTORY (moved early for FilamentSpool dependencies)
# ============================================================================

class PrinterFactory(DjangoModelFactory):
    """Factory for Printer model."""
    class Meta:
        model = Printer
    
    title = factory.Sequence(lambda n: f"Printer {n}")
    manufacturer = factory.SubFactory(BrandFactory)
    serial_number = factory.Sequence(lambda n: f"SN-{n:06d}")
    purchase_date = factory.LazyAttribute(lambda _: fake.date_between(start_date='-2y', end_date='today'))
    status = fuzzy.FuzzyChoice(['operational', 'maintenance', 'retired'])
    notes = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    purchase_price = fuzzy.FuzzyDecimal(200.0, 5000.0, precision=2)


# ============================================================================
# FILAMENT SPOOL FACTORIES
# ============================================================================

class FilamentBlueprintMaterialFactory(DjangoModelFactory):
    """Factory for creating Material blueprints (non-generic materials for filament spools)."""
    class Meta:
        model = Material
    
    name = factory.Sequence(lambda n: f"Filament Blueprint {n}")
    is_generic = False
    brand = factory.SubFactory(BrandFactory)
    diameter = "1.75"
    spool_weight = 1000
    vendor = factory.SubFactory(VendorFactory)
    price_per_spool = fuzzy.FuzzyDecimal(15.0, 50.0, precision=2)
    
    @factory.lazy_attribute
    def base_material(self):
        """Create or get a generic PLA material as base."""
        from inventory.models import Material
        pla, _ = Material.objects.get_or_create(
            name='PLA',
            is_generic=True,
            defaults={'is_generic': True}
        )
        return pla


class GenericMaterialFactory(DjangoModelFactory):
    """Factory for creating generic material types (PLA, PETG, ABS, etc.)."""
    class Meta:
        model = Material
        django_get_or_create = ('name',)
    
    name = factory.Iterator(['PLA', 'PETG', 'ABS', 'ASA', 'TPU', 'Nylon'])
    is_generic = True


class FilamentSpoolFactory(DjangoModelFactory):
    """
    Factory for FilamentSpool model (Blueprint mode).
    
    Creates spools linked to a Material blueprint with proper filament type.
    """
    class Meta:
        model = FilamentSpool
    
    # Blueprint mode - linked to Material
    filament_type = factory.SubFactory(FilamentBlueprintMaterialFactory)
    
    # Quantity and opened state
    quantity = 1
    is_opened = False
    
    # Weight tracking
    initial_weight = fuzzy.FuzzyInteger(750, 1100)
    current_weight = factory.LazyAttribute(lambda obj: obj.initial_weight)
    
    # Location and assignments
    location = factory.SubFactory(LocationFactory)
    assigned_printer = None
    project = None
    
    # Status (default: new for unopened)
    status = 'new'
    
    # Optional fields
    notes = factory.LazyAttribute(lambda _: fake.sentence())
    price_paid = None
    nfc_tag_id = None
    
    class Params:
        """Factory traits for common spool configurations."""
        
        # Create an opened spool with some usage
        opened = factory.Trait(
            is_opened=True,
            quantity=1,
            status='opened',
            current_weight=factory.LazyAttribute(
                lambda obj: int(obj.initial_weight * 0.7)  # 70% remaining
            )
        )
        
        # Create a spool in use on a printer
        in_use = factory.Trait(
            is_opened=True,
            quantity=1,
            status='in_use',
            assigned_printer=factory.SubFactory(PrinterFactory),
            current_weight=factory.LazyAttribute(
                lambda obj: int(obj.initial_weight * 0.5)  # 50% remaining
            )
        )
        
        # Create a low stock spool
        low = factory.Trait(
            is_opened=True,
            quantity=1,
            status='low',
            current_weight=factory.LazyAttribute(
                lambda obj: int(obj.initial_weight * 0.15)  # 15% remaining
            )
        )
        
        # Create an empty spool
        empty = factory.Trait(
            is_opened=True,
            quantity=1,
            status='empty',
            current_weight=0
        )
        
        # Create a batch of unopened spools
        batch = factory.Trait(
            is_opened=False,
            quantity=fuzzy.FuzzyInteger(2, 5),
            status='new'
        )


class QuickAddSpoolFactory(DjangoModelFactory):
    """
    Factory for FilamentSpool model (Quick Add mode).
    
    Creates spools without a blueprint, using standalone fields instead.
    """
    class Meta:
        model = FilamentSpool
    
    # Quick Add mode - no blueprint
    filament_type = None
    
    # Standalone fields (Quick Add)
    standalone_name = factory.Sequence(lambda n: f"Quick Add Spool {n}")
    standalone_brand = factory.SubFactory(BrandFactory)
    standalone_colors = factory.LazyAttribute(
        lambda _: [fake.hex_color() for _ in range(fuzzy.FuzzyInteger(1, 3).fuzz())]
    )
    standalone_color_family = fuzzy.FuzzyChoice([
        'red', 'orange', 'yellow', 'green', 'blue', 'purple', 
        'pink', 'brown', 'black', 'white', 'gray', 'clear', 'multi'
    ])
    standalone_photo = None
    standalone_nozzle_temp_min = fuzzy.FuzzyInteger(190, 210)
    standalone_nozzle_temp_max = fuzzy.FuzzyInteger(220, 240)
    standalone_bed_temp_min = fuzzy.FuzzyInteger(50, 60)
    standalone_bed_temp_max = fuzzy.FuzzyInteger(65, 80)
    standalone_density = fuzzy.FuzzyDecimal(1.20, 1.30, precision=2)
    
    # Quantity and opened state
    quantity = 1
    is_opened = False
    
    # Weight tracking
    initial_weight = fuzzy.FuzzyInteger(750, 1100)
    current_weight = factory.LazyAttribute(lambda obj: obj.initial_weight)
    
    # Location and assignments
    location = factory.SubFactory(LocationFactory)
    assigned_printer = None
    project = None
    
    # Status
    status = 'new'
    
    # Optional fields
    notes = factory.LazyAttribute(lambda _: fake.sentence())
    price_paid = fuzzy.FuzzyDecimal(10.0, 40.0, precision=2)
    nfc_tag_id = None
    
    @factory.lazy_attribute
    def standalone_material_type(self):
        """Create or get a generic PLA material type."""
        from inventory.models import Material
        pla, _ = Material.objects.get_or_create(
            name='PLA',
            is_generic=True,
            defaults={'is_generic': True}
        )
        return pla


# ============================================================================
# INVENTORY ITEM FACTORY
# ============================================================================

class InventoryItemFactory(DjangoModelFactory):
    """Factory for InventoryItem model."""
    class Meta:
        model = InventoryItem
    
    title = factory.Sequence(lambda n: f"Inventory Item {n}")
    brand = factory.SubFactory(BrandFactory)
    part_type = factory.SubFactory(PartTypeFactory)
    location = factory.SubFactory(LocationFactory)
    quantity = fuzzy.FuzzyInteger(1, 100)
    cost = fuzzy.FuzzyDecimal(1.0, 500.0, precision=2)
    notes = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    is_consumable = False
    low_stock_threshold = None
    vendor = factory.SubFactory(VendorFactory)
    vendor_link = factory.LazyAttribute(lambda _: fake.url())
    model = factory.Sequence(lambda n: f"Model-{n}")


# ============================================================================
# PROJECT FACTORY
# ============================================================================

class ProjectFactory(DjangoModelFactory):
    """Factory for Project model."""
    class Meta:
        model = Project
    
    project_name = factory.Sequence(lambda n: f"Project {n}")
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=500))
    status = fuzzy.FuzzyChoice(['planning', 'active', 'on_hold', 'completed', 'cancelled'])
    start_date = factory.LazyAttribute(lambda _: fake.date_between(start_date='-1y', end_date='today'))
    due_date = factory.LazyAttribute(lambda _: fake.date_between(start_date='today', end_date='+1y'))
    notes = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=300))


class ProjectLinkFactory(DjangoModelFactory):
    """Factory for ProjectLink model."""
    class Meta:
        model = ProjectLink
    
    name = factory.Sequence(lambda n: f"Link {n}")
    url = factory.LazyAttribute(lambda _: fake.url())
    project = factory.SubFactory(ProjectFactory)


class ProjectFileFactory(DjangoModelFactory):
    """Factory for ProjectFile model."""
    class Meta:
        model = ProjectFile
    
    name = factory.Sequence(lambda n: f"File_{n}.stl")
    project = factory.SubFactory(ProjectFactory)


# ============================================================================
# TRACKER FACTORIES
# ============================================================================

class TrackerFactory(DjangoModelFactory):
    """Factory for Tracker model."""
    class Meta:
        model = Tracker
    
    name = factory.Sequence(lambda n: f"Tracker {n}")
    project = factory.SubFactory(ProjectFactory)
    github_url = factory.LazyAttribute(lambda _: f"https://github.com/user/repo/tree/main/stls")
    storage_type = fuzzy.FuzzyChoice(['link', 'local'])
    creation_mode = fuzzy.FuzzyChoice(['github', 'manual'])
    primary_color = "#1E40AF"
    accent_color = "#DC2626"
    show_on_dashboard = False
    total_quantity = 0
    printed_quantity_total = 0
    progress_percentage = 0
    total_storage_used = 0
    files_downloaded = False


class TrackerFileFactory(DjangoModelFactory):
    """Factory for TrackerFile model."""
    class Meta:
        model = TrackerFile
    
    tracker = factory.SubFactory(TrackerFactory)
    storage_type = fuzzy.FuzzyChoice(['link', 'local'])
    filename = factory.Sequence(lambda n: f"part_{n}.stl")
    directory_path = factory.LazyAttribute(lambda _: f"folder/{fake.word()}")
    github_url = factory.LazyAttribute(lambda _: f"https://github.com/user/repo/blob/main/stls/part.stl")
    file_size = fuzzy.FuzzyInteger(1024, 10485760)  # 1KB to 10MB
    sha = factory.LazyAttribute(lambda _: fake.sha1())
    color = fuzzy.FuzzyChoice(['Primary', 'Accent', 'Multicolor'])
    material = fuzzy.FuzzyChoice(['ABS', 'PLA', 'PETG', 'ASA'])
    quantity = fuzzy.FuzzyInteger(1, 10)
    is_selected = True
    status = fuzzy.FuzzyChoice(['not_started', 'in_progress', 'completed'])
    printed_quantity = 0


# ============================================================================
# MOD FACTORIES
# ============================================================================

class ModFactory(DjangoModelFactory):
    """Factory for Mod model."""
    class Meta:
        model = Mod
    
    printer = factory.SubFactory(PrinterFactory)
    name = factory.Sequence(lambda n: f"Mod {n}")
    link = factory.LazyAttribute(lambda _: fake.url())
    status = fuzzy.FuzzyChoice(['planning', 'in_progress', 'completed'])


class ModFileFactory(DjangoModelFactory):
    """Factory for ModFile model."""
    class Meta:
        model = ModFile
    
    mod = factory.SubFactory(ModFactory)
    name = factory.Sequence(lambda n: f"mod_file_{n}.stl")
