# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for the :any:`BashLauncher` implementation.
"""

from pathlib import Path
import re

import pytest

from ifsbench import (
    Job,
    BashLauncher,
    DirectLauncher,
    SrunLauncher,
    EnvHandler,
    EnvOperation,
    DefaultEnvPipeline
)


@pytest.fixture(name='test_env')
def fixture_test_env():
    return DefaultEnvPipeline(
        handlers=[
            EnvHandler(mode=EnvOperation.SET, key='SOME_VALUE', value='5'),
            EnvHandler(mode=EnvOperation.SET, key='OTHER_VALUE', value='6'),
            EnvHandler(mode=EnvOperation.DELETE, key='SOME_VALUE'),
        ]
    )


@pytest.fixture(name='test_env_none')
def fixture_test_env_none():
    return None


@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('custom_flags', [None, [], ['--cuda']])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
def test_bashlauncher_run_dir(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    request
):
    """
    Test the run_dir component of the LaunchData object that is returned by
    BashLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = BashLauncher(
        base_launcher=base_launcher,
        base_launcher_flags=base_launcher_flags
    )

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=custom_flags
    )

    assert result.run_dir == result.run_dir

    # Asser that the corresponding bash script has been written to
#    assert len(list((tmp_path/'bash_scripts').glob(cmd[0]+'*.sh'))) == 1

@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('custom_flags', [None, [], ['--cuda']])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
def test_bashlauncher_env(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    request
):
    """
    Test the env component of the LaunchData object that is returned by
    BashLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = BashLauncher(
        base_launcher=base_launcher,
        base_launcher_flags=base_launcher_flags
    )

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=custom_flags
    )

    # pylint: disable=C1803
    assert result.env == {}

@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('custom_flags', [None, [], ['--cuda']])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
def test_bashlauncher_cmd(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    request
):
    """
    Test the cmd component of the LaunchData object that is returned by
    BashLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = BashLauncher(
        base_launcher=base_launcher,
        base_launcher_flags=base_launcher_flags
    )

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=custom_flags
    )

    # The command is expected to be /bin/bash script_path.
    assert len(result.cmd) == 2

    assert result.cmd[0] == '/bin/bash'

    # We check the script_path now. The directory of the script must be equal
    # to run_dir/bash_scripts.
    script_path = Path(result.cmd[1])

    assert script_path.parent == tmp_path/'bash_scripts'


    # The script name itself is of the format command_date.sh. We don't check
    # the date exactly here, just the format.
    assert re.match(cmd[0] + '_[0-9-:]*.sh', script_path.name)

@pytest.mark.parametrize('cmd', [['ls', '-l'], ['something']])
@pytest.mark.parametrize('job', [Job(tasks=64), Job()])
@pytest.mark.parametrize('library_paths', [None, [], ['/library/path/something']])
@pytest.mark.parametrize('env_pipeline_name', ['test_env_none', 'test_env'])
@pytest.mark.parametrize('custom_flags', [None, [], ['--cuda']])
@pytest.mark.parametrize('base_launcher', [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize('base_launcher_flags', [[], ['--do-something']])
def test_bashlauncher_script(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    request
):
    """
    Test that the bash script that the BashLauncher prepares is correct.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = BashLauncher(
        base_launcher=base_launcher,
        base_launcher_flags=base_launcher_flags
    )

    base_result = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=base_launcher_flags
    )

    result = launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=custom_flags
    )

    script_path = Path(result.cmd[1])

    # There are essentially only three things we have to check
    # * The header/hashbang.
    # * All environmental definitions
    # * The actual launch command.

    header = None
    env_lines = []
    cmd_line = None

    with script_path.open('r', encoding='utf-8') as f:
        header = f.readline()

        lines = f.readlines()

        for line in lines:
            line = line.strip()

            if not line:
                continue

            if line.startswith('export'):
                env_lines.append(line.strip())
            else:
                cmd_line = line
                break

    assert '#! /bin/bash'.strip() == header.strip()

    ref_env = []

    for key, value in base_result.env.items():
        ref_env.append(f'export {key}="{value}"')

    assert set(ref_env) == set(env_lines)


    # pylint: disable=R1713
    ref_cmd_line = ""
    for c in base_result.cmd:
        ref_cmd_line += f'"{c}" '

    assert ref_cmd_line.strip() == cmd_line.strip()
