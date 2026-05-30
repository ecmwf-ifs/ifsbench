# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Functional tests for ifsbench CMake installation.
"""

import os
from pathlib import Path
import shutil
from subprocess import CalledProcessError, PIPE

import pytest

from ifsbench.util import execute


def check_cmake():
    """
    Check if CMake is available.
    """
    try:
        execute(['cmake', '--version'], stdout=PIPE)
    except (CalledProcessError, FileNotFoundError):
        return False
    return True


pytestmark = pytest.mark.skipif(not check_cmake(), reason='CMake not available')


@pytest.fixture(scope='module', name='repo_root')
def fixture_repo_root():
    """
    Return the ifsbench source directory.
    """
    return Path(__file__).parents[1]


@pytest.fixture(scope='module', name='ecbuild_cmake_dir')
def fixture_ecbuild_cmake_dir(tmp_path_factory):
    """
    Download ecbuild and return its CMake module directory.
    """
    if not shutil.which('git'):
        pytest.skip('git not available')

    tmp_dir = tmp_path_factory.mktemp('ecbuild')
    ecbuild_dir = tmp_dir/'ecbuild'
    execute(['git', 'clone', 'https://github.com/ecmwf/ecbuild.git', str(ecbuild_dir)])
    return ecbuild_dir/'cmake'


@pytest.fixture(scope='module', name='ifsbench_install', params=[False, True], ids=['online', 'populate'])
def fixture_ifsbench_install(tmp_path_factory, repo_root, ecbuild_cmake_dir, request):
    """
    Configure and install ifsbench with CMake.
    """
    tmp_dir = tmp_path_factory.mktemp(f'ifsbench_cmake_{request.param}')
    build_dir = tmp_dir/'build'
    install_dir = tmp_dir/'install'
    env = os.environ.copy()
    cmake_args = []

    if request.param:
        artifacts_dir = tmp_dir/'artifacts'
        env['ARTIFACTS_DIR'] = str(artifacts_dir)
        execute([str(repo_root/'populate')], cwd=repo_root, env=env)
        assert any(artifacts_dir.glob('*.whl'))

        cmake_args += [f'-DARTIFACTS_DIR={artifacts_dir}']
        env['http_proxy'] = 'http://foo.bar.baz'
        env['https_proxy'] = 'http://foo.bar.baz'

    configure_command = [
        'cmake',
        '-S', str(repo_root),
        '-B', str(build_dir),
        f'-DCMAKE_MODULE_PATH={ecbuild_cmake_dir}',
        '-DENABLE_TESTS=OFF',
    ]
    configure_command += cmake_args

    execute(configure_command, env=env)
    execute(['cmake', '--install', str(build_dir), '--prefix', str(install_dir)], env=env)

    return build_dir, install_dir


def write_consumer_project(project_dir):
    """
    Write a small ecbuild consumer project for ifsbench.
    """
    project_dir.mkdir()
    (project_dir/'CMakeLists.txt').write_text(
        """
cmake_minimum_required( VERSION 3.19 FATAL_ERROR )
find_package( ecbuild REQUIRED )

project( ifsbench_consumer VERSION 1.0.0 LANGUAGES NONE )

ecbuild_find_package( ifsbench REQUIRED )

if( NOT IFSBENCH_Python3_EXECUTABLE )
    message( FATAL_ERROR "IFSBENCH_Python3_EXECUTABLE is not defined" )
endif()

if( NOT EXISTS ${IFSBENCH_Python3_EXECUTABLE} )
    message( FATAL_ERROR "IFSBENCH_Python3_EXECUTABLE does not exist: ${IFSBENCH_Python3_EXECUTABLE}" )
endif()

if( NOT TARGET ifs-bench.py )
    message( FATAL_ERROR "ifs-bench.py target is not defined" )
endif()

if( NOT TARGET nml-diff.py )
    message( FATAL_ERROR "nml-diff.py target is not defined" )
endif()

get_target_property( IFSBENCH_CLI ifs-bench.py IMPORTED_LOCATION )
get_target_property( NML_DIFF_CLI nml-diff.py IMPORTED_LOCATION )

if( NOT EXISTS ${IFSBENCH_CLI} )
    message( FATAL_ERROR "ifs-bench.py imported location does not exist: ${IFSBENCH_CLI}" )
endif()

if( NOT EXISTS ${NML_DIFF_CLI} )
    message( FATAL_ERROR "nml-diff.py imported location does not exist: ${NML_DIFF_CLI}" )
endif()

execute_process(
    COMMAND ${IFSBENCH_Python3_EXECUTABLE} -c "import ifsbench"
    RESULT_VARIABLE _RET
)
if( NOT _RET EQUAL 0 )
    message( FATAL_ERROR "Unable to import ifsbench with exported Python interpreter" )
endif()
        """,
        encoding='utf-8'
    )


def test_cmake_install_and_exports(tmp_path, ifsbench_install, ecbuild_cmake_dir):
    """
    Verify CMake install and downstream package discovery.
    """
    build_dir, install_dir = ifsbench_install

    env = os.environ.copy()
    env['http_proxy'] = 'http://foo.bar.baz'
    env['https_proxy'] = 'http://foo.bar.baz'

    ifsbench_cli = install_dir/'bin'/'ifs-bench.py'
    nml_diff_cli = install_dir/'bin'/'nml-diff.py'
    install_python = install_dir/'var'/'ifsbench_env'/'bin'/'python'

    assert ifsbench_cli.exists()
    assert nml_diff_cli.exists()
    assert install_python.exists()

    execute([str(ifsbench_cli), '--help'], env=env)
    execute([str(nml_diff_cli), '--help'], env=env)
    execute([str(install_python), '-c', '__import__("ifsbench")'], env=env)

    consumer_dir = tmp_path/'consumer'
    write_consumer_project(consumer_dir)

    for package_root in (build_dir, install_dir):
        consumer_build_dir = tmp_path/f'consumer-build-{package_root.name}'
        execute([
            'cmake',
            '-S', str(consumer_dir),
            '-B', str(consumer_build_dir),
            f'-DCMAKE_MODULE_PATH={ecbuild_cmake_dir}',
            f'-Difsbench_ROOT={package_root}',
        ], env=env)
