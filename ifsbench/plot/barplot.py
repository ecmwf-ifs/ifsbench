# (C) Copyright 2020- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from collections.abc import Iterable

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

from ifsbench.logging import debug, info


__all__ = ['GroupedBarPlot', 'StackedBarPlot']


class GroupedBarPlot:
    """
    A grouped bar plot that clusters individual bars by groups.

    Parameters
    ----------
    groups : list of str
        Names of the groups by which to cluster bars.
    """

    def __init__(self, groups, group_colors, nruns=2, figsize=(12,9)):
        self.groups = groups
        self.group_colors = group_colors
        self.x = np.arange(len(self.groups))

        self.fig, self.ax = plt.subplots(figsize=figsize, layout='constrained')
        self.figsize = figsize
        self.width = 1. / len(self.groups) * .9 * figsize[0] / nruns

        self.idx = 0

        info(f'[Perfplot] Creating GroupedBarPlot with {len(self.groups)} groups '
             f'[figsize={self.figsize}, width={self.width:.2f}]')

    def add_group(self, values, label, hatch_dic={'_': '', 'execute': '', 'offload': '//', 'setup': '\\'}):
        """
        Add a bar to each group for a given set of values.

        Parameters
        ----------
        values : list of float
            Values for the bar height for all group entries.
        label : str
            Label to appear in the legend for all entries
        """
        assert len(values) == len(self.groups)

        # Figure the max set of stacked values and create a filled matrix
        maxlen = max(len(v) if isinstance(v, (Iterable, dict)) else 1 for v in values)
        # 'unpack' the values dict
        _values = []
        for elem in values:
            nested_vals = []
            for key, val in elem.items():
                nested_vals.append(sum(val))
            _values.append(nested_vals)
        #
        values = _values
        fill_values = np.asarray([
            [v[i] if isinstance(v, Iterable) and len(v) > i else 0. for v in values]
            for i in range(maxlen)
        ])
        # Get the cumulative of the filled matrix, so we can get the previous "bottom"
        cum_values = np.asarray(
            [[sum(fill_values[:j+1,i]) for j in range(maxlen)] for i in range(len(values))]
        ).transpose()

        offset = self.width * self.idx
        color = None
        for i in range(maxlen):
            # Determine the previous from the cumulative sums
            prev = cum_values[i-1,:] if i >= 1 else [0. for _ in values]
            rects = self.ax.bar(
                self.x + offset, fill_values[i,:], bottom=prev,
                width=self.width# , label=label#, hatch=hatch[i] # , color=color
            )
            # Record most recent color so that we can keep it homogenous
            color = rects.patches[-1].get_facecolor()

        # Add max cumulative value as bar label
        self.ax.bar_label(rects, padding=3, labels=[f'{i:.2f}' for i in cum_values[-1,:]])

        self.idx += 1

    def plot(self, filename, title=None, ylabel=None, ylim=None):
        """
        Plot figure to file and configure labels and legends.

        Parameters
        ----------
        filename : str
            Path and name of output file.
        title : str, optional
            A title to add to the top of the plot.
        ylabel : str, optional
            Label for the y-axis
        ylim : tuple of float, optional
            Min and max value for the y-axis
        """
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.set_xticks(self.x + self.width, self.groups)
        self.ax.legend(loc='upper left', ncols=3)
        self.ax.set_ylim(ylim)

        plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)


class StackedBarPlot:
    """
    A stacked bar plot that clusters multiple bars in a stack for each x-entry.

    Parameters
    ----------
    groups : list of str
        Names of the groups by which to cluster bars.
    cmap : str, optional
        Name of the colormap to use, as defined in matplotlib.
    """

    def __init__(self, groups, group_colors=None, cmap='viridis', colors=None, figsize=(12,9), nruns=2):
        self.groups = groups
        self.group_colors = group_colors

        self.fig, self.ax = plt.subplots(figsize=figsize)
        self.nruns = nruns

        # Define and discretise colormap
        if colors is None:
            self.cmap = mpl.colormaps[cmap]
            self.colors = self.cmap(np.linspace(0, 1, len(groups)))
        else:
            self.colors = colors

    def add_stack(self, values, label, groups=None, text=False):
        """
        Add stacked bar data for defined groups from a single run.

        Parameters
        ----------
        values : list of float
            The run time values to stack for each bar column
        label : str
            Label for the x-axis of this entry
        """
        if groups is None:
            groups = self.groups

        assert len(values) == len(groups)

        total = 0.
        for i, v in enumerate(values):
            bar = plt.bar(label, v, bottom=total, label=groups[i], color=self.colors[i])
            total += v

        if text:
            yval = total # bar.get_height()
            plt.text(label, yval + 0.01 * yval, round(yval, 1), horizontalalignment='center') 

        debug(dict(zip(groups, values)))


    def add_group(self, values, label, hatch_dic={'_': '', 'execute': '', 'offload': '//', 'setup': '\\'}, colors=None, groups=None):
        """
        Add a bar to each group for a given set of values.

        Parameters
        ----------
        values : list of float
            Values for the bar height for all group entries.
        label : str
            Label to appear in the legend for all entries
        """

        groups = groups or self.groups
        assert len(values) == len(groups)

        _colors = self.group_colors

        # Figure the max set of stacked values and create a filled matrix
        maxlen = max(len(v) if isinstance(v, (Iterable, dict)) else 1 for v in values)
        combined_values = []
        for elem in values:
            combined_values.append({key: sum(val) for key, val in elem.items()})
        fill_values = []
        hatches = []
        colors = []
        for i_elem, elem in enumerate(combined_values):
            execute = 0
            if 'setup' in elem:
                fill_values += [elem['setup']]
                hatches += [hatch_dic['setup']]
                colors += [_colors[i_elem]]
            if 'offload' in elem:
                fill_values += [elem['offload']]
                hatches += [hatch_dic['offload']]
                colors += [_colors[i_elem]]
            if '_' in elem:
                execute += elem['_']
            if 'execute' in elem:
                execute += elem['execute']
            if execute > 0:
                fill_values += [execute]
                hatches += [hatch_dic['execute']]
                colors += [_colors[i_elem]]

        total = 0
        for i, val in enumerate(fill_values):
            bar = plt.bar(label, val, bottom=total, color=colors[i], hatch=hatches[i])
            total += val


    def plot(self, filename, title=None, ylabel=None, ylim=None, text=False, save=True):
        """
        Plot figure to file and configure labels and legends.

        Parameters
        ----------
        filename : str
            Path and name of output file.
        title : str, optional
            A title to add to the top of the plot.
        ylabel : str, optional
            Label for the y-axis
        ylim : tuple of float, optional
            Min and max value for the y-axis
        """
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.legend(self.groups, ncols=4, loc='center', bbox_to_anchor=(.5, 1.08))
        self.ax.set_ylim(ylim)

        if save:
            plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)

    def save(self, filename):
        plt.savefig(filename)
