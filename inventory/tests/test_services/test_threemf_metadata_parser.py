"""
Tests for the shared 3MF embedded-metadata parser.

Uses synthetic in-test ZIP structures mimicking OrcaSlicer (JSON config) and
PrusaSlicer (INI config) 3MF layouts — no real slicer files needed.
"""
import json
import zipfile

from inventory.services.threemf_metadata_parser import parse_threemf_metadata

CORE_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
 {metadata}
 <resources></resources>
 <build></build>
</model>"""


def build_3mf(path, metadata_xml='', extra_members=None):
    """Write a minimal synthetic .3mf zip to `path`."""
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('3D/3dmodel.model', CORE_XML_TEMPLATE.format(metadata=metadata_xml))
        for member_name, content in (extra_members or {}).items():
            zf.writestr(member_name, content)
    return path


def test_orca_style_3mf(tmp_path):
    """OrcaSlicer layout: JSON project_settings.config + core XML metadata."""
    metadata_xml = (
        '<metadata name="Application">OrcaSlicer-2.1.1</metadata>'
        '<metadata name="Title">Benchy</metadata>'
    )
    config_json = json.dumps({
        "printer_settings_id": "Bambu Lab P1S 0.4 nozzle",
        "print_settings_id": "0.20mm Standard",
        "filament_settings_id": ["Generic PLA", "Generic PETG"],
        "filament_type": ["PLA", "PETG"],
        "filament_colour": ["#FFFFFF", "#000000"],
        "layer_height": "0.2",
        "nozzle_diameter": ["0.4"]
    })
    path = build_3mf(
        tmp_path / 'test.3mf',
        metadata_xml=metadata_xml,
        extra_members={'Metadata/project_settings.config': config_json}
    )

    result = parse_threemf_metadata(path)

    assert result['slicer_name'] == 'OrcaSlicer'
    assert result['slicer_version'] == '2.1.1'
    assert result['title'] == 'Benchy'
    assert result['printer_profile'] == 'Bambu Lab P1S 0.4 nozzle'
    assert result['print_profile'] == '0.20mm Standard'
    assert result['filaments'] == [
        {'name': 'Generic PLA', 'type': 'PLA', 'color': '#FFFFFF'},
        {'name': 'Generic PETG', 'type': 'PETG', 'color': '#000000'}
    ]
    assert result['layer_height'] == 0.2
    assert result['nozzle_diameter'] == 0.4


def test_prusa_style_3mf(tmp_path):
    """PrusaSlicer layout: ;-prefixed INI Slic3r_PE.config, multi-filament via ';'."""
    metadata_xml = '<metadata name="Application">PrusaSlicer-2.7.1+win64</metadata>'
    config_content = (
        "; printer_settings_id = Original Prusa MK4 0.4\n"
        "; print_settings_id = 0.20mm SPEED\n"
        "; filament_settings_id = Prusament PLA;Prusament PETG\n"
        "; filament_type = PLA;PETG\n"
        "; filament_colour = #FF0000;#00FF00\n"
        "; layer_height = 0.2\n"
        "; nozzle_diameter = 0.4,0.4\n"
    )
    path = build_3mf(
        tmp_path / 'test.3mf',
        metadata_xml=metadata_xml,
        extra_members={'Metadata/Slic3r_PE.config': config_content}
    )

    result = parse_threemf_metadata(path)

    assert result['slicer_name'] == 'PrusaSlicer'
    assert result['slicer_version'] == '2.7.1'  # +win64 build suffix stripped
    assert result['printer_profile'] == 'Original Prusa MK4 0.4'
    assert len(result['filaments']) == 2
    assert result['filaments'][0]['type'] == 'PLA'
    assert result['filaments'][0]['color'] == '#FF0000'
    assert result['filaments'][1]['type'] == 'PETG'
    assert result['filaments'][1]['color'] == '#00FF00'
    assert result['layer_height'] == 0.2
    # "0.4,0.4" is not a parseable float — key must be omitted, not garbled
    assert 'nozzle_diameter' not in result


def test_not_a_zip_returns_empty(tmp_path):
    """A non-ZIP file (e.g. an STL handed in by mistake) returns {}."""
    path = tmp_path / 'fake.3mf'
    path.write_bytes(b'solid ascii stl not a zip')

    assert parse_threemf_metadata(path) == {}


def test_missing_file_returns_empty(tmp_path):
    """A nonexistent path returns {} instead of raising."""
    assert parse_threemf_metadata(tmp_path / 'does_not_exist.3mf') == {}


def test_zip_without_known_members_returns_empty(tmp_path):
    """A valid ZIP with no recognized 3MF members returns {}."""
    path = tmp_path / 'test.3mf'
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('random.txt', 'content')

    assert parse_threemf_metadata(path) == {}


def test_broken_core_xml_still_returns_config_fields(tmp_path):
    """Unparseable core XML doesn't block the slicer config from being read."""
    path = tmp_path / 'test.3mf'
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('3D/3dmodel.model', '<model><unclosed')
        zf.writestr(
            'Metadata/project_settings.config',
            json.dumps({"printer_settings_id": "TestPrinter"})
        )

    result = parse_threemf_metadata(path)

    assert result['printer_profile'] == 'TestPrinter'
    assert 'slicer_name' not in result


def test_broken_json_config_still_returns_xml_fields(tmp_path):
    """Unparseable slicer config doesn't block core XML metadata."""
    metadata_xml = '<metadata name="Application">OrcaSlicer-2.1.1</metadata>'
    path = build_3mf(
        tmp_path / 'test.3mf',
        metadata_xml=metadata_xml,
        extra_members={'Metadata/project_settings.config': '{not json'}
    )

    result = parse_threemf_metadata(path)

    assert result['slicer_name'] == 'OrcaSlicer'
    assert 'printer_profile' not in result


def test_application_without_version(tmp_path):
    """An Application string with no version yields slicer_name only."""
    metadata_xml = '<metadata name="Application">SomeSlicer</metadata>'
    path = build_3mf(tmp_path / 'test.3mf', metadata_xml=metadata_xml)

    assert parse_threemf_metadata(path) == {'slicer_name': 'SomeSlicer'}


def test_empty_filament_entries_skipped(tmp_path):
    """All-empty filament values produce no filaments key at all."""
    config_json = json.dumps({"filament_type": ["", ""]})
    path = build_3mf(
        tmp_path / 'test.3mf',
        extra_members={'Metadata/project_settings.config': config_json}
    )

    assert 'filaments' not in parse_threemf_metadata(path)


def test_application_with_prerelease_version(tmp_path):
    """Hyphenated prerelease versions (real BambuStudio output) split correctly."""
    metadata_xml = '<metadata name="Application">BambuStudio-2.2.0-beta</metadata>'
    path = build_3mf(tmp_path / 'test.3mf', metadata_xml=metadata_xml)

    result = parse_threemf_metadata(path)

    assert result['slicer_name'] == 'BambuStudio'
    assert result['slicer_version'] == '2.2.0-beta'
