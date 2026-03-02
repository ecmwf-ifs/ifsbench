# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Test the common CLI options and utilities provided by ifsbench
"""

from pathlib import Path
import re

from click.testing import CliRunner
import pytest

from ifsbench.command_line.cli import cli, reference_options, run_options


@pytest.fixture(scope='module', name='runner')
def fixture_runner():
    """Provides a :any:`CliRunner` instance"""
    return CliRunner()


@pytest.fixture(scope='module', name='runopts_cmd')
def fixture_runopts_cmd():
    """
    Instantiate a helper command that prints :any:`RunOptions`
    """

    @cli.command('runopts-cmd')
    @run_options
    def _runopts_cmd(runopts):
        print(f'nproc = {runopts.nproc}')
        print(f'nthread = {runopts.nthread}')
        print(f'hyperthread = {runopts.hyperthread}')
        print(f'nproc_io = {runopts.nproc_io}')
        print(f'arch = {runopts.arch}')
        print(f'launch_cmd = {runopts.launch_cmd}')
        print(f'launch_options = {runopts.launch_options}')
        print(f'forecast_length = {runopts.forecast_length}')
        print(f'nproma = {runopts.nproma}')

    return _runopts_cmd


@pytest.fixture(scope='module', name='refopts_cmd')
def fixture_refopts_cmd():
    """
    Instantiate a helper command that prints :any:`ReferenceOptions`
    """

    @cli.command('refopts-cmd')
    @reference_options
    def _refopts_cmd(refopts):
        print(f'path = {refopts.path}')
        print(f'validate = {refopts.validate}')
        print(f'update = {refopts.update}')
        print(f'comment = {refopts.comment}')

    return _refopts_cmd


_output_pattern = re.compile(r'^(\w+) = (.+)$', re.MULTILINE)


def parse_output(string):
    """Uitility routine to parse the output of the test commands"""
    output = {match[1]: match[2] for match in _output_pattern.finditer(string)}
    return output


@pytest.mark.usefixtures('runopts_cmd')
@pytest.mark.parametrize(
    'options,expected',
    [
        (
            [],
            {
                'nproc': '1',
                'nthread': '1',
                'hyperthread': '1',
                'nproc_io': '0',
                'arch': 'None',
                'launch_cmd': 'None',
                'launch_options': 'None',
                'forecast_length': 'None',
                'nproma': 'None',
            },
        ),
        (
            [
                '--nproc=32',
                '--nthread=4',
                '--hyperthread=2',
                '--nproc-io=2',
                '--arch=foobar',
                '--launch-options="--mem=120G -q np -p par"',
                '--forecast-length=h24',
                '--nproma=32',
            ],
            {
                'nproc': '32',
                'nthread': '4',
                'hyperthread': '2',
                'nproc_io': '2',
                'arch': 'foobar',
                'launch_cmd': 'None',
                'launch_options': '"--mem=120G -q np -p par"',
                'forecast_length': 'h24',
                'nproma': '32',
            },
        ),
        (
            ['--launch-cmd="srun -n 12"'],
            {
                'nproc': '1',
                'nthread': '1',
                'hyperthread': '1',
                'nproc_io': '0',
                'arch': 'None',
                'launch_cmd': '"srun -n 12"',
                'launch_options': 'None',
                'forecast_length': 'None',
                'nproma': 'None',
            },
        ),
        (
            ['-l"srun -n 12"', '-a', 'foobar'],
            {
                'nproc': '1',
                'nthread': '1',
                'hyperthread': '1',
                'nproc_io': '0',
                'arch': 'foobar',
                'launch_cmd': '"srun -n 12"',
                'launch_options': 'None',
                'forecast_length': 'None',
                'nproma': 'None',
            },
        ),
        (
            ['-n4', '-c2', '-a blub', '--fclen=d10', '--nproma=-24'],
            {
                'nproc': '4',
                'nthread': '2',
                'hyperthread': '1',
                'nproc_io': '0',
                'arch': ' blub',
                'launch_cmd': 'None',
                'launch_options': 'None',
                'forecast_length': 'd10',
                'nproma': '-24',
            },
        ),
    ],
)
def test_run_options(runner, options, expected):
    """
    Verify that the :any:`run_options` decorator works as expected
    """
    response = runner.invoke(cli, ['runopts-cmd', *options])
    assert response.exit_code == 0
    output = parse_output(response.output)
    assert output == expected


@pytest.mark.usefixtures('refopts_cmd')
@pytest.mark.parametrize(
    'options,expected',
    [
        (
            [],
            {
                'path': 'None',
                'validate': 'True',
                'update': 'False',
                'comment': 'None',
            },
        ),
        (
            [f'--reference={Path(__file__).resolve}', '--validate', '--update-reference'],
            {
                'path': str(Path(__file__).resolve),
                'validate': 'True',
                'update': 'True',
                'comment': 'None',
            },
        ),
        (
            [
                f'-r{Path(__file__).resolve}',
                '--no-validate',
                '--update-reference',
                '--comment="Some funny text"',
            ],
            {
                'path': str(Path(__file__).resolve),
                'validate': 'False',
                'update': 'True',
                'comment': '"Some funny text"',
            },
        ),
    ],
)
def test_reference_options(runner, options, expected):
    """
    Verify that the :any:`reference_options` decorator works as expected
    """
    response = runner.invoke(cli, ['refopts-cmd', *options])
    assert response.exit_code == 0
    output = parse_output(response.output)
    assert output == expected
