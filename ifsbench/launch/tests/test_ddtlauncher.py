# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Some sanity tests for :any:`Arch` implementations
"""

import pytest

from ifsbench import (
    Job,
    DDTLauncher,
    DirectLauncher,
    SrunLauncher,
    EnvHandler,
    EnvOperation,
    DefaultEnvPipeline,
)


@pytest.fixture(name="test_env")
def fixture_test_env():
    return DefaultEnvPipeline(
        handlers=[
            EnvHandler(mode=EnvOperation.SET, key="SOME_VALUE", value="5"),
            EnvHandler(mode=EnvOperation.SET, key="OTHER_VALUE", value="6"),
            EnvHandler(mode=EnvOperation.DELETE, key="SOME_VALUE"),
        ]
    )


@pytest.fixture(name="test_env_none")
def fixture_test_env_none():
    return None


@pytest.mark.parametrize("cmd", [["ls", "-l"], ["something"]])
@pytest.mark.parametrize("job", [Job(tasks=64), Job()])
@pytest.mark.parametrize("library_paths", [None, [], ["/library/path/something"]])
@pytest.mark.parametrize("env_pipeline_name", ["test_env_none", "test_env"])
@pytest.mark.parametrize("custom_flags", [[], ["--cuda"]])
@pytest.mark.parametrize("base_launcher", [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize("base_launcher_flags", [[], ["--do-something"]])
def test_ddtlauncher_run_dir(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    request,
):
    """
    Test the run_dir component of the LaunchData object that is returned by
    DDTLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = DDTLauncher(flags=custom_flags)
    base_launch_data = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=base_launcher_flags,
    )

    result = launcher.wrap(
        launch_data=base_launch_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    assert result.run_dir == base_launch_data.run_dir


@pytest.mark.parametrize("cmd", [["ls", "-l"], ["something"]])
@pytest.mark.parametrize("job", [Job(tasks=64), Job()])
@pytest.mark.parametrize("library_paths", [None, [], ["/library/path/something"]])
@pytest.mark.parametrize("env_pipeline_name", ["test_env_none", "test_env"])
@pytest.mark.parametrize("custom_flags", [[], ["--cuda"]])
@pytest.mark.parametrize("base_launcher", [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize("base_launcher_flags", [[], ["--do-something"]])
def test_ddtlauncher_env(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    request,
):
    """
    Test the env component of the LaunchData object that is returned by
    DDTLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    launcher = DDTLauncher(flags=custom_flags)
    base_launch_data = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=base_launcher_flags,
    )

    result = launcher.wrap(
        launch_data=base_launch_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    assert result.env == base_launch_data.env


@pytest.mark.parametrize("cmd", [["ls", "-l"], ["something"]])
@pytest.mark.parametrize("job", [Job(tasks=64), Job()])
@pytest.mark.parametrize("library_paths", [None, [], ["/library/path/something"]])
@pytest.mark.parametrize("env_pipeline_name", ["test_env_none", "test_env"])
@pytest.mark.parametrize("custom_flags", [None, [], ["--cuda"]])
@pytest.mark.parametrize("base_launcher", [SrunLauncher(), DirectLauncher()])
@pytest.mark.parametrize("base_launcher_flags", [[], ["--do-something"]])
def test_ddtlauncher_cmd(
    tmp_path,
    cmd,
    job,
    library_paths,
    env_pipeline_name,
    custom_flags,
    base_launcher,
    base_launcher_flags,
    request,
):
    """
    Test the cmd component of the LaunchData object that is returned by
    DDTLauncher.prepare.
    """

    env_pipeline = request.getfixturevalue(env_pipeline_name)

    if custom_flags:
        launcher = DDTLauncher(flags=custom_flags)
    else:
        launcher = DDTLauncher()
    base_launch_data = base_launcher.prepare(
        run_dir=tmp_path,
        job=job,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
        custom_flags=base_launcher_flags,
    )

    result = launcher.wrap(
        launch_data=base_launch_data,
        run_dir=tmp_path,
        cmd=cmd,
        library_paths=library_paths,
        env_pipeline=env_pipeline,
    )

    if not custom_flags:
        assert ["ddt"] + ["--"] + base_launch_data.cmd == result.cmd
    else:
        assert ["ddt"] + custom_flags + ["--"] + base_launch_data.cmd == result.cmd
