# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

##############################################################################
#.rst:
#
# ifsbench_find_executables
# =========================
#
# Find ifsbench executable scripts and make them available as imported targets. ::
#
#   ifsbench_find_executables()
#
##############################################################################

macro( ifsbench_find_executables )

    ecbuild_debug( "IFSBENCH_EXECUTABLES=${IFSBENCH_EXECUTABLES}" )

    # Create a bin directory in the install location and add the Python binaries
    # as a quasi-symlink.
    install( CODE "
        file( MAKE_DIRECTORY \"\${CMAKE_INSTALL_PREFIX}/bin\" )
    " )

    # Make CLI executables available in add_custom_command by setting
    # their location to the virtual environment's bin folder.
    foreach( _exe_name IN LISTS IFSBENCH_EXECUTABLES )
        if( NOT TARGET ${_exe_name} )
            add_executable( ${_exe_name} IMPORTED GLOBAL )
            set_property( TARGET ${_exe_name} PROPERTY IMPORTED_LOCATION ${Python3_VENV_BIN}/${_exe_name} )
            ecbuild_debug( "Adding executable ${_exe_name} from ${Python3_VENV_BIN}/${_exe_name}" )
        endif()

        # Create symlinks for frontend scripts when installing ifsbench.
        install( CODE "
            file( REAL_PATH \${CMAKE_INSTALL_PREFIX}/var/${Python3_VENV_NAME}/bin _venv_bin )
            file( CREATE_LINK
                \${_venv_bin}/${_exe_name}
                \${CMAKE_INSTALL_PREFIX}/bin/${_exe_name}
                SYMBOLIC
            )
        " )
    endforeach()

endmacro()
