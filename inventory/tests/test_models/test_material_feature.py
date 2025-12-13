"""
Tests for MaterialFeature model and Material.features ManyToMany relationship.

MaterialFeature provides tagging capabilities for Material blueprints,
allowing users to categorize materials by characteristics like "Matte",
"Silk", "High Speed", "UV Resistant", etc.
"""
from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from inventory.models import MaterialFeature, Material, Brand


class MaterialFeatureModelTest(TestCase):
    """Test suite for MaterialFeature model."""
    
    def test_create_feature(self):
        """Test creating a feature with valid data."""
        feature = MaterialFeature.objects.create(name="Matte")
        self.assertEqual(feature.name, "Matte")
        self.assertEqual(str(feature), "Matte")
        self.assertIsNotNone(feature.created_at)
    
    def test_feature_name_required(self):
        """Test that name field is required."""
        with self.assertRaises(IntegrityError):
            MaterialFeature.objects.create(name=None)
    
    def test_feature_name_unique(self):
        """Test that duplicate feature names are not allowed."""
        MaterialFeature.objects.create(name="Silk Finish")
        with self.assertRaises(IntegrityError):
            MaterialFeature.objects.create(name="Silk Finish")
    
    def test_feature_name_max_length(self):
        """Test that name field has a max length of 100 characters."""
        # 100 characters should work
        long_name = "A" * 100
        feature = MaterialFeature.objects.create(name=long_name)
        self.assertEqual(len(feature.name), 100)
    
    def test_feature_ordering(self):
        """Test that features are ordered alphabetically by name."""
        MaterialFeature.objects.create(name="UV Resistant")
        MaterialFeature.objects.create(name="High Speed")
        MaterialFeature.objects.create(name="Matte")
        
        features = list(MaterialFeature.objects.all())
        self.assertEqual(features[0].name, "High Speed")
        self.assertEqual(features[1].name, "Matte")
        self.assertEqual(features[2].name, "UV Resistant")
    
    def test_created_at_auto_now_add(self):
        """Test that created_at is automatically set on creation."""
        before = timezone.now()
        feature = MaterialFeature.objects.create(name="Glow in Dark")
        after = timezone.now()
        
        self.assertGreaterEqual(feature.created_at, before - timedelta(seconds=1))
        self.assertLessEqual(feature.created_at, after + timedelta(seconds=1))


class MaterialFeaturesRelationshipTest(TestCase):
    """Test suite for Material.features ManyToMany relationship."""
    
    def setUp(self):
        """Create test data for relationship tests."""
        self.brand = Brand.objects.create(name="Test Brand")
        self.feature_matte = MaterialFeature.objects.create(name="Matte")
        self.feature_silk = MaterialFeature.objects.create(name="Silk")
        self.feature_highspeed = MaterialFeature.objects.create(name="High Speed")
    
    def test_material_can_have_no_features(self):
        """Test that a material can exist without any features."""
        material = Material.objects.create(
            name="Basic PLA",
            is_generic=False,
            brand=self.brand
        )
        self.assertEqual(material.features.count(), 0)
    
    def test_material_can_have_single_feature(self):
        """Test that a material can have one feature."""
        material = Material.objects.create(
            name="Matte PLA",
            is_generic=False,
            brand=self.brand
        )
        material.features.add(self.feature_matte)
        
        self.assertEqual(material.features.count(), 1)
        self.assertIn(self.feature_matte, material.features.all())
    
    def test_material_can_have_multiple_features(self):
        """Test that a material can have multiple features."""
        material = Material.objects.create(
            name="Matte High Speed PLA",
            is_generic=False,
            brand=self.brand
        )
        material.features.add(self.feature_matte, self.feature_highspeed)
        
        self.assertEqual(material.features.count(), 2)
        self.assertIn(self.feature_matte, material.features.all())
        self.assertIn(self.feature_highspeed, material.features.all())
    
    def test_feature_can_be_used_by_multiple_materials(self):
        """Test that the same feature can be assigned to multiple materials."""
        material1 = Material.objects.create(
            name="Brand A Matte PLA",
            is_generic=False,
            brand=self.brand
        )
        material2 = Material.objects.create(
            name="Brand B Matte PLA",
            is_generic=False,
            brand=self.brand
        )
        
        material1.features.add(self.feature_matte)
        material2.features.add(self.feature_matte)
        
        # Check both materials have the feature
        self.assertIn(self.feature_matte, material1.features.all())
        self.assertIn(self.feature_matte, material2.features.all())
        
        # Check reverse relation works
        materials_with_matte = self.feature_matte.materials.all()
        self.assertEqual(materials_with_matte.count(), 2)
        self.assertIn(material1, materials_with_matte)
        self.assertIn(material2, materials_with_matte)
    
    def test_remove_feature_from_material(self):
        """Test removing a feature from a material."""
        material = Material.objects.create(
            name="Test Material",
            is_generic=False,
            brand=self.brand
        )
        material.features.add(self.feature_matte, self.feature_silk)
        self.assertEqual(material.features.count(), 2)
        
        # Remove one feature
        material.features.remove(self.feature_silk)
        
        self.assertEqual(material.features.count(), 1)
        self.assertIn(self.feature_matte, material.features.all())
        self.assertNotIn(self.feature_silk, material.features.all())
    
    def test_clear_all_features(self):
        """Test clearing all features from a material."""
        material = Material.objects.create(
            name="Test Material",
            is_generic=False,
            brand=self.brand
        )
        material.features.add(self.feature_matte, self.feature_silk, self.feature_highspeed)
        self.assertEqual(material.features.count(), 3)
        
        material.features.clear()
        
        self.assertEqual(material.features.count(), 0)
    
    def test_set_features_replaces_existing(self):
        """Test that setting features replaces all existing features."""
        material = Material.objects.create(
            name="Test Material",
            is_generic=False,
            brand=self.brand
        )
        material.features.add(self.feature_matte, self.feature_silk)
        self.assertEqual(material.features.count(), 2)
        
        # Set to only highspeed
        material.features.set([self.feature_highspeed])
        
        self.assertEqual(material.features.count(), 1)
        self.assertIn(self.feature_highspeed, material.features.all())
        self.assertNotIn(self.feature_matte, material.features.all())
    
    def test_delete_feature_removes_from_materials(self):
        """Test that deleting a feature removes it from all materials."""
        material1 = Material.objects.create(
            name="Material 1",
            is_generic=False,
            brand=self.brand
        )
        material2 = Material.objects.create(
            name="Material 2",
            is_generic=False,
            brand=self.brand
        )
        
        material1.features.add(self.feature_matte, self.feature_silk)
        material2.features.add(self.feature_matte)
        
        # Delete the Matte feature
        self.feature_matte.delete()
        
        # Refresh from database
        material1.refresh_from_db()
        material2.refresh_from_db()
        
        # Matte should be removed from both materials
        self.assertEqual(material1.features.count(), 1)
        self.assertIn(self.feature_silk, material1.features.all())
        self.assertEqual(material2.features.count(), 0)
    
    def test_features_ordered_alphabetically(self):
        """Test that features for a material are ordered alphabetically."""
        material = Material.objects.create(
            name="Multi-Feature Material",
            is_generic=False,
            brand=self.brand
        )
        # Add features in non-alphabetical order
        material.features.add(self.feature_silk)
        material.features.add(self.feature_highspeed)
        material.features.add(self.feature_matte)
        
        features = list(material.features.all())
        self.assertEqual(features[0].name, "High Speed")
        self.assertEqual(features[1].name, "Matte")
        self.assertEqual(features[2].name, "Silk")
