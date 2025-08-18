#!/usr/bin/env python3

# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
import tempfile
import click

from ifsbench import (
    cli, header, debug, ExperimentFiles,
    DarshanReport, read_files_from_darshan, write_files_from_darshan
)


@cli.command()
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for packed files (default: current working directy)')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=False,
              help='Verify checksum of files listed in YAML files (default: disabled)')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
def pack_ifsdata(output_dir, verify_checksum, inputs):
    """
    Create a tarball with ifsdata files for (multiple) YAML files from
    pack-experiment

    INPUTS is one or multiple <exp_id>.yml files.

    Note that checksum verification is disabled by default for this command
    because experiment-specific files mentioned in YAML files are possibly
    already cleaned up.
    """
    ifsdata_files = ExperimentFiles('ifsdata')
    for summary_file in inputs:
        header('Reading %s...', str(summary_file))
        exp_files = ExperimentFiles.from_yaml(summary_file, verify_checksum=verify_checksum)
        ifsdata_files.add_input_file(*exp_files.ifsdata_files)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ifsdata_files.to_tarball(output_dir, with_ifsdata=True)


@cli.command()
@click.option('--input-dir', default=Path.cwd(),
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
              help='Input directory for ifsdata tarball (default: current working directory)')
@click.option('--output-dir', default=Path.cwd(), type=click.Path(file_okay=False, dir_okay=True),
              help='Output directory for unpacked files (default: current working directory)')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
              help='Verify checksum of unpacked files (default: enabled)')
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
def unpack_ifsdata(input_dir, output_dir, verify_checksum, inputs):
    """
    Read YAML files produced by pack-experiment and unpack and verify
    corresponding ifsdata files

    INPUTS can be one or multiple <exp_id>.yml.
    """
    # Build ifsdata YAML file
    ifsdata_files = ExperimentFiles('ifsdata')
    for summary_file in inputs:
        header('Reading %s...', str(summary_file))
        exp_files = ExperimentFiles.from_yaml(summary_file, verify_checksum=False)
        ifsdata_files.add_input_file(*exp_files.ifsdata_files)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='ifsbench') as tmp_dir:
        ifsdata_yaml = Path(tmp_dir)/'ifsdata.yml'
        ifsdata_files.to_yaml(ifsdata_yaml)

        # Extract all ifsdata files
        ExperimentFiles.from_tarball(ifsdata_yaml, input_dir, output_dir, ifsdata_dir=output_dir,
                                     with_ifsdata=True, verify_checksum=verify_checksum)


@cli.command()
@click.option('--exp-id', required=True, type=str, help='ID of the experiment')
@click.option('--darshan-log', required=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
              help='Darshan logfile (produced by Darshan during execution)')
@click.option('--input-dir', required=True, multiple=True,
              type=click.Path(file_okay=False, dir_okay=True, readable=True),
              help=('Data directory relative to which input files are searched. '
                    'To use files from different directories this can be given more than once.'))
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for tarballs (default: current working directory)')
@click.option('--with-ifsdata/--without-ifsdata', default=False, type=bool,
               help=('Pack files in ifsdata (default: capture only in <exp_id>.yml '
                     'for later packaging with pack-ifsdata)'))
def pack_experiment(exp_id, darshan_log, input_dir, output_dir, with_ifsdata):
    """Pack input files of an experiment for standalone use"""

    # Parse the darshan report
    header('Reading Darshan report %s', darshan_log)
    report = DarshanReport(darshan_log)
    read_files = read_files_from_darshan(report)
    write_files = write_files_from_darshan(report)

    # Hack: we need to remove namelists from write_files because for unknown reasons
    # Darshan reports sometimes a single write on these files for ioserver ranks.
    # Once this behaviour is resolved, this can be removed in the future
    namelist_names = {'namelist', 'namelistfc', 'namelist_ice', 'wam_namelist',
                      'namnemowamcoup.in', 'namnemocoup.in', 'fort.4'}
    namelists_in_write_files = {f for f in write_files if Path(f).name in namelist_names}
    write_files -= namelists_in_write_files

    input_files = read_files - write_files
    header('Identified %d input files', len(input_files))

    for f in input_files:
        debug('  %s', f)

    # Create input files overview
    exp_files = ExperimentFiles(exp_id, src_dir=input_dir)
    exp_files.add_file(*input_files)

    # Setup output directory
    output_dir = Path(output_dir)/exp_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write input files summary
    summary_yml = output_dir/f"{exp_id}.yml"
    header('Creating summary file %s', str(summary_yml))
    exp_files.to_yaml(summary_yml)

    # Pack experiment files
    exp_files.to_tarball(output_dir, with_ifsdata=with_ifsdata)


@cli.command()
@click.option('--input-dir', default=[Path.cwd()], multiple=True,
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help=('Input directory for tarballs (default: current working directory). '
                    'Can be given multiple times.'))
@click.option('--output-dir', default=Path.cwd(),
              type=click.Path(file_okay=False, dir_okay=True, writable=True),
              help='Output directory for unpacked files (default: current working directory).')
@click.option('--verify-checksum/--no-verify-checksum', type=bool, default=True,
              help='Verify checksum of unpacked files (default: enabled)')
@click.option('--with-ifsdata/--without-ifsdata', type=bool, default=False,
              help='Unpack ifsdata archives (default: disabled)')
@click.option('--ifsdata-input-dir', default=None, type=click.Path(file_okay=False, dir_okay=True),
              help='Use a different input directory for joint ifsdata tarball.')
@click.option('--ifsdata-dir', default=None, type=click.Path(file_okay=False, dir_okay=True),
              help=('Directory for ifsdata files (pre-existing or when --with-ifsdata '
                    'is enabled, it will extract files there). Defaults to --output-dir.'))
@click.argument('inputs', required=True, nargs=-1,
                type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.pass_context
def unpack_experiment(ctx, input_dir, output_dir, verify_checksum, with_ifsdata,
                      ifsdata_input_dir, ifsdata_dir, inputs):
    """
    Read yaml-files produced by pack-experiment and unpack all
    corresponding archives

    INPUTS can be one or multiple <exp_id>.yml files.
    """
    # Set-up output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if ifsdata_dir is None:
        ifsdata_dir = output_dir
    else:
        ifsdata_output_dir = Path(ifsdata_dir)
        ifsdata_output_dir.mkdir(parents=True, exist_ok=True)

    # Unpack ifsdata files if asked for different directory
    if with_ifsdata and ifsdata_input_dir is not None:
        ctx.invoke(unpack_ifsdata, input_dir=ifsdata_input_dir, output_dir=ifsdata_dir,
                   verify_checksum=verify_checksum, inputs=inputs)

    # Unpack all files
    inplace_ifsdata = with_ifsdata and ifsdata_input_dir is None
    for summary_file in inputs:
        header('Reading %s...', summary_file)
        ExperimentFiles.from_tarball(summary_file, input_dir, output_dir, ifsdata_dir=ifsdata_dir,
                                     with_ifsdata=inplace_ifsdata, verify_checksum=verify_checksum)


if __name__ == "__main__":
    cli(obj={})  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
