# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Plotting utility entry point for performance data plotting.
"""
from pathlib import Path

import click
import yaml

from ifsbench import DrHookRecord, GStatsRecord
from ifsbench.plot import GroupedBarPlot, StackedBarPlot
from ifsbench.logging import logger, DEBUG, warning


def preset_from_yaml(path):
    """
    Read "preset" mapping of group keys to DrHook timing labels
    """
    with Path(path).open(encoding='utf-8') as f:
        preset_map = yaml.safe_load(f)
    return preset_map


def data_from_preset(drhook, preset, groups):
    """
    Construct an array of timing values, summing any list of grouped keys.
    """

    data = []
    for k in groups:
        if lbl := preset.get(k):
            val = drhook.get(lbl, fill=0.)

            if isinstance(lbl, str):
                # Ensure lists from here
                val, lbl = [val], [lbl]

            for l, v in zip(lbl, val):
                if v == 0.:
                    warning(f'[Perfplot] Could not find label {l} in DR_HOOK timings')

            data.append( sum(val) )
        else:
            warning(f'[Perfplot] Could not find group key {k} in preset')
            data.append( 0.0 )

    return data


@click.group()
def perfplot():
    pass


@perfplot.command('ecphys-stacked')
@click.option(
    '--cpu-data', '-c', multiple=True, type=click.Path(),
    help='Paths to CPU data sets to add to bar plot'
)
@click.option(
    '--cpu-preset', '-cp', multiple=True, type=click.Path(),
    help='Paths to group preset definition YAML file'
)
@click.option(
    '--gpu-data', '-g', multiple=True, type=click.Path(),
    help='Paths to GPU data sets to add to bar plot'
)
@click.option(
    '--gpu-preset', '-gp', multiple=True, type=click.Path(),
    help='Paths to group preset definition YAML file'
)
@click.option(
    '--output', default='plot.pdf', type=click.Path(),
    help='Filename of the output plot'
)
@click.option(
    '--cmap', '-cm', default='viridis',
    help='Colormap to use for different component bars'
)
@click.option(
    '--verbose', '-v', is_flag=True, default=False,
    help='Enable verbose (debugging) output.'
)
def plot_ecphysics_stacked(cpu_data, cpu_preset, gpu_data, gpu_preset, output, cmap, verbose):
    """
    Plot EC-physics performance as a stacked barplot for comparing difference runs.
    """
    metric = 'avgTimeTotal'

    if verbose:
        logger.setLevel(DEBUG)

    groups = [
        'Init', 'Pre', 'Rad Trans', 'Turbulence', 'Convection', 'Cloud',
        'WMS', 'Diag', 'Chem', 'Rad Vis', 'Surface', 'Ozone', 'SLPhy', 'Pullback', 'Post',
    ]
    groups += ['Other']
    plot = StackedBarPlot(groups, cmap=cmap)

    for path, preset_path in zip(cpu_data, cpu_preset):
        drhook = DrHookRecord.from_raw(path)
        gstats = GStatsRecord.from_file(path)

        preset = preset_from_yaml(preset_path)

        data = data_from_preset(drhook=drhook, preset=preset, groups=groups[:-1])

        # Add "other" as the difference to the EC_PHYS gstats label
        data += [gstats.total_ecphys - sum(data)]

        plot.add_stack(data, label='CPU-Fused')

    for path, preset_path in zip(gpu_data, gpu_preset):

        drhook = DrHookRecord.from_raw(path)
        gstats = GStatsRecord.from_file(path)

        preset = preset_from_yaml(preset_path)

        data = data_from_preset(drhook=drhook, preset=preset, groups=groups[:-1])

        # Add "other" as the difference to the EC_PHYS gstats label
        data += [gstats.total_ecphys - sum(data)]

        plot.add_stack(data, label='GPU-Stack')

        # from IPython import embed; embed()

    plot.plot(filename=output)


@perfplot.command('ecphys-detail')
@click.option(
    '--cpu-data', '-c', multiple=True, type=click.Path(),
    help='Paths to CPU data sets to add to bar plot'
)
@click.option(
    '--gpu-data', '-g', multiple=True, type=click.Path(),
    help='Paths to GPU data sets to add to bar plot'
)
@click.option(
    '--output', '-o', default='plot.pdf', type=click.Path(),
    help='Filename of the output plot'
)
@click.option(
    '--verbose', '-v', is_flag=True, default=False,
    help='Enable verbose (debugging) output.'
)
def plot_ecphysics_compare(cpu_data, gpu_data, output, verbose):
    """
    Plot the EC-physics performance breakdown per component.
    """
    metric = 'avgTimeTotal'

    if verbose:
        logger.setLevel(DEBUG)

    groups = ['Turbulence', 'Convection', 'Cloud']
    plot = GroupedBarPlot(groups=groups)

    for path in cpu_data:
        preset = preset_cpu_fused_ecphys
        drhook = DrHookRecord.from_raw(path)
        data = drhook.get([preset[k] for k in groups], fill=0.0)
        plot.add_group(data, label='CPU-Fused')

    for path in gpu_data:
        preset = preset_gpu_ecphys
        drhook = DrHookRecord.from_raw(path)
        data = drhook.get([preset[k] for k in groups], fill=0.0)
        plot.add_group(data, label='GPU-Stack')

    plot.plot(filename=output)
