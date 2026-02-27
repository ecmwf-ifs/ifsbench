# (C) Copyright 2026 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

##############################################################################
#.rst:
#
# download_python_wheels
# ======================
#
# Download all dependencies for the given ``REQUIREMENT_SPEC`` and cache them in a
# wheelhouse at ``WHEELS_DIR``
#
#   download_python_wheels( REQUIREMENT_SPEC <spec> [ WHEELS_DIR <path> ] [ PYTHON_VERSION <version str> ]
#                           [ WHEEL_ARCH <spec> ] [ WHEEL_PYTHON_VERSION <spec> ] [ PYTHON_ROOT_DIR <path> ])
#
# Implementation note
# -------------------
#
# This function does intentionally not expose all PIP options directly because the PIP command line
# interface allows to specify option values via environment variables. These can therefore be used
# to further control the PIP behaviour, see https://pip.pypa.io/en/stable/cli/pip_download/
#
# Because PIP does not provide a mechanism for downloading PEP 518 build dependencies,
# this function builds the wheel also for the provided REQUIREMENT_SPEC instead of only downloading
# the required dependencies. See https://github.com/pypa/pip/issues/7863 for details.
# To provide a sane minimum, setuptools and wheel packages are always downloaded.
#
# The provided PYTHON_VERSION is used to discover a Python interpreter matching the version
# specification when calling pip. To download wheels for specific platforms or Python versions,
# use the PIP_PLATFORM, PIP_PYTHON_VERSION, PIP_IMPLEMENTATION, or PIP_ABI environment variables.
#
# It is safe to call this function during an offline build, as long as all wheels are already
# available in the wheelhouse. A dry-run call to ``pip install`` is used to determine the need
# for any wheel downloads before executing the ``pip download`` command.
#
# Options
# -------
#
# :REQUIREMENT_SPEC: The requirement spec as given to ``pip download`` and ``pip wheel``
# :WHEELS_DIR: The path of the wheelhouse directory to cache the wheels. Defaults to
#              ``${CMAKE_CURRENT_BINARY_DIR}/wheelhouse``
# :PYTHON_VERSION: Optional specification of permissible Python versions for find_package
# :WHEEL_ARCH: Optional specification of architecture for which to download non-pure Python wheels
# :WHEEL_PYTHON_VERSION: Optional specification of Python version for which to download wheels
#
##############################################################################

# We add this here to enforce the correct behaviour for find_package( Python3 ... )
cmake_minimum_required( VERSION 3.17 FATAL_ERROR )

function( download_python_wheels )

    set( options "" )
    set( oneValueArgs REQUIREMENT_SPEC WHEELS_DIR PYTHON_VERSION WHEEL_ARCH WHEEL_PYTHON_VERSION )
    set( multiValueArgs "" )

    cmake_parse_arguments( _PAR "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )

    if( _PAR_UNPARSED_ARGUMENTS )
        message( FATAL_ERROR "Unknown keywords given to download_python_wheels(): \"${_PAR_UNPARSED_ARGUMENTS}\"" )
    endif()

    if( NOT _PAR_REQUIREMENT_SPEC )
        message( FATAL_ERROR "No REQUIREMENT_SPEC provided to download_python_wheels()" )
    endif()

    message( STATUS "Checking for cached wheels in ${WHEELS_DIR}" )

    # Check for a suitable python interpreter
    find_package( Python3 ${_PAR_PYTHON_VERSION} COMPONENTS Interpreter REQUIRED QUIET )

    # If no wheelhouse dir is given, create one in the current binary directory
    if( _PAR_WHEELS_DIR )
        set( WHEELS_DIR "${_PAR_WHEELS_DIR}" )
    else()
        set( WHEELS_DIR "${CMAKE_CURRENT_BINARY_DIR}/wheelhouse" )
    endif()
    file( MAKE_DIRECTORY "${WHEELS_DIR}" )

    unset( PIP_OPTIONS )
    if( DEFINED _PAR_WHEEL_ARCH AND NOT _PAR_WHEEL_ARCH MATCHES None|NONE )
        string(REPLACE "\"" "" _WHEEL_ARCH ${_PAR_WHEEL_ARCH})
        list( APPEND PIP_OPTIONS "--platform=${_WHEEL_ARCH}" )
    endif()
    if( DEFINED _PAR_WHEEL_PYTHON_VERSION AND NOT _PAR_WHEEL_PYTHON_VERSION MATCHES None|NONE )
        string(REPLACE "\"" "" _PYTHON_VERSION ${_PAR_WHEEL_PYTHON_VERSION})
        list( APPEND PIP_OPTIONS "--python-version=${_PYTHON_VERSION}" )
    endif()

    # We use a dry-run installation to check if all dependencies have already been downloaded
    execute_process(
        COMMAND
            ${Python3_EXECUTABLE} -m pip install
                --dry-run --break-system-packages
                --no-index --find-links "${WHEELS_DIR}" --only-binary :all:
                ${PIP_OPTIONS}
                ${_PAR_REQUIREMENT_SPEC}
        OUTPUT_QUIET ERROR_QUIET
        RESULT_VARIABLE _RET_VAL
    )

    if( "${_RET_VAL}" EQUAL "0" )

        message( STATUS "All dependency wheels for ${_PAR_REQUIREMENT_SPEC} found in cache" )

    else()

        message( STATUS "Downloading dependency wheels for ${_PAR_REQUIREMENT_SPEC} to ${WHEELS_DIR}" )

        # Download build dependencies separately, since these aren't automatically recongnized by pip
        execute_process(
            COMMAND
                ${Python3_EXECUTABLE} -m pip download
                --disable-pip-version-check --only-binary :all: --dest "${WHEELS_DIR}"
                ${PIP_OPTIONS}
                setuptools>=75.0.0,<80.10.0 wheel setuptools_scm[toml]>=6.2,<9.3
            OUTPUT_QUIET
            RESULT_VARIABLE _RET_VAL
        )

        if( NOT "${_RET_VAL}" EQUAL "0" )
            message( FATAL_ERROR "Download build dependency wheels for ${_PAR_REQUIREMENT_SPEC} to ${WHEELS_DIR} failed" )
        endif()

        # Download dependencies for the specified REQUIREMENT_SPEC
        execute_process(
            COMMAND
                ${Python3_EXECUTABLE} -m pip download
                --disable-pip-version-check --only-binary :all: --dest "${WHEELS_DIR}"
                ${PIP_OPTIONS}
                ${_PAR_REQUIREMENT_SPEC}
            OUTPUT_QUIET
            RESULT_VARIABLE _RET_VAL
        )

        if( NOT "${_RET_VAL}" EQUAL "0" )
            message( FATAL_ERROR "Download dependency wheels for ${_PAR_REQUIREMENT_SPEC} to ${WHEELS_DIR} failed" )
        endif()

    endif()

endfunction()

download_python_wheels( REQUIREMENT_SPEC     ${REQUIREMENT_SPEC}
                        WHEELS_DIR           ${WHEELS_DIR}
                        WHEEL_ARCH           ${IFSBENCH_WHEEL_ARCH}
                        WHEEL_PYTHON_VERSION ${IFSBENCH_WHEEL_PYTHON_VERSION} )
