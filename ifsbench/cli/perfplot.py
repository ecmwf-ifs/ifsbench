# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Plotting utility entry point for performance data plotting.
"""

import click

from ifsbench import DrHookRecord
from ifsbench.plot import GroupedBarPlot
from ifsbench.logging import logger, DEBUG


preset_cpu_fused_ecphys = {
    'Turbulence': 'CALLPAR_TURB',
    'Convection': 'CALLPAR_CONV',
    'Cloud': 'CALLPAR_CLOUD',
}

preset_gpu_ecphys = {
    'Turbulence': 'TURBULENCE_LAYER_LOKI',
    'Convection': 'CONVECTION_LAYER_LOKI',
    'Cloud': 'CLOUD_LAYER_LOKI',
}


@click.group()
def perfplot():
    pass


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
