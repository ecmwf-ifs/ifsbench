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

from ifsbench import DrHookRecord, GStatsRecord
from ifsbench.plot import GroupedBarPlot, StackedBarPlot
from ifsbench.logging import logger, DEBUG


preset_cpu_fused_ecphys = {
    'Init': 'EC_PHYS_DRV_FIELD_INIT',
    'Pre': 'EC_PHYS_DRV_PRE',
    'Pre2': 'EC_PHYS_PRE',
    'Pre3': 'CALLPAR_PRE',
    'Rad Trans': 'CALLPAR_RADTRANS',
    'Turbulence': 'CALLPAR_TURB',
    'Convection': 'CALLPAR_CONV',
    'Cloud': 'CALLPAR_CLOUD',
    'WMS': 'CALLPAR_WMS',
    'Diag': 'CALLPAR_DIAG_CTV',
    'Chem': 'CALLPAR_CHEM',
    'Rad Vis': 'CALLPAR_RADVIS',
    'Surface': 'CALLPAR_SURFTS',
    'Ozone': 'CALLPAR_O3CHEM',
    'SLPhy': 'CALLPAR_SLPHY',
    'Post1': 'CALLPAR_POST',
    'Post2': 'EC_PHYS_POST',
    'Deallo': 'EC_PHYS_DRV_DEALLO',
}

preset_cpu_fused_ecphys2 = {
    'Init': lambda d: d.get('EC_PHYS_DRV_FIELD_INIT'),
    'Pre': lambda d: sum(d.get(['EC_PHYS_DRV_PRE', 'EC_PHYS_PRE', 'CALLPAR_PRE'])),
    'Rad Trans': lambda d: d.get('CALLPAR_RADTRANS'),
    'Turbulence': lambda d: d.get('CALLPAR_TURB'),
    'Convection': lambda d: d.get('CALLPAR_CONV'),
    'Cloud': lambda d: d.get('CALLPAR_CLOUD'),
    'WMS': lambda d: d.get('CALLPAR_WMS'),
    'Diag': lambda d: d.get('CALLPAR_DIAG_CTV'),
    'Chem': lambda d: d.get('CALLPAR_CHEM'),
    'Rad Vis': lambda d: d.get('CALLPAR_RADVIS'),
    'Surface': lambda d: d.get('CALLPAR_SURFTS'),
    'Ozone': lambda d: d.get('CALLPAR_O3CHEM'),
    'SLPhy': lambda d: d.get('CALLPAR_SLPHY'),
    'Post': lambda d: sum(d.get(['CALLPAR_POST', 'EC_PHYS_POST', 'EC_PHYS_DRV_DEALLO'])),
}

preset_gpu_ecphys = {
    'Init': 'ECPHYS_FIELD_INIT',
    'Pre': 'EC_PHYS_FC_PRE',
    'Rad Trans': 'EC_PHYS_FC_RADTRANS',
    'Turbulence': 'TURBULENCE_LAYER_LOKI',
    'Convection': 'CONVECTION_LAYER_LOKI',
    'Cloud': 'CLOUD_LAYER_LOKI',
    'WMS': 'EC_PHYS_FC_WMS',
    'Diag': 'EC_PHYS_FC_DIAG_CTV',
    'Chem' : 'EC_PHYS_FC_CHEM',
    # 'Chem + Rad Vis' : 'EC_PHYS_FC_CHEM',
    'Surface': 'EC_PHYS_FC_SURFTS',
    'Ozone': 'EC_PHYS_FC_O3CHEM',
    'SLPhy': 'EC_PHYS_FC_SLPHY',
    # 'SLPhy + Qnegat': 'EC_PHYS_FC_SLPHY',
    'Post1': 'EC_PHYS_FC_POST',
    'Post2': 'EC_PHYS_FC_POST2',
    'Deallo': 'EC_PHYS_FC_DEALLO',
    'Pullback': 'EC_PHYS_FC_PULLBACK',
    'Mem-save PB': 'CONVECTION_PULLBACK',
}

preset_gpu_ecphys2 = {
    'Init': lambda d: d.get('ECPHYS_FIELD_INIT'),
    'Pre': lambda d: d.get('EC_PHYS_FC_PRE'),
    'Rad Trans': lambda d: d.get('EC_PHYS_FC_RADTRANS'),
    'Turbulence': lambda d: sum(d.get(['GWDRAG_LAYER_LOKI', 'TURBULENCE_LAYER_LOKI'])),
    'Convection': lambda d: d.get('CONVECTION_LAYER_LOKI'),
    'Cloud': lambda d: d.get('CLOUD_LAYER_LOKI'),
    'WMS': lambda d: d.get('EC_PHYS_FC_WMS'),
    'Diag': lambda d: d.get('EC_PHYS_FC_DIAG_CTV'),
    'Chem' : lambda d: d.get('EC_PHYS_FC_CHEM'),
    # 'Chem + Rad Vis' : 'EC_PHYS_FC_CHEM',
    'Surface': lambda d: d.get('EC_PHYS_FC_SURFTS'),
    'Ozone': lambda d: d.get('EC_PHYS_FC_O3CHEM'),
    'SLPhy': lambda d: d.get('EC_PHYS_FC_SLPHY'),
    # 'SLPhy + Qnegat': 'EC_PHYS_FC_SLPHY',
    'Post': lambda d: sum(d.get(['EC_PHYS_FC_POST', 'EC_PHYS_FC_POST2', 'EC_PHYS_FC_DEALLO'])),
    # 'Post2': lambda d: d.get('EC_PHYS_FC_POST2'),
    # 'Deallo': lambda d: d.get('EC_PHYS_FC_DEALLO'),
    'Pullback': lambda d: d.get('EC_PHYS_FC_PULLBACK'),
    'Mem-save PB': lambda d: d.get('CONVECTION_PULLBACK'),
}


@click.group()
def perfplot():
    pass


@perfplot.command('ecphys-stacked')
@click.option(
    '--cpu-data', '-c', multiple=True, type=click.Path(),
    help='Paths to CPU data sets to add to bar plot'
)
@click.option(
    '--gpu-data', '-g', multiple=True, type=click.Path(),
    help='Paths to GPU data sets to add to bar plot'
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
def plot_ecphysics_stacked(cpu_data, gpu_data, output, cmap, verbose):
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

    for path in cpu_data:
        # preset = preset_cpu_fused_ecphys
        preset = preset_cpu_fused_ecphys2
        drhook = DrHookRecord.from_raw(path)
        gstats = GStatsRecord.from_file(path)

        # keys = [preset.get(k, 'N/A') for k in groups[:-1]]
        # data = drhook.get(keys, fill=0.0)
        data = [preset[k](drhook) if k in preset else 0. for k in groups[:-1]]

        # Add "other" as the difference to the EC_PHYS gstats label
        data += [gstats.total_ecphys - sum(data)]

        plot.add_stack(data, label='CPU-Fused')

        # from IPython import embed; embed()

    for path in gpu_data:
        preset = preset_gpu_ecphys2
        drhook = DrHookRecord.from_raw(path)
        gstats = GStatsRecord.from_file(path)

        # keys = [preset.get(k, 'NA') for k in groups[:-1]]
        # data = drhook.get(keys, fill=0.0)
        data = [preset[k](drhook) if k in preset else 0. for k in groups[:-1]]

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
