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
cmake_minimum_required( VERSION 3.17 FATAL_ERROR )
find_package( ecbuild 3.4 REQUIRED HINTS ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../ecbuild)

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

# Setup Python virtual environment
include( python_venv )
python_venv( ifsbench_env )

# Enable Pytest testing
if( ${ENABLE_TESTS} )

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
if( NOT ${CMAKE_VERBOSE_MAKEFILE} )
    list ( APPEND PIP_OPTIONS "-q" )
endif()
if( ${HAVE_EDITABLE} )
    list( APPEND PIP_OPTIONS "-e" )
endif()

set( _INSTALL_OPTIONS "" )
if( IFSBENCH_INSTALL_OPTIONS )
    list( JOIN IFSBENCH_INSTALL_OPTIONS "," _INSTALL_OPT_STR )
    set( _INSTALL_OPTIONS "[${_INSTALL_OPT_STR}]" )
endif()

if( DEFINED ARTIFACTS_DIR )
    list( APPEND PIP_OPTIONS "--no-index;--find-links=${ARTIFACTS_DIR}" )
endif()
add_custom_target( ifsbench ALL ${Python3_EXECUTABLE} -m pip install ${PIP_OPTIONS} ${CMAKE_CURRENT_SOURCE_DIR}${_INSTALL_OPTIONS} )

add_executable( ifs-bench.py IMPORTED GLOBAL )
set_property( TARGET ifs-bench.py PROPERTY IMPORTED_LOCATION ${Python3_VENV_BIN}/ifs-bench.py )
add_dependencies( ifs-bench.py ifsbench )

# Make certain variables available
if( NOT PROJECT_NAME STREQUAL CMAKE_PROJECT_NAME )
    set( IFSBENCH_Python3_EXECUTABLE ${Python3_EXECUTABLE} PARENT_SCOPE )
endif()

# Install the project so it can be used within the bundle
ecbuild_install_project( NAME ifsbench )

# print summary
ecbuild_print_summary()
