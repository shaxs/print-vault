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
    Brand, PartType, Location, Material, Vendor, Printer, Mod, ModFile,
    InventoryItem, Project, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters,
    Tracker, TrackerFile
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
# PRINTER FACTORY
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
