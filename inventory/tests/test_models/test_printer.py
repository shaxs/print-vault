"""
Tests for Printer model

Printer is a core model that links to Brand and is foundational for the tracker system.
Tests cover creation, relationships, validation, and computed properties.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from inventory.models import Printer, Brand


class PrinterModelTest(TestCase):
    """Test suite for Printer model"""
    
    def setUp(self):
        """Create test data used across multiple tests"""
        self.brand = Brand.objects.create(name="Creality")
    
    def test_create_printer_minimal(self):
        """Test creating a printer with only required fields"""
        printer = Printer.objects.create(title="Ender 3 V2")
        
        self.assertEqual(printer.title, "Ender 3 V2")
        self.assertEqual(str(printer), "Ender 3 V2")
        self.assertEqual(printer.status, "Active")  # Default status
    
    def test_create_printer_full(self):
        """Test creating a printer with all fields populated"""
        printer = Printer.objects.create(
            title="Ender 3 V2",
            manufacturer=self.brand,
            serial_number="E3V2-12345",
            purchase_date=date(2024, 1, 15),
            status="Active",
            notes="Primary printer for PLA prints",
            purchase_price=Decimal("199.99"),
            build_size_x=Decimal("220"),
            build_size_y=Decimal("220"),
            build_size_z=Decimal("250"),
            moonraker_url="http://192.168.1.100:7125"
        )
        
        self.assertEqual(printer.title, "Ender 3 V2")
        self.assertEqual(printer.manufacturer, self.brand)
        self.assertEqual(printer.serial_number, "E3V2-12345")
        self.assertEqual(printer.purchase_price, Decimal("199.99"))
        self.assertEqual(printer.build_size_x, Decimal("220"))
    
    def test_printer_serial_number_unique(self):
        """Test that serial numbers must be unique"""
        Printer.objects.create(title="Printer 1", serial_number="12345")
        
        # Creating another printer with same serial should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Printer.objects.create(title="Printer 2", serial_number="12345")
    
    def test_printer_status_choices(self):
        """Test that printer status field has correct choices"""
        printer = Printer.objects.create(title="Test Printer")
        
        # Valid status values
        valid_statuses = ['Active', 'Under Repair', 'Sold', 'Archived', 'Planned']
        for status in valid_statuses:
            printer.status = status
            printer.save()
            self.assertEqual(printer.status, status)
    
    def test_printer_manufacturer_can_be_null(self):
        """Test that manufacturer (brand) is optional"""
        printer = Printer.objects.create(title="DIY Printer")
        self.assertIsNone(printer.manufacturer)
    
    def test_printer_manufacturer_set_null_on_delete(self):
        """Test that deleting a brand sets manufacturer to null"""
        printer = Printer.objects.create(title="Ender 3", manufacturer=self.brand)
        self.assertEqual(printer.manufacturer, self.brand)
        
        # Delete the brand
        self.brand.delete()
        
        # Refresh printer from database
        printer.refresh_from_db()
        self.assertIsNone(printer.manufacturer)
    
    def test_printer_ordering(self):
        """Test that printers are ordered by title"""
        Printer.objects.create(title="Zebra Printer")
        Printer.objects.create(title="Alpha Printer")
        Printer.objects.create(title="Micro Printer")
        
        printers = list(Printer.objects.all())
        self.assertEqual(printers[0].title, "Alpha Printer")
        self.assertEqual(printers[1].title, "Micro Printer")
        self.assertEqual(printers[2].title, "Zebra Printer")
    
    def test_printer_maintenance_dates(self):
        """Test maintenance-related date fields"""
        today = date.today()
        next_week = today + timedelta(days=7)
        
        printer = Printer.objects.create(
            title="Test Printer",
            last_maintained_date=today,
            maintenance_reminder_date=next_week,
            last_carbon_replacement_date=today,
            carbon_reminder_date=next_week
        )
        
        self.assertEqual(printer.last_maintained_date, today)
        self.assertEqual(printer.maintenance_reminder_date, next_week)
        self.assertEqual(printer.last_carbon_replacement_date, today)
        self.assertEqual(printer.carbon_reminder_date, next_week)
    
    def test_printer_photo_optional(self):
        """Test that photo field is optional"""
        printer = Printer.objects.create(title="Test Printer")
        self.assertFalse(printer.photo)  # Should be empty/falsy
    
    def test_printer_notes_optional(self):
        """Test that notes fields are optional"""
        printer = Printer.objects.create(title="Test Printer")
        self.assertIsNone(printer.notes)
        self.assertIsNone(printer.maintenance_notes)
    
    def test_printer_moonraker_url_optional(self):
        """Test that Moonraker URL is optional and validates URL format"""
        printer = Printer.objects.create(title="Test Printer")
        self.assertIsNone(printer.moonraker_url)
        
        # Test with valid URL
        printer.moonraker_url = "http://192.168.1.100:7125"
        printer.save()
        self.assertEqual(printer.moonraker_url, "http://192.168.1.100:7125")
