# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Utilities for loading YAML files.
"""

import copy
from pathlib import Path
from typing import Any, Dict, Union

import yaml


__all__ = ['read_yaml']


class _ConfigureMarker:
    """
    Placeholder for a ``!configure`` node that is resolved after the
    full document has been loaded.
    """

    def __init__(self, template_path, overrides):
        self.template_path = template_path
        self.overrides = overrides


def _make_loader(base_dir, encoding):
    """
    Create a custom YAML loader with ``!import`` and ``!configure``
    constructors that resolve paths relative to *base_dir*.
    """

    # pylint: disable=R0901
    class _Loader(yaml.SafeLoader):
        pass

    def _import_constructor(loader, node):
        """Handle ``!import other_file.yaml``."""

        # Load the import path.
        rel_path = loader.construct_scalar(node)

        # Only use the path relative to the base dir.
        import_path = (base_dir / rel_path).resolve()

        if not import_path.is_file():
            raise FileNotFoundError(f'Imported YAML file not found: {import_path}')

        # Parse the imported file in the same way as everything else.
        return read_yaml(str(import_path), encoding)

    def _configure_constructor(loader, tag_suffix, node):
        """Handle ``!configure:template/path`` mapping nodes."""
        overrides = loader.construct_mapping(node, deep=True)

        # Extract the template from the !configure:<template> line.
        template_ref = tag_suffix.lstrip(':')

        return _ConfigureMarker(template_ref, overrides)

    _Loader.add_constructor('!import', _import_constructor)
    _Loader.add_multi_constructor('!configure:', _configure_constructor)

    return _Loader


def _resolve_template(root, template_path):
    """
    Walk *root* (a dict) along the slash-separated *template_path* and
    return the value found there.
    """
    current = root
    for key in template_path.split('/'):
        try:
            current = current[key]
        except (KeyError, TypeError) as ex:
            raise KeyError(f'Template path {template_path!r} not found in YAML document') from ex
    return current


def _substitute(obj, overrides):
    """
    Recursively replace ``${key}`` placeholders in strings inside *obj*
    with values from *overrides*.
    """
    if isinstance(obj, str):
        # Check for an exact single-placeholder match first so that
        # non-string override types are preserved.
        for key, value in overrides.items():
            if obj == f'${{{key}}}':
                return value
        for key, value in overrides.items():
            obj = obj.replace(f'${{{key}}}', str(value))
        return obj
    if isinstance(obj, dict):
        return {k: _substitute(v, overrides) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(item, overrides) for item in obj]
    return obj


def _resolve_markers(obj, root):
    """
    Walk the parsed data structure and resolve any
    :class:`_ConfigureMarker` instances using templates from *root*.
    """
    if isinstance(obj, _ConfigureMarker):
        template = copy.deepcopy(_resolve_template(root, obj.template_path))
        return _substitute(template, obj.overrides)
    if isinstance(obj, dict):
        return {k: _resolve_markers(v, root) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_markers(item, root) for item in obj]
    return obj


def read_yaml(filename: Union[str, Path], encoding='utf-8') -> Dict[str, Any]:
    """
    Parse a YAML file and return the resulting dictionary.

    In addition to standard YAML files, using this function adds support for

      * ``!import`` (includes the content of another file)
      * ``!configure:reference`` (copies an existing YAML block and replaces
        ${name} entries with specified values.

    Parameters
    ----------
    filename: str or Path
        The path to the YAML file.
    encoding: str
        The encoding that is used when opening the YAML file.

    Returns
    -------
    Dict
        The parsed values as a YAML file.

    Raises
    ------
    FileNotFoundError
        If *filename* or any ``!import``-ed file does not exist.

    Example
    -------
        included: !import other_file.yaml

        templates:
          greeting:
            message: Hello, ${name}!

        instances:
          welcome: !configure:templates/greeting
            name: World

    """

    filepath = Path(filename).resolve()
    if not filepath.is_file():
        raise FileNotFoundError(f'YAML file not found: {filepath}')

    # Get the base_dir of the YAML file. This will be used as the reference
    # directory for finding other YAML files to import.
    base_dir = filepath.parent
    loader_cls = _make_loader(base_dir, encoding)

    with open(filepath, encoding=encoding) as fh:
        data = yaml.load(fh, Loader=loader_cls)

    # Resolve the !configure annotations in a post-processing step.
    data = _resolve_markers(data, data)
    return data
