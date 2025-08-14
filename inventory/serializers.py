# printvault/inventory/serializers.py
import json
from rest_framework import serializers
from .models import (
    Brand, PartType, Location, Printer, Mod, ModFile,
    InventoryItem, Project, ProjectLink, ProjectFile, ProjectInventory, ProjectPrinters
)

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']

class PartTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartType
        fields = ['id', 'name']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name']
        
class ModFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModFile
        fields = '__all__'

class ModSerializer(serializers.ModelSerializer):
    files = ModFileSerializer(many=True, read_only=True)
    class Meta:
        model = Mod
        fields = ['id', 'printer', 'name', 'link', 'status', 'files']

class ProjectLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLink
        fields = '__all__'

class ProjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = '__all__'

class SimpleProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'project_name']

def get_or_create_nested(model_class, data):
    if not data: return None
    if isinstance(data, str):
        try: data = json.loads(data)
        except (json.JSONDecodeError, TypeError): return None
    if isinstance(data, dict) and 'name' in data and data['name']:
        instance, _ = model_class.objects.get_or_create(name=data['name'])
        return instance
    return None

class InventoryItemSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    part_type = PartTypeSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    associated_projects = SimpleProjectSerializer(many=True, read_only=True)
    project_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Project.objects.all(), source='associated_projects', write_only=True, required=False
    )
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'title', 'brand', 'part_type', 'quantity', 
            'cost', 'location', 'photo', 'notes',
            'associated_projects', 'project_ids'
        ]

    def create(self, validated_data):
        projects = validated_data.pop('associated_projects', None)
        request_data = self.context['request'].data
        validated_data['brand'] = get_or_create_nested(Brand, request_data.get('brand'))
        validated_data['part_type'] = get_or_create_nested(PartType, request_data.get('part_type'))
        validated_data['location'] = get_or_create_nested(Location, request_data.get('location'))
        instance = InventoryItem.objects.create(**validated_data)
        if projects:
            instance.associated_projects.set(projects)
        return instance

    def update(self, instance, validated_data):
        projects = validated_data.pop('associated_projects', None)
        request_data = self.context['request'].data
        if 'brand' in request_data:
            instance.brand = get_or_create_nested(Brand, request_data.get('brand'))
        if 'part_type' in request_data:
            instance.part_type = get_or_create_nested(PartType, request_data.get('part_type'))
        if 'location' in request_data:
            instance.location = get_or_create_nested(Location, request_data.get('location'))
        instance = super().update(instance, validated_data)
        if projects is not None:
            instance.associated_projects.set(projects)
        return instance

class PrinterSerializer(serializers.ModelSerializer):
    manufacturer = BrandSerializer(read_only=True)
    mods = ModSerializer(many=True, read_only=True)
    associated_projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = Printer
        fields = '__all__'

    def create(self, validated_data):
        request_data = self.context['request'].data
        validated_data['manufacturer'] = get_or_create_nested(Brand, request_data.get('manufacturer'))
        return Printer.objects.create(**validated_data)

    def update(self, instance, validated_data):
        request_data = self.context['request'].data
        if 'manufacturer' in request_data:
            instance.manufacturer = get_or_create_nested(Brand, request_data.get('manufacturer'))
        return super().update(instance, validated_data)

class ProjectSerializer(serializers.ModelSerializer):
    associated_inventory_items = InventoryItemSerializer(many=True, read_only=True)
    associated_printers = PrinterSerializer(many=True, read_only=True)
    total_cost = serializers.SerializerMethodField()
    links = ProjectLinkSerializer(many=True, read_only=True)
    files = ProjectFileSerializer(many=True, read_only=True)

    inventory_item_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=InventoryItem.objects.all(), source='associated_inventory_items', write_only=True, required=False)
    printer_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Printer.objects.all(), source='associated_printers', write_only=True, required=False)
    
    class Meta:
        model = Project
        fields = [
            'id', 'project_name', 'description', 'status', 'start_date', 'end_date',
            'notes', 'photo', 'associated_inventory_items', 'associated_printers', 
            'total_cost', 'inventory_item_ids', 'printer_ids', 'links', 'files'
        ]
    
    def get_total_cost(self, obj):
        total = sum(item.cost for item in obj.associated_inventory_items.all() if item.cost)
        return total

    def create(self, validated_data):
        inventory_items = validated_data.pop('associated_inventory_items', None)
        printers = validated_data.pop('associated_printers', None)
        project = Project.objects.create(**validated_data)
        if inventory_items: project.associated_inventory_items.set(inventory_items)
        if printers: project.associated_printers.set(printers)
        return project

    def update(self, instance, validated_data):
        inventory_items = validated_data.pop('associated_inventory_items', None)
        printers = validated_data.pop('associated_printers', None)
        instance = super().update(instance, validated_data)
        if inventory_items is not None: instance.associated_inventory_items.set(inventory_items)
        if printers is not None: instance.associated_printers.set(printers)
        return instance

class ProjectInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInventory
        fields = '__all__'

class ProjectPrintersSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPrinters
        fields = '__all__'