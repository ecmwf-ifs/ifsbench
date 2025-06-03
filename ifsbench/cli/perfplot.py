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


def config_from_yaml(path):
    """
    Read plot config from YAML file
    """
    with Path(path).open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def data_from_preset(drhook, preset, groups, do_sums=True):
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

            data.append( sum(val) if do_sums else val )
        else:
            warning(f'[Perfplot] Could not find group key {k} in preset')
            data.append( 0.0 )

    return data


@click.group()
def perfplot():
    pass


@perfplot.command('ecphys-stacked')
@click.option(
    '--config', '-c', type=click.Path(),
    help='Paths to plot configuration YAML file'
)
@click.option(
    '--output', '-o', default='plot.pdf', type=click.Path(),
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
def plot_ecphysics_stacked(config, output, cmap, verbose):
    """
    Plot EC-physics performance as a stacked barplot for comparing difference runs.
    """
    metric = 'avgTimeTotal'

    if verbose:
        logger.setLevel(DEBUG)

    config = config_from_yaml(config)

    groups = config['groups']

    groups += ['Other']
    plot = StackedBarPlot(groups, cmap=cmap, nruns=len(config['runs']))

    for run in config['runs']:
        label = run['label']
        path = Path(run['path'])
        preset = run['preset']

        drhook = DrHookRecord.from_raw(path)
        gstats = GStatsRecord.from_file(path)

        data = data_from_preset(drhook=drhook, preset=preset, groups=groups[:-1])

        # Add "other" as the difference to the EC_PHYS gstats label
        data += [gstats.total_ecphys - sum(data)]

        plot.add_stack(data, label=label)

    plot.plot(filename=output)


@perfplot.command('ecphys-detail')
@click.option(
    '--config', '-c', type=click.Path(),
    help='Paths to plot configuration YAML file'
)
@click.option(
    '--output', '-o', default='plot.pdf', type=click.Path(),
    help='Filename of the output plot'
)
@click.option(
    '--verbose', '-v', is_flag=True, default=False,
    help='Enable verbose (debugging) output.'
)
def plot_ecphysics_compare(config, output, verbose):
    """
    Plot the EC-physics performance breakdown per component.
    """
    metric = 'avgTimeTotal'

    if verbose:
        logger.setLevel(DEBUG)

    config = config_from_yaml(config)
    groups = config['groups']

    plot = GroupedBarPlot(groups=groups, figsize=(12,7))

    for run in config['runs']:
        label = run['label']
        path = Path(run['path'])
        preset = run['preset']

        drhook = DrHookRecord.from_raw(path)
        gstats = GStatsRecord.from_file(path)

        data = data_from_preset(drhook=drhook, preset=preset, groups=groups, do_sums=False)

        plot.add_group(data, label=label)

    plot.plot(filename=output)
