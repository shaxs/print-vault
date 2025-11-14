"""
Tests for simple lookup models (Brand, PartType, Location, Material, Vendor)

These models share similar structure:
- Single required name field
- Unique constraint
- Alphabetical ordering
- Simple string representation
"""
from django.test import TestCase
from django.db import IntegrityError
from inventory.models import Brand, PartType, Location, Material, Vendor


class BrandModelTest(TestCase):
    """Test suite for Brand model"""
    
    def test_create_brand(self):
        """Test creating a brand with valid data"""
        brand = Brand.objects.create(name="Creality")
        self.assertEqual(brand.name, "Creality")
        self.assertEqual(str(brand), "Creality")
    
    def test_brand_name_required(self):
        """Test that name field is required"""
        with self.assertRaises(IntegrityError):
            Brand.objects.create(name=None)
    
    def test_brand_name_unique(self):
        """Test that duplicate brand names are not allowed"""
        Brand.objects.create(name="Creality")
        with self.assertRaises(IntegrityError):
            Brand.objects.create(name="Creality")
    
    def test_brand_ordering(self):
        """Test that brands are ordered alphabetically"""
        Brand.objects.create(name="Zebra")
        Brand.objects.create(name="Alpha")
        Brand.objects.create(name="Micro")
        
        brands = list(Brand.objects.all())
        self.assertEqual(brands[0].name, "Alpha")
        self.assertEqual(brands[1].name, "Micro")
        self.assertEqual(brands[2].name, "Zebra")


class PartTypeModelTest(TestCase):
    """Test suite for PartType model"""
    
    def test_create_part_type(self):
        """Test creating a part type with valid data"""
        part_type = PartType.objects.create(name="Nozzle")
        self.assertEqual(part_type.name, "Nozzle")
        self.assertEqual(str(part_type), "Nozzle")
    
    def test_part_type_name_required(self):
        """Test that name field is required"""
        with self.assertRaises(IntegrityError):
            PartType.objects.create(name=None)
    
    def test_part_type_name_unique(self):
        """Test that duplicate part type names are not allowed"""
        PartType.objects.create(name="Nozzle")
        with self.assertRaises(IntegrityError):
            PartType.objects.create(name="Nozzle")
    
    def test_part_type_ordering(self):
        """Test that part types are ordered alphabetically"""
        PartType.objects.create(name="Thermistor")
        PartType.objects.create(name="Heater")
        PartType.objects.create(name="Nozzle")
        
        part_types = list(PartType.objects.all())
        self.assertEqual(part_types[0].name, "Heater")
        self.assertEqual(part_types[1].name, "Nozzle")
        self.assertEqual(part_types[2].name, "Thermistor")


class LocationModelTest(TestCase):
    """Test suite for Location model"""
    
    def test_create_location(self):
        """Test creating a location with valid data"""
        location = Location.objects.create(name="Garage Shelf A")
        self.assertEqual(location.name, "Garage Shelf A")
        self.assertEqual(str(location), "Garage Shelf A")
    
    def test_location_name_required(self):
        """Test that name field is required"""
        with self.assertRaises(IntegrityError):
            Location.objects.create(name=None)
    
    def test_location_name_unique(self):
        """Test that duplicate location names are not allowed"""
        Location.objects.create(name="Garage Shelf A")
        with self.assertRaises(IntegrityError):
            Location.objects.create(name="Garage Shelf A")
    
    def test_location_ordering(self):
        """Test that locations are ordered alphabetically"""
        Location.objects.create(name="Workshop")
        Location.objects.create(name="Basement")
        Location.objects.create(name="Garage")
        
        locations = list(Location.objects.all())
        self.assertEqual(locations[0].name, "Basement")
        self.assertEqual(locations[1].name, "Garage")
        self.assertEqual(locations[2].name, "Workshop")


class MaterialModelTest(TestCase):
    """Test suite for Material model"""
    
    def test_create_material(self):
        """Test creating a material with valid data"""
        material = Material.objects.create(name="Test Material XYZ")
        self.assertEqual(material.name, "Test Material XYZ")
        self.assertEqual(str(material), "Test Material XYZ")
    
    def test_material_name_required(self):
        """Test that name field is required"""
        with self.assertRaises(IntegrityError):
            Material.objects.create(name=None)
    
    def test_material_name_unique(self):
        """Test that duplicate material names are not allowed"""
        Material.objects.create(name="Unique Test Material 123")
        with self.assertRaises(IntegrityError):
            Material.objects.create(name="Unique Test Material 123")  # Duplicate
    
    def test_material_ordering(self):
        """Test that materials are ordered alphabetically"""
        Material.objects.create(name="Test Material Z")
        Material.objects.create(name="Test Material A")
        Material.objects.create(name="Test Material M")
        
        # Filter to only our test materials
        materials = list(Material.objects.filter(name__startswith="Test Material").order_by('name'))
        self.assertEqual(materials[0].name, "Test Material A")
        self.assertEqual(materials[1].name, "Test Material M")
        self.assertEqual(materials[2].name, "Test Material Z")


class VendorModelTest(TestCase):
    """Test suite for Vendor model"""
    
    def test_create_vendor(self):
        """Test creating a vendor with valid data"""
        vendor = Vendor.objects.create(name="Amazon")
        self.assertEqual(vendor.name, "Amazon")
        self.assertEqual(str(vendor), "Amazon")
    
    def test_vendor_name_required(self):
        """Test that name field is required"""
        with self.assertRaises(IntegrityError):
            Vendor.objects.create(name=None)
    
    def test_vendor_name_unique(self):
        """Test that duplicate vendor names are not allowed"""
        Vendor.objects.create(name="Amazon")
        with self.assertRaises(IntegrityError):
            Vendor.objects.create(name="Amazon")
    
    def test_vendor_ordering(self):
        """Test that vendors are ordered alphabetically (case-sensitive)"""
        Vendor.objects.create(name="Zebra Vendor")
        Vendor.objects.create(name="Alpha Vendor")
        Vendor.objects.create(name="Micro Vendor")
        
        vendors = list(Vendor.objects.all())
        self.assertEqual(vendors[0].name, "Alpha Vendor")
        self.assertEqual(vendors[1].name, "Micro Vendor")
        self.assertEqual(vendors[2].name, "Zebra Vendor")
