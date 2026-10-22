"""Strict, offline validation of the unchanged v1 interchange contracts."""
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).parent / 'contracts' / 'v1'


def reject_network(uri):
    raise ValueError('Remote schema resolution is disabled')


SCHEMAS = {p.stem.removesuffix('.schema'): json.loads(p.read_text())
           for p in SCHEMA_DIR.glob('*.schema.json')}
REGISTRY = Registry(retrieve=reject_network).with_resources(
    (schema['$id'], Resource.from_contents(schema)) for schema in SCHEMAS.values())
VALIDATORS = {name: Draft202012Validator(schema, registry=REGISTRY,
                                       format_checker=FormatChecker())
              for name, schema in SCHEMAS.items()}
ID_VALIDATOR = Draft202012Validator(SCHEMAS['common']['$defs']['id'])
VERSIONS_VALIDATOR = Draft202012Validator(SCHEMAS['common']['$defs']['versions'])


def validate(name, value):
    VALIDATORS[name].validate(value)


def public_schema(name):
    """Embed contract refs in OpenAPI without modifying the stored contracts."""
    schema = deepcopy(SCHEMAS[name])

    def rewrite(value):
        if isinstance(value, dict):
            value.pop('$id', None)
            for key, item in list(value.items()):
                if key == '$ref':
                    filename, _, fragment = item.partition('#')
                    target = filename.removesuffix('.schema.json')
                    value[key] = f'#/components/schemas/{target}' + fragment
                else:
                    rewrite(item)
        elif isinstance(value, list):
            for item in value:
                rewrite(item)
    rewrite(schema)
    return schema
