"""
Tests for InventoryItem model

InventoryItem is the core inventory management model with complex validation,
FK relationships, and low stock threshold logic.
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from inventory.models import InventoryItem, Brand, PartType, Location, Vendor


class InventoryItemModelTest(TestCase):
    """Test suite for InventoryItem model"""
    
    def setUp(self):
        """Create test data used across multiple tests"""
        self.brand = Brand.objects.create(name="Prusa")
        self.part_type = PartType.objects.create(name="Nozzle")
        self.location = Location.objects.create(name="Drawer A1")
        self.vendor = Vendor.objects.create(name="Amazon")
    
    def test_create_inventory_item_minimal(self):
        """Test creating an inventory item with only required field (title)"""
        item = InventoryItem.objects.create(title="0.4mm Brass Nozzle")
        
        self.assertEqual(item.title, "0.4mm Brass Nozzle")
        self.assertEqual(str(item), "0.4mm Brass Nozzle")
        self.assertEqual(item.quantity, 1)  # Default quantity is 1
        self.assertFalse(item.is_consumable)  # Default consumable flag
    
    def test_create_inventory_item_full(self):
        """Test creating an inventory item with all fields populated"""
        item = InventoryItem.objects.create(
            title="0.4mm Brass Nozzle",
            brand=self.brand,
            part_type=self.part_type,
            quantity=10,
            cost=Decimal("3.99"),
            location=self.location,
            notes="High quality nozzles",
            is_consumable=True,
            low_stock_threshold=5,
            vendor=self.vendor,
            vendor_link="https://amazon.com/nozzles",
            model="V6-NOZZLE-04"
        )
        
        self.assertEqual(item.title, "0.4mm Brass Nozzle")
        self.assertEqual(item.brand, self.brand)
        self.assertEqual(item.part_type, self.part_type)
        self.assertEqual(item.quantity, 10)
        self.assertEqual(item.cost, Decimal("3.99"))
        self.assertEqual(item.location, self.location)
        self.assertTrue(item.is_consumable)
        self.assertEqual(item.low_stock_threshold, 5)
    
    def test_inventory_item_title_required(self):
        """Test that title field is required"""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            InventoryItem.objects.create(title=None)
    
    def test_inventory_item_quantity_default(self):
        """Test that quantity defaults to 1"""
        item = InventoryItem.objects.create(title="Test Item")
        self.assertEqual(item.quantity, 1)
    
    def test_inventory_item_quantity_validation(self):
        """Test that quantity cannot be negative"""
        item = InventoryItem.objects.create(
            title="Test Item",
            quantity=-5  # This violates MinValueValidator(0)
        )
        
        # Validation happens during full_clean(), not during save()
        with self.assertRaises(ValidationError) as cm:
            item.full_clean()
        
        # Check that the error is for quantity field
        self.assertIn('quantity', cm.exception.error_dict)
    
    def test_inventory_item_quantity_zero_allowed(self):
        """Test that quantity of 0 is allowed"""
        item = InventoryItem.objects.create(title="Test Item", quantity=0, location=self.location)
        item.full_clean()  # Should not raise
        self.assertEqual(item.quantity, 0)
    
    def test_inventory_item_quantity_positive_allowed(self):
        """Test that positive quantities are allowed"""
        item = InventoryItem.objects.create(title="Test Item", quantity=100, location=self.location)
        item.full_clean()  # Should not raise
        self.assertEqual(item.quantity, 100)
    
    def test_inventory_item_is_consumable_default(self):
        """Test that is_consumable defaults to False"""
        item = InventoryItem.objects.create(title="Test Item")
        self.assertFalse(item.is_consumable)
    
    def test_inventory_item_is_consumable_flag(self):
        """Test setting is_consumable to True"""
        item = InventoryItem.objects.create(title="Filament", is_consumable=True)
        self.assertTrue(item.is_consumable)
    
    def test_inventory_item_low_stock_threshold_optional(self):
        """Test that low_stock_threshold is optional (can be null)"""
        item = InventoryItem.objects.create(title="Test Item")
        self.assertIsNone(item.low_stock_threshold)
    
    def test_inventory_item_low_stock_threshold_set(self):
        """Test setting low_stock_threshold value"""
        item = InventoryItem.objects.create(
            title="Test Item",
            low_stock_threshold=10
        )
        self.assertEqual(item.low_stock_threshold, 10)
    
    def test_inventory_item_brand_optional(self):
        """Test that brand is optional"""
        item = InventoryItem.objects.create(title="Generic Part")
        self.assertIsNone(item.brand)
    
    def test_inventory_item_brand_set_null_on_delete(self):
        """Test that deleting brand sets FK to null"""
        item = InventoryItem.objects.create(title="Test Item", brand=self.brand)
        self.assertEqual(item.brand, self.brand)
        
        self.brand.delete()
        item.refresh_from_db()
        self.assertIsNone(item.brand)
    
    def test_inventory_item_part_type_optional(self):
        """Test that part_type is optional"""
        item = InventoryItem.objects.create(title="Generic Part")
        self.assertIsNone(item.part_type)
    
    def test_inventory_item_part_type_set_null_on_delete(self):
        """Test that deleting part_type sets FK to null"""
        item = InventoryItem.objects.create(title="Test Item", part_type=self.part_type)
        self.assertEqual(item.part_type, self.part_type)
        
        self.part_type.delete()
        item.refresh_from_db()
        self.assertIsNone(item.part_type)
    
    def test_inventory_item_location_optional(self):
        """Test that location is optional"""
        item = InventoryItem.objects.create(title="Unlocated Item")
        self.assertIsNone(item.location)
    
    def test_inventory_item_location_set_null_on_delete(self):
        """Test that deleting location sets FK to null"""
        item = InventoryItem.objects.create(title="Test Item", location=self.location)
        self.assertEqual(item.location, self.location)
        
        self.location.delete()
        item.refresh_from_db()
        self.assertIsNone(item.location)
    
    def test_inventory_item_vendor_optional(self):
        """Test that vendor is optional"""
        item = InventoryItem.objects.create(title="Generic Part")
        self.assertIsNone(item.vendor)
    
    def test_inventory_item_vendor_set_null_on_delete(self):
        """Test that deleting vendor sets FK to null"""
        item = InventoryItem.objects.create(title="Test Item", vendor=self.vendor)
        self.assertEqual(item.vendor, self.vendor)
        
        self.vendor.delete()
        item.refresh_from_db()
        self.assertIsNone(item.vendor)
    
    def test_inventory_item_cost_optional(self):
        """Test that cost is optional"""
        item = InventoryItem.objects.create(title="Free Sample")
        self.assertIsNone(item.cost)
    
    def test_inventory_item_cost_decimal(self):
        """Test that cost stores decimal values correctly"""
        item = InventoryItem.objects.create(
            title="Expensive Part",
            cost=Decimal("99.99")
        )
        self.assertEqual(item.cost, Decimal("99.99"))
    
    def test_inventory_item_notes_optional(self):
        """Test that notes are optional"""
        item = InventoryItem.objects.create(title="Test Item")
        self.assertIsNone(item.notes)
    
    def test_inventory_item_photo_optional(self):
        """Test that photo is optional"""
        item = InventoryItem.objects.create(title="Test Item")
        self.assertFalse(item.photo)  # Should be empty/falsy
    
    def test_inventory_item_vendor_link_optional(self):
        """Test that vendor_link is optional"""
        item = InventoryItem.objects.create(title="Test Item")
        self.assertIsNone(item.vendor_link)
    
    def test_inventory_item_vendor_link_validates_url(self):
        """Test that vendor_link accepts valid URLs"""
        item = InventoryItem.objects.create(
            title="Test Item",
            vendor_link="https://example.com/product/123",
            location=self.location
        )
        item.full_clean()  # Should not raise
        self.assertEqual(item.vendor_link, "https://example.com/product/123")
    
    def test_inventory_item_model_optional(self):
        """Test that model number is optional"""
        item = InventoryItem.objects.create(title="Test Item")
        self.assertIsNone(item.model)
    
    def test_inventory_item_model_set(self):
        """Test setting model number"""
        item = InventoryItem.objects.create(
            title="Test Item",
            model="SKU-12345-XYZ"
        )
        self.assertEqual(item.model, "SKU-12345-XYZ")
    
    def test_inventory_item_ordering(self):
        """Test that items are ordered by title"""
        InventoryItem.objects.create(title="Zebra Item")
        InventoryItem.objects.create(title="Alpha Item")
        InventoryItem.objects.create(title="Micro Item")
        
        items = list(InventoryItem.objects.all())
        self.assertEqual(items[0].title, "Alpha Item")
        self.assertEqual(items[1].title, "Micro Item")
        self.assertEqual(items[2].title, "Zebra Item")
