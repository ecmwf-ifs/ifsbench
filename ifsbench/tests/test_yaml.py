# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Tests for ifsbench.yaml utilities
"""

import textwrap

import pytest

from ifsbench.yaml import read_yaml


@pytest.fixture(name='yaml_dir')
def fixture_yaml_dir(tmp_path):
    """Provide a temporary directory for YAML test files."""
    return tmp_path


def test_read_yaml_basic(yaml_dir):
    """read_yaml loads a simple YAML file."""
    f = yaml_dir / 'basic.yaml'
    f.write_text('key: value\ncount: 42\n')
    result = read_yaml(str(f))
    assert result == {'key': 'value', 'count': 42}


def test_read_yaml_file_not_found():
    """read_yaml raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        read_yaml('/nonexistent/path/missing.yaml')


# -- !include -----------------------------------------------------------------


def test_include_basic(yaml_dir):
    """!include includes another YAML file."""
    (yaml_dir / 'child.yaml').write_text('child_key: child_value\n')
    (yaml_dir / 'parent.yaml').write_text('included: !include child.yaml\n')
    result = read_yaml(str(yaml_dir / 'parent.yaml'))
    assert result == {'included': {'child_key': 'child_value'}}


def test_include_subdirectory(yaml_dir):
    """!include resolves relative to the main file's directory."""
    sub = yaml_dir / 'sub'
    sub.mkdir()
    (sub / 'nested.yaml').write_text('nested: true\n')
    (yaml_dir / 'main.yaml').write_text('data: !include sub/nested.yaml\n')
    result = read_yaml(str(yaml_dir / 'main.yaml'))
    assert result == {'data': {'nested': True}}


def test_include_missing_file(yaml_dir):
    """!include raises FileNotFoundError when the referenced file is missing."""
    (yaml_dir / 'main.yaml').write_text('data: !include nonexistent.yaml\n')
    with pytest.raises(FileNotFoundError, match='nonexistent.yaml'):
        read_yaml(str(yaml_dir / 'main.yaml'))


def test_include_nested(yaml_dir):
    """!include works recursively (included file can include another)."""
    (yaml_dir / 'c.yaml').write_text('level: 2\n')
    (yaml_dir / 'b.yaml').write_text('nested: !include c.yaml\n')
    (yaml_dir / 'a.yaml').write_text('top: !include b.yaml\n')
    result = read_yaml(str(yaml_dir / 'a.yaml'))
    assert result == {'top': {'nested': {'level': 2}}}


def test_include_relative(yaml_dir):
    """!include only accepts relative paths."""
    (yaml_dir / 'subdir').mkdir()

    (yaml_dir / 'import1.yaml').write_text('level: 2\n')
    (yaml_dir / 'subdir/import2.yaml').write_text('level: 2\n')

    (yaml_dir / 'relative1.yaml').write_text('nested: !include import1.yaml\n')
    (yaml_dir / 'relative2.yaml').write_text('nested: !include subdir/import2.yaml\n')
    (yaml_dir / 'relative3.yaml').write_text('nested: !include subdir/../import1.yaml\n')

    # Read the files with the relative includes and just make sure that it
    # doesn't crash.
    for i in range(1, 4):
        read_yaml(yaml_dir / f'relative{i}.yaml')

    (yaml_dir / 'not_relative1.yaml').write_text('top: !include /etc/something.yaml\n')
    (yaml_dir / 'not_relative2.yaml').write_text('top: !include ../other_dir/something.yaml\n')
    (yaml_dir / 'not_relative3.yaml').write_text(
        'top: !include subdir/../../other_dir/something.yaml\n'
    )

    # Read the files with the non-relative includes and make sure that it
    # raises a ValueError.
    for i in range(1, 4):
        with pytest.raises(ValueError):
            read_yaml(yaml_dir / f'not_relative{i}.yaml')


# -- !configure --------------------------------------------------------------


def test_configure_basic(yaml_dir):
    """!configure substitutes template placeholders."""
    content = textwrap.dedent("""\
        templates:
          greeting:
            message: Hello, ${name}!

        instances:
          welcome: !configure:templates/greeting
            name: World
    """)
    (yaml_dir / 'cfg.yaml').write_text(content)
    result = read_yaml(str(yaml_dir / 'cfg.yaml'))
    assert result['instances']['welcome'] == {'message': 'Hello, World!'}


def test_configure_multiple_values(yaml_dir):
    """!configure substitutes multiple placeholders."""
    content = textwrap.dedent("""\
        templates:
          point:
            first: ${x}
            second: "${y}"
            third: "Hello ${z}"

        instances:
          origin: !configure:templates/point
            x: 0
            y: True
            z: World
    """)
    (yaml_dir / 'cfg.yaml').write_text(content)
    result = read_yaml(str(yaml_dir / 'cfg.yaml'))
    assert result['instances']['origin'] == {'first': 0, 'second': True, 'third': 'Hello World'}


def test_configure_preserves_template(yaml_dir):
    """!configure does not mutate the original template."""
    content = textwrap.dedent("""\
        templates:
          item:
            value: ${passed_value}

        instances:
          a: !configure:templates/item
            passed_value: 1
          b: !configure:templates/item
            passed_value: 2
    """)
    (yaml_dir / 'cfg.yaml').write_text(content)
    result = read_yaml(str(yaml_dir / 'cfg.yaml'))
    assert result['instances']['a'] == {'value': 1}
    assert result['instances']['b'] == {'value': 2}
    # Template is untouched
    assert result['templates']['item'] == {'value': '${passed_value}'}


def test_configure_missing_template(yaml_dir):
    """!configure raises KeyError for a missing template path."""
    content = textwrap.dedent("""\
        instances:
          bad: !configure:missing/path
            value: 1
    """)
    (yaml_dir / 'cfg.yaml').write_text(content)
    with pytest.raises(KeyError, match='missing/path'):
        read_yaml(str(yaml_dir / 'cfg.yaml'))


def test_configure_nested_template(yaml_dir):
    """!configure works with deeply nested template paths."""
    content = textwrap.dedent("""\
        some_template:
          default_template:
            value: ${passed_value}

        instances:
          my_instance: !configure:some_template/default_template
            passed_value: 5
    """)
    (yaml_dir / 'cfg.yaml').write_text(content)
    result = read_yaml(str(yaml_dir / 'cfg.yaml'))
    assert result['instances']['my_instance'] == {'value': 5}


def test_read_yaml_reference(yaml_dir):
    """
    Create custom YAML files and check the result explicitly.
    """
    content_include = textwrap.dedent("""\
        my_template:
          value: ${value}
          str_value: some_${str_value}
          list:
            - ${first_value}
            - ${second_value}
    """)

    content_main = textwrap.dedent("""\
        templates: !include include.yaml

        instances:
            my_instance: !configure:templates/my_template
                value: 5
                str_value: thing
                first_value: True
                second_value:
                    - 1
                    - 2
    """)

    (yaml_dir / 'include.yaml').write_text(content_include)
    (yaml_dir / 'main.yaml').write_text(content_main)

    result = read_yaml(yaml_dir / 'main.yaml')

    my_instance = result['instances']['my_instance']

    assert my_instance['value'] == 5
    assert my_instance['str_value'] == 'some_thing'
    assert my_instance['list'][0] is True
    assert my_instance['list'][1] == [1, 2]


# -- encoding ----------------------------------------------------------------


def test_read_yaml_custom_encoding(yaml_dir):
    """read_yaml respects a custom encoding parameter."""
    f = yaml_dir / 'latin.yaml'
    f.write_bytes('key: café\n'.encode('latin-1'))
    result = read_yaml(str(f), encoding='latin-1')
    assert result == {'key': 'café'}
