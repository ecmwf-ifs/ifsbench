# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

##############################################################################
#.rst:
#
# ifsbench
# ========
#
# Install ifsbench with dependencies. ::
#
# Features
# --------
#
# :EDITABLE:    Install ifsbench as an editable package (Default: ``OFF``)
#
# Installation procedure
# ----------------------
#
# A virtual environment is created for ifsbench into which it is installed along
# with any dependencies.
#
##############################################################################

# Version 3.12 required to use FindPython
# Version 3.15 officially required to use Python3_FIND_VIRTUALENV (not working on 3.15.3,
# though, and use 3.17 for conda support anyway)
# Version 3.19 for support of file(CHMOD)
cmake_minimum_required( VERSION 3.19 FATAL_ERROR )
find_package( ecbuild 3.7 REQUIRED )

# Specify project and configuration options
project( ifsbench LANGUAGES NONE )

# Declare options
ecbuild_add_option(
    FEATURE EDITABLE
    DEFAULT OFF
    DESCRIPTION "Install ifsbench as an editable Python package"
)

ecbuild_add_option(
    FEATURE GRIB
    DEFAULT OFF
    DESCRIPTION "Install ifsbench with GRIB support (requires eccodes)"
    REQUIRED_PACKAGES "eccodes"
)

# Make CMake script files available in build and install directory
add_subdirectory( cmake )
install( DIRECTORY cmake DESTINATION ${INSTALL_DATA_DIR} PATTERN "CMakeLists.txt" EXCLUDE )

# The list of ifsbench frontend scripts
set( IFSBENCH_EXECUTABLES ifs-bench.py nml-diff.py )

# Setup Python virtual environment
include( ifsbench_python_macros )
set( PYTHON_VERSION 3.8 )
ifsbench_setup_python_venv(
    VENV_NAME ifsbench_env
    PYTHON_VERSION ${PYTHON_VERSION}
    INSTALL_VENV
)

# Enable Pytest testing
if( HAVE_TESTS )

    ecbuild_add_test(
        TARGET ifsbench_tests
        COMMAND ${Python3_EXECUTABLE}
        ARGS -m pytest -v tests
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    list( APPEND IFSBENCH_INSTALL_OPTIONS "tests" )

endif()

if( HAVE_GRIB )
  list( APPEND IFSBENCH_INSTALL_OPTIONS "grib" )
endif()

# Install ifsbench with dependencies
set( _INSTALL_OPTIONS "" )
if( IFSBENCH_INSTALL_OPTIONS )
    list( JOIN IFSBENCH_INSTALL_OPTIONS "," _INSTALL_OPT_STR )
    set( _INSTALL_OPTIONS "[${_INSTALL_OPT_STR}]" )
endif()

# Optionally use the ARTIFACTS_DIR as wheelhouse, if provided
if( DEFINED ARTIFACTS_DIR )
    set( WHEELS_DIR_OPTION WHEELS_DIR "${ARTIFACTS_DIR}" )
else()
    set( WHEELS_DIR_OPTION "" )
endif()

if( HAVE_EDITABLE )
   set( EDITABLE_OPTION "EDITABLE" )
else()
   set( EDITABLE_OPTION "" )
endif()

# Determine whether this is a Git worktree or if we have to provide
# the version number to setuptools_scm
if( NOT EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/.git )
    set( ENV{SETUPTOOLS_SCM_PRETEND_VERSION} ${ifsbench_VERSION} )
endif()

# We install ifsbench at configure time to make the CLI targets immediately
# available to later CMake projects in the bundle.
ecbuild_info( "Install ifsbench in virtual environment" )
ifsbench_install_python_package(
    REQUIREMENT_SPEC ${CMAKE_CURRENT_SOURCE_DIR}${_INSTALL_OPTIONS}
    ${EDITABLE_OPTION}
    ${WHEELS_DIR_OPTION}
)
ecbuild_info( "Install ifsbench in virtual environment - done" )

# Discover ifsbench executables and make available as CMake targets
include( ifsbench_find_executables )
ifsbench_find_executables()

# Install the project so it can be used within the bundle
ecbuild_install_project( NAME ifsbench )

# print summary
ecbuild_print_summary()
