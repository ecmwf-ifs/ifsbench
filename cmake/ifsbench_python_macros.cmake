# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

##############################################################################
#.rst:
#
# ifsbench_find_python_venv
# =========================
#
# Call ``find_package( Python3 )``, making sure to discover a specific
# virtual environment at the given location ``VENV_PATH``::
#
#   ifsbench_find_python_venv( VENV_PATH <path> [ PYTHON_VERSION <version str> ] )
#
##############################################################################

function( ifsbench_find_python_venv )

    set( options "" )
    set( oneValueArgs VENV_PATH PYTHON_VERSION )
    set( multiValueArgs "" )

    cmake_parse_arguments( _PAR "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )

    if( _PAR_UNPARSED_ARGUMENTS )
        message( FATAL_ERROR "Unknown keywords given to ifsbench_find_python_venv(): \"${_PAR_UNPARSED_ARGUMENTS}\"" )
    endif()

    if( NOT _PAR_VENV_PATH )
        message( FATAL_ERROR "No VENV_PATH provided to ifsbench_find_python_venv()" )
    endif()

    # Update the environment with VIRTUAL_ENV variable (mimic the activate script)
    set( ENV{VIRTUAL_ENV} "${_PAR_VENV_PATH}" )

    # Change the context of the search to only find the venv
    set( Python3_FIND_VIRTUALENV ONLY )

    # Python3_EXECUTABLE is also an input variable. Set it explicitly because
    # super-builds may already have a system interpreter cached from another project.
    # see https://cmake.org/cmake/help/latest/module/FindPython.html#artifacts-specification
    set( Python3_EXECUTABLE "${_PAR_VENV_PATH}/bin/python3" )
    # To allow cmake to discover the newly created venv if Python3_ROOT_DIR
    # was passed as an argument at build-time
    set( Python3_ROOT_DIR "${_PAR_VENV_PATH}" )

    # Launch a new search
    find_package( Python3 ${_PAR_PYTHON_VERSION} COMPONENTS Interpreter REQUIRED )

    cmake_path( IS_PREFIX _PAR_VENV_PATH "${Python3_EXECUTABLE}" NORMALIZE _IS_VENV_INTERPRETER )
    if( NOT _IS_VENV_INTERPRETER )
        ecbuild_error( "The discovered Python interpreter is not within the virtual environment" )
    endif()

    # Find the binary directory of the virtual environment
    execute_process(
        COMMAND ${Python3_EXECUTABLE} -c "import sys; import os.path; print(os.path.dirname(sys.executable), end='')"
        OUTPUT_VARIABLE Python3_VENV_BIN
    )

    # Forward variables to parent scope
    foreach ( _VAR_NAME Python3_FOUND Python3_EXECUTABLE Python3_VENV_BIN )
        set( ${_VAR_NAME} ${${_VAR_NAME}} PARENT_SCOPE )
    endforeach()

endfunction()

##############################################################################
#.rst:
#
# ifsbench_create_python_venv
# ===========================
#
# Discover a Python 3 interpreter and create a virtual environment at the
# specified location ``VENV_PATH``. ::
#
#   ifsbench_create_python_venv( VENV_PATH <path> [ PYTHON_VERSION <version str> ] [ INSTALL_VENV ] )
#
##############################################################################

function( ifsbench_create_python_venv )

    set( options INSTALL_VENV )
    set( oneValueArgs VENV_NAME PYTHON_VERSION )
    set( multiValueArgs "" )

    cmake_parse_arguments( _PAR "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )

    if( _PAR_UNPARSED_ARGUMENTS )
        message( FATAL_ERROR "Unknown keywords given to ifsbench_create_python_venv(): \"${_PAR_UNPARSED_ARGUMENTS}\"" )
    endif()

    if( NOT _PAR_VENV_NAME )
        message( FATAL_ERROR "No VENV_NAME provided to ifsbench_create_python_venv()" )
    endif()

    set( VENV_PATH "${CMAKE_CURRENT_BINARY_DIR}/${_PAR_VENV_NAME}" )

    # Discover only system install Python 3
    set( Python3_FIND_VIRTUALENV STANDARD )
    find_package( Python3 ${_PAR_PYTHON_VERSION} COMPONENTS Interpreter REQUIRED )

    # Ensure the activate scripts are writable in case the venv exists already
    file( GLOB activate_SCRIPTS "${VENV_PATH}/bin/activate*" )
    file( GLOB Activate_SCRIPTS "${VENV_PATH}/bin/Activate*" )
    foreach( _SCRIPT ${activate_SCRIPTS} ${Activate_SCRIPTS} )
        if( EXISTS "${_SCRIPT}" )
            message( STATUS "Making activate script ${_SCRIPT} writable" )
            file( CHMOD "${_SCRIPT}" FILE_PERMISSIONS OWNER_READ OWNER_WRITE )
        endif()
    endforeach()

    # Create a virtualenv
    message( STATUS "Create Python virtual environment ${VENV_PATH}" )
    execute_process( COMMAND ${Python3_EXECUTABLE} -m venv "${VENV_PATH}" COMMAND_ERROR_IS_FATAL ANY )
    set( Python3_VENV_NAME "${_PAR_VENV_NAME}" PARENT_SCOPE )

    # Upon installation, we create an equivalent Python venv in the installation directory
    if( _PAR_INSTALL_VENV )
        install(
            CODE
                "execute_process( COMMAND ${Python3_EXECUTABLE} -m venv \${CMAKE_INSTALL_PREFIX}/var/${_PAR_VENV_NAME} RESULT_VARIABLE _RET )"
        )
        set( Python3_INSTALL_VENV TRUE PARENT_SCOPE )
    endif()

endfunction()

##############################################################################
#.rst:
#
# ifsbench_setup_python_venv
# ==========================
#
# Find Python 3, create a virtual environment and make it available. ::
#
#   ifsbench_setup_python_venv( VENV_PATH <path> [ PYTHON_VERSION <version str> ] [ INSTALL_VENV ] )
#
# It combines calls to ``ifsbench_create_python_venv`` and ``ifsbench_find_python_venv``
#
##############################################################################

function( ifsbench_setup_python_venv )

    set( options INSTALL_VENV )
    set( oneValueArgs VENV_NAME PYTHON_VERSION )
    set( multiValueArgs "" )

    cmake_parse_arguments( _PAR "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )

    if( _PAR_UNPARSED_ARGUMENTS )
        message( FATAL_ERROR "Unknown keywords given to ifsbench_setup_python_venv(): \"${_PAR_UNPARSED_ARGUMENTS}\"" )
    endif()

    if( NOT _PAR_VENV_NAME )
        message( FATAL_ERROR "No VENV_NAME provided to ifsbench_setup_python_venv()" )
    endif()

    # Create the virtual environment
    set( _ARGS VENV_NAME "${_PAR_VENV_NAME}" )
    if( _PAR_PYTHON_VERSION )
        list( APPEND _ARGS PYTHON_VERSION "${_PAR_PYTHON_VERSION}" )
    endif()
    if( _PAR_INSTALL_VENV )
        list( APPEND _ARGS INSTALL_VENV )
    endif()

    ifsbench_create_python_venv( ${_ARGS} )

    set( Python3_VENV_NAME "${Python3_VENV_NAME}" PARENT_SCOPE )
    if( DEFINED Python3_INSTALL_VENV )
        set( Python3_INSTALL_VENV "${Python3_INSTALL_VENV}" PARENT_SCOPE )
    endif()

    # Discover Python in the virtual environment and set-up variables
    set( _ARGS VENV_PATH "${CMAKE_CURRENT_BINARY_DIR}/${_PAR_VENV_NAME}" )
    if( _PAR_PYTHON_VERSION )
        list( APPEND _ARGS PYTHON_VERSION "${_PAR_PYTHON_VERSION}" )
    endif()
    ifsbench_find_python_venv( ${_ARGS} )

    foreach ( _VAR_NAME Python3_FOUND Python3_EXECUTABLE Python3_VENV_BIN )
        set( ${_VAR_NAME} ${${_VAR_NAME}} PARENT_SCOPE )
    endforeach()

endfunction()

##############################################################################
#.rst:
#
# ifsbench_download_python_wheels
# ===============================
#
# Download all dependencies for the given ``REQUIREMENT_SPEC`` and cache them in a
# wheelhouse at ``WHEELS_DIR``
#
##############################################################################

function( ifsbench_download_python_wheels )

    set( options "" )
    set( oneValueArgs REQUIREMENT_SPEC WHEELS_DIR WHEEL_ARCH WHEEL_PYTHON_VERSION PYTHON_VERSION )
    set( multiValueArgs "" )

    cmake_parse_arguments( _PAR "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )

    if( _PAR_UNPARSED_ARGUMENTS )
        message( FATAL_ERROR "Unknown keywords given to ifsbench_download_python_wheels(): \"${_PAR_UNPARSED_ARGUMENTS}\"" )
    endif()

    if( NOT _PAR_REQUIREMENT_SPEC )
        message( FATAL_ERROR "No REQUIREMENT_SPEC provided to ifsbench_download_python_wheels()" )
    endif()

    message( STATUS "Checking for cached wheels in ${WHEELS_DIR}" )

    # Check for a suitable python interpreter
    find_package( Python3 ${_PAR_PYTHON_VERSION} COMPONENTS Interpreter REQUIRED QUIET )

    execute_process(
        COMMAND ${Python3_EXECUTABLE} -m ensurepip --upgrade
        OUTPUT_QUIET ERROR_QUIET
    )

    # If no wheelhouse dir is given, create one in the current binary directory
    if( _PAR_WHEELS_DIR )
        set( WHEELS_DIR "${_PAR_WHEELS_DIR}" )
    else()
        set( WHEELS_DIR "${CMAKE_CURRENT_BINARY_DIR}/wheelhouse" )
    endif()
    file( MAKE_DIRECTORY "${WHEELS_DIR}" )

    unset( PIP_OPTIONS )
    if( DEFINED _PAR_WHEEL_ARCH AND NOT _PAR_WHEEL_ARCH MATCHES None|NONE )
        # PIP does not recognize the Python version anymore if it is enclosed
        # by quotes, thus we need to strip any spurious quotes from the version
        string( REPLACE "\"" "" _ARCH ${_PAR_WHEEL_ARCH} )
       list( APPEND PIP_OPTIONS --platform=${_ARCH} )
    endif()
    if( DEFINED _PAR_WHEEL_PYTHON_VERSION AND NOT _PAR_WHEEL_PYTHON_VERSION MATCHES None|NONE )
        # PIP does not recognize the Python version anymore if it is enclosed
        # by quotes, thus we need to strip any spurious quotes from the version
        string( REPLACE "\"" "" _PYTHON_VERSION ${_PAR_WHEEL_PYTHON_VERSION} )
        list( APPEND PIP_OPTIONS --python-version=${_PYTHON_VERSION} )
    endif()
    if( PIP_OPTIONS )
        list( APPEND PIP_OPTIONS --no-deps )
    endif()

    # We use a dry-run installation to check if all dependencies have already been downloaded
    set( _CMD
        ${Python3_EXECUTABLE} -m pip install
            --dry-run --break-system-packages
            --no-index --find-links "${WHEELS_DIR}" --only-binary :all:
            ${PIP_OPTIONS} ${_PAR_REQUIREMENT_SPEC}
    )
    execute_process(
        COMMAND ${_CMD}
        OUTPUT_QUIET ERROR_QUIET
        RESULT_VARIABLE _RET_VAL
    )

    if( "${_RET_VAL}" EQUAL "0" )

        message( STATUS "All dependency wheels for ${_PAR_REQUIREMENT_SPEC} found in cache" )

    else()

        message( STATUS "Downloading dependency wheels for ${_PAR_REQUIREMENT_SPEC} to ${WHEELS_DIR}" )

        # Download typical build dependencies for wheels. Keep setuptools in
        # sync with ifsbench's pyproject.toml build-system constraints.
        set( _CMD
            ${Python3_EXECUTABLE} -m pip download
            --disable-pip-version-check --dest "${WHEELS_DIR}"
            ${PIP_OPTIONS} setuptools>=75.0.0,<80.10.0 wheel setuptools_scm[toml]>=6.2,<9.3
        )
        execute_process(
            COMMAND ${_CMD}
            COMMAND_ERROR_IS_FATAL ANY
            OUTPUT_QUIET
        )

        # Download dependencies for the specified REQUIREMENT_SPEC
        set( _CMD
            ${Python3_EXECUTABLE} -m pip download
            --disable-pip-version-check --dest "${WHEELS_DIR}"
            ${PIP_OPTIONS} ${_PAR_REQUIREMENT_SPEC}
        )
        execute_process(
            COMMAND ${_CMD}
            COMMAND_ERROR_IS_FATAL ANY
            OUTPUT_QUIET
        )

        execute_process(
            COMMAND
                ${Python3_EXECUTABLE} -m pip wheel
                    --disable-pip-version-check --wheel-dir "${WHEELS_DIR}"
                    ${_PAR_REQUIREMENT_SPEC}
            COMMAND_ERROR_IS_FATAL ANY
            OUTPUT_QUIET
        )

    endif()

endfunction()

##############################################################################
#.rst:
#
# ifsbench_build_python_wheels
# ============================
#
# Build a Python wheel for the given ``REQUIREMENT_SPEC`` and store it in the
# specified ``BUILD_DIR``.
#
##############################################################################

function( ifsbench_build_python_wheels )

    set( options "" )
    set( oneValueArgs REQUIREMENT_SPEC WHEELS_DIR BUILD_DIR PYTHON_VERSION )
    set( multiValueArgs "" )

    cmake_parse_arguments( _PAR "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )

    if( _PAR_UNPARSED_ARGUMENTS )
        message( FATAL_ERROR "Unknown keywords given to ifsbench_build_python_wheels(): \"${_PAR_UNPARSED_ARGUMENTS}\"" )
    endif()

    if( NOT _PAR_REQUIREMENT_SPEC )
        message( FATAL_ERROR "No REQUIREMENT_SPEC provided to ifsbench_build_python_wheels()" )
    endif()

    message( STATUS "Building wheel for ${_PAR_REQUIREMENT_SPEC}" )

    # Check for a suitable python interpreter
    find_package( Python3 ${_PAR_PYTHON_VERSION} COMPONENTS Interpreter REQUIRED QUIET )
    # If no build dir is given, create one in the current binary directory
    if( _PAR_BUILD_DIR )
        set( BUILD_DIR "${_PAR_BUILD_DIR}" )
    else()
        set( BUILD_DIR "${CMAKE_CURRENT_BINARY_DIR}/wheelhouse" )
    endif()
    file( MAKE_DIRECTORY "${BUILD_DIR}" )

    # If no wheelhouse is given, use the build directory
    if( _PAR_WHEELS_DIR )
        set( WHEELS_DIR "${_PAR_WHEELS_DIR}" )
    else()
        set( WHEELS_DIR "${BUILD_DIR}" )
    endif()
    file( MAKE_DIRECTORY "${WHEELS_DIR}" )

    execute_process(
        COMMAND
            ${Python3_EXECUTABLE} -m pip wheel
                --no-index --find-links "${WHEELS_DIR}" --wheel-dir "${BUILD_DIR}"
                ${_PAR_REQUIREMENT_SPEC}
    )

endfunction()

##############################################################################
#.rst:
#
# ifsbench_install_python_package
# ===============================
#
# Install a Python package using the provided ``REQUIREMENT_SPEC``.
#
#   ifsbench_install_python_package( REQUIREMENT_SPEC <spec> [ WHEELS_DIR <path> ] [ EDITABLE ] )
#
##############################################################################
function( ifsbench_install_python_package )

    set( options EDITABLE )
    set( oneValueArgs REQUIREMENT_SPEC WHEELS_DIR PYTHON_VERSION )
    set( multiValueArgs "" )

    cmake_parse_arguments( _PAR "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN} )

    if( _PAR_UNPARSED_ARGUMENTS )
        message( FATAL_ERROR "Unknown keywords given to ifsbench_install_python_package(): \"${_PAR_UNPARSED_ARGUMENTS}\"" )
    endif()

    if( NOT _PAR_REQUIREMENT_SPEC )
        message( FATAL_ERROR "No REQUIREMENT_SPEC provided to ifsbench_install_python_package()" )
    endif()

    # Check for a suitable python interpreter
    find_package( Python3 ${_PAR_PYTHON_VERSION} COMPONENTS Interpreter REQUIRED QUIET )

    if( _PAR_WHEELS_DIR )
        # Force installation from provided wheelhouse
        set( INSTALL_OPTS --no-index "--find-links=${_PAR_WHEELS_DIR}" )
    else()
        # Default pip install
        set( INSTALL_OPTS --disable-pip-version-check )
    endif()

    if( _PAR_EDITABLE )
        set( INSTALL_OPTS ${INSTALL_OPTS} -e )
    endif()

    message( STATUS "Installing Python package ${_PAR_REQUIREMENT_SPEC}" )

    set( OUTPUT_OPTIONS OUTPUT_VARIABLE _OUTPUT ERROR_VARIABLE _OUTPUT )
    if( ${CMAKE_VERBOSE_MAKEFILE} )
        list(
            APPEND
                OUTPUT_OPTIONS
            ECHO_OUTPUT_VARIABLE
            ECHO_ERROR_VARIABLE
            COMMAND_ECHO STDOUT
        )
    endif()

    # Install package
    execute_process(
        COMMAND ${Python3_EXECUTABLE} -m pip install ${INSTALL_OPTS} ${_PAR_REQUIREMENT_SPEC}
        COMMAND_ERROR_IS_FATAL ANY
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        ${OUTPUT_OPTIONS}
    )

    # Upon installation, repeat the installation
    if( Python3_INSTALL_VENV )
        if( DEFINED ENV{SETUPTOOLS_SCM_PRETEND_VERSION} )
            install(CODE "set( ENV{SETUPTOOLS_SCM_PRETEND_VERSION} $ENV{SETUPTOOLS_SCM_PRETEND_VERSION})")
        endif()
        install(
            CODE
                "execute_process( COMMAND \${CMAKE_INSTALL_PREFIX}/var/${Python3_VENV_NAME}/bin/python -m pip install ${INSTALL_OPTS} ${_PAR_REQUIREMENT_SPEC} COMMAND_ERROR_IS_FATAL ANY )"
        )
    endif()

endfunction()
