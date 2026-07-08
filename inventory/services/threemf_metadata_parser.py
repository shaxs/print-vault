"""
Generic 3MF embedded-metadata parser.

A .3mf file is a ZIP archive: core model metadata lives in XML
(``3D/3dmodel.model``), and slicers embed their own config alongside it —
PrusaSlicer as an INI-style ``Metadata/Slic3r_PE.config``, OrcaSlicer and
Bambu Studio as JSON ``Metadata/project_settings.config``.

Shared between the STL/3MF Library feature and the future Slicer Config
feature (see SLICER_CONFIG_FEATURE_PLAN.md) — keep this module free of any
model/ORM coupling so both can call it with just a file path.

Output is a small curated dict, not a dump of the slicer's full config
(Orca project settings run to hundreds of keys — the callers store this in a
per-file JSONField, so only the fields the UI actually shows are kept):

    {
        'slicer_name': 'OrcaSlicer',
        'slicer_version': '2.1.1',
        'printer_profile': 'Bambu Lab P1S 0.4 nozzle',
        'print_profile': '0.20mm Standard @BBL P1P',
        'filaments': [{'name': ..., 'type': 'PLA', 'color': '#FFFFFF'}, ...],
        'layer_height': 0.2,
        'nozzle_diameter': 0.4,
        'title': 'Benchy',
        'designer': '...',
    }

Absent/unparseable values are simply omitted. parse_threemf_metadata() never
raises — a malformed file returns whatever subset could be read (possibly {}).
"""

import json
import logging
import re
import zipfile
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# <metadata name="..."> keys from the core 3D/3dmodel.model worth keeping,
# mapped to our output keys.
_CORE_METADATA_KEYS = {
    'Title': 'title',
    'Designer': 'designer',
    'Description': 'description',
    'CreationDate': 'creation_date',
}

# Config keys (identical names in PrusaSlicer INI and Orca/Bambu JSON).
_PRINTER_PROFILE_KEY = 'printer_settings_id'
_PRINT_PROFILE_KEY = 'print_settings_id'
_FILAMENT_NAME_KEY = 'filament_settings_id'
_FILAMENT_TYPE_KEY = 'filament_type'
_FILAMENT_COLOR_KEY = 'filament_colour'
_LAYER_HEIGHT_KEY = 'layer_height'
_NOZZLE_DIAMETER_KEY = 'nozzle_diameter'


def parse_threemf_metadata(file_path) -> dict:
    """
    Extract slicer/embedded metadata from a .3mf file.

    Never raises: returns as much as could be parsed, or {} for files that
    aren't valid ZIPs / contain none of the known metadata members.
    """
    result = {}
    try:
        with zipfile.ZipFile(file_path) as zf:
            names = zf.namelist()

            core_name = _find_member(names, suffix='3dmodel.model')
            if core_name:
                result.update(_parse_core_model_xml(zf, core_name))

            config = {}
            orca_name = _find_member(names, suffix='project_settings.config')
            prusa_name = _find_member(names, suffix='slic3r_pe.config')
            if orca_name:
                config = _parse_json_config(zf, orca_name)
            elif prusa_name:
                config = _parse_ini_config(zf, prusa_name)
            result.update(_extract_slicer_fields(config))
    except (zipfile.BadZipFile, OSError) as e:
        logger.warning(f"Could not read 3MF metadata from {file_path}: {e}")
    except Exception:
        logger.exception(f"Unexpected error parsing 3MF metadata from {file_path}")
    return result


def _find_member(names, suffix):
    """Case-insensitive lookup of a ZIP member by path suffix."""
    suffix = suffix.lower()
    for name in names:
        if name.lower().endswith(suffix):
            return name
    return None


def _parse_core_model_xml(zf, member_name) -> dict:
    """Pull <metadata name="..."> entries out of the core model XML.

    Only the header is interesting, but the geometry can make this file tens
    of MB — iterparse and bail at the first non-metadata element instead of
    building the whole tree.
    """
    found = {}
    try:
        with zf.open(member_name) as fh:
            for _, elem in ET.iterparse(fh, events=('end',)):
                tag = elem.tag.rsplit('}', 1)[-1]  # strip XML namespace
                if tag == 'metadata':
                    name = elem.get('name', '')
                    # Slicers namespace some entries, e.g. "slic3rpe:Version3mf"
                    plain = name.rsplit(':', 1)[-1]
                    if name == 'Application' or plain == 'Application':
                        found.update(_split_application(elem.text or ''))
                    elif name in _CORE_METADATA_KEYS and elem.text:
                        found[_CORE_METADATA_KEYS[name]] = elem.text.strip()
                elif tag in ('resources', 'mesh', 'object', 'build'):
                    break  # past the metadata header — stop before geometry
                elem.clear()
    except (ET.ParseError, KeyError, OSError, UnicodeDecodeError) as e:
        logger.warning(f"Could not parse 3MF core model XML ({member_name}): {e}")
    return found


def _split_application(app_string) -> dict:
    """
    Split an Application metadata string like "PrusaSlicer-2.7.1+win64" or
    "OrcaSlicer-2.1.1" into slicer name + version.
    """
    app_string = (app_string or '').strip()
    if not app_string:
        return {}
    match = re.match(r'^(.*?)[-\s]v?(\d[\w.+-]*)$', app_string)
    if match:
        name = match.group(1).strip()
        version = match.group(2).split('+')[0]  # drop build suffix like +win64
        return {'slicer_name': name, 'slicer_version': version}
    return {'slicer_name': app_string}


def _parse_json_config(zf, member_name) -> dict:
    """Orca/Bambu Metadata/project_settings.config — one flat JSON object."""
    try:
        with zf.open(member_name) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, KeyError, OSError, UnicodeDecodeError) as e:
        logger.warning(f"Could not parse 3MF JSON config ({member_name}): {e}")
        return {}


def _parse_ini_config(zf, member_name) -> dict:
    """
    PrusaSlicer Metadata/Slic3r_PE.config — lines of "; key = value"
    (every line is ;-prefixed in files PrusaSlicer writes).
    """
    config = {}
    try:
        with zf.open(member_name) as fh:
            text = fh.read().decode('utf-8', errors='replace')
        for line in text.splitlines():
            line = line.lstrip('; \t')
            if '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            if key:
                config[key] = value.strip()
    except (KeyError, OSError) as e:
        logger.warning(f"Could not parse 3MF INI config ({member_name}): {e}")
    return config


def _extract_slicer_fields(config) -> dict:
    """Map the (Prusa or Orca) config dict onto our curated output keys."""
    if not config:
        return {}
    out = {}

    printer = _first(config.get(_PRINTER_PROFILE_KEY))
    if printer:
        out['printer_profile'] = printer
    print_profile = _first(config.get(_PRINT_PROFILE_KEY))
    if print_profile:
        out['print_profile'] = print_profile

    names = _as_list(config.get(_FILAMENT_NAME_KEY))
    types = _as_list(config.get(_FILAMENT_TYPE_KEY))
    colors = _as_list(config.get(_FILAMENT_COLOR_KEY))
    count = max(len(names), len(types), len(colors))
    filaments = []
    for i in range(count):
        filament = {}
        if i < len(names) and names[i]:
            filament['name'] = names[i]
        if i < len(types) and types[i]:
            filament['type'] = types[i]
        if i < len(colors) and colors[i]:
            filament['color'] = colors[i]
        if filament:
            filaments.append(filament)
    if filaments:
        out['filaments'] = filaments

    layer_height = _as_float(_first(config.get(_LAYER_HEIGHT_KEY)))
    if layer_height is not None:
        out['layer_height'] = layer_height
    nozzle = _as_float(_first(config.get(_NOZZLE_DIAMETER_KEY)))
    if nozzle is not None:
        out['nozzle_diameter'] = nozzle

    return out


def _as_list(value):
    """
    Normalize a config value to a list of strings: Orca JSON uses real lists
    for per-filament values; Prusa INI packs them as "A;B" strings.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(';')]


def _first(value):
    """First element of a per-filament value, or the scalar itself."""
    values = _as_list(value)
    return values[0] if values else None


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
