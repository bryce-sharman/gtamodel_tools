"""
Plotting utilities for GtaModel tools.

"""

import matplotlib.pyplot as plt
from matplotlib import colormaps
from os import PathLike
import numpy as np
import pandas as pd
from typing import Tuple

idx = pd.IndexSlice

def plot_line_profiles(
        line_profiles: pd.DataFrame,
        fp: PathLike,
        *,
        figsize: Tuple=(8, 10),
        fontsize: float=12.0,
        titlefontsize: float=16.0
    ) -> None:
    """ Plots transit volumes, boardings and alightings along line profile.

    Args:
        line_profiles:
            Produced from Network.calculate_line_profiles
        fp:
            Filepath for exported image.
        figsize: tuple(float) 
            Width and height of individual profile plot. Default is (8, 10)
        fontsize 
            font size of tick labels and legend text
        titlefontsize
            font size of title
    """

    # Find the number of transit lines (# rows in the plot)
    lines = line_profiles.index.get_level_values('Line').unique()
    nrows = len(lines)
    # Find maximum number of directions per line (# columns in plot)
    ncols = 0
    for line in lines:
        line_df = line_profiles.loc[idx[line, :]]
        ndirs_in_line = line_df.index.get_level_values('Direction').nunique()
        if ndirs_in_line > ncols:
            ncols = ndirs_in_line
    figsize = (ncols*figsize[0], nrows*figsize[1])

    # Create the plot
    fig, axs = plt.subplots(nrows, ncols, figsize=figsize, layout='constrained')
    for i, line in enumerate(lines):
        line_df = line_profiles.loc[idx[line, :]]
        # Loop over all directions in the line
        for j, direction in enumerate(
                line_df.index.get_level_values('Direction').unique()):
            line_dir = line_df.loc[direction].copy()
            nstns = len(line_dir)
            # Check for a two-level index, means that there's a loop.
            if line_dir.index.nlevels==2:
                combined_index = \
                    line_dir.index.get_level_values(0).astype(str).str.cat(
                        line_dir.index.get_level_values(1).astype(str), 
                        sep=' - '
                    )
                line_dir = line_dir.set_index(combined_index)
            ax = axs[i, j]
            ax.set_title(
                f'Line profile:\n{line}\n{direction}', 
                fontsize=titlefontsize
            )
            # Boardings 
            ax.plot(
                line_dir.index.astype(str), line_dir['boardings'], linestyle='', 
                fillstyle='full', marker = '^', markerfacecolor ='cyan',
                markeredgecolor='black', markeredgewidth=1, markersize=7,
                label='Boardings'
            )
            # Alightings 
            ax.plot(
                line_dir.index.astype(str), line_dir['alightings'], linestyle='', 
                fillstyle='full', marker = 'v', markerfacecolor ='blue',
                markeredgecolor='black', markeredgewidth=1, markersize=7,
                label='Alightings'
            )
            # Volumes 
            ax.bar(
                line_dir.index.astype(str), line_dir['volume'], width=1, 
                color='blanchedalmond', edgecolor='black', linewidth=1,
                label='Volume'
            )
            
            # Write x labels
            major_ticks = np.arange(0, nstns)
            ax.set_xticks(major_ticks)
            xlabels = [''] * nstns
            stn_label_incr = max(int(nstns // 10), 1)
            for xpos, tick in enumerate(ax.xaxis.get_majorticklabels()):
                if xpos % stn_label_incr == 0:
                    xlabels[xpos] = line_dir.index[xpos]
                tick.set_horizontalalignment("right")
            ax.set_xticklabels(xlabels)
            ax.tick_params('x', rotation=45, labelsize=fontsize)
            ax.tick_params('y', labelsize=fontsize)
            
            ax.legend(loc=1, fontsize=fontsize)

    fig.savefig(fp)
    fig.clf()


def plot_tlfds(fp, *args):
    """ Plot an number of trip length distributions.

    Args:
        fp: Filepath in which to save final plot
        args:
            Set of four inputs, each containing:
            - numpy array: cumulative number of trips
            - numpy array: bins
            - str: label
            - matplotlib color
    """
    len_args = len(args)
    if len_args == 0 or len_args % 4 != 0:
        raise ValueError(
            '*args must contain inputs in sets of four, as follows: \n'
            '  - cumulative number of trips \n'
            '  - bin edges \n'
            '  - label \n'
            '  - matplotlib color \n'
        )
    fig, ax = plt.subplots(layout='constrained')

    n_series = int(len_args // 2)
    all_bins = []
    for i in range(0, n_series+1, 4):
        v = list(args[i])
        bins=list(args[i+1])
        label = args[i+2]
        color = args[i+3]
        
        x = [bins[0]]
        y = [0]
        for j in range(0, len(v)):
            x.extend([bins[j], bins[j+1]])
            y.extend([v[j], v[j]])
        ax.plot(x, y, label=label, color=color)
        all_bins.extend(bins)

    all_bins = np.sort(np.unique(all_bins))
    # Set x limits to the first and last bin edge

    ymax = ax.get_ylim()[1]
    xmax = ax.get_xlim()[1]
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    # Draw outer box around limits
    ax.plot([0, 0], [0, ymax], color='k', linewidth=2)
    ax.plot([0, xmax], [0, 0], color='k', linewidth=2)
    # Draw dotted lines at bin edges
    for ab in all_bins:
        if ab > 0 and ab < xmax:
            ax.plot([ab, ab], [0, ymax], color='k', linestyle=':',
                   linewidth=0.5)
    ax.legend(loc='center right')
    ax.set_ylabel('Number of trips', fontsize=12)
    ax.set_xlabel('Distance', fontsize=12)
    ax.set_title('Trip Length Frequecy Distribution')
    fig.savefig(fp)
    fig.clf()


def plot_annual_boardings_validation(
        model_boardings: pd.Series, 
        reference_boardings: pd.Series,
        fp: PathLike,
        *,
        figsize: Tuple=(8, 5),
        fontsize=12.0,
        titlefontsize=16.0
) -> None:
    """ Validates (daily) model boardings vs annual reference boardings.

    This validation is not clear-cut given that there is no expected ratio
    of annual to daily boardings. Hence this function plots this ratio in
    comparison to the following cases:
        a. even boardings every day of the week (365)
        b. even boardings on all weekdays, none on a weekend(261)
        c. even boardings on 3 days per week, none on any other day (156)
        d. even boardings on w days per week, none on any other day (104)

    Args:
        model_boardings: pandas.Series
            Aggregated daily model boardings
        reference_boardings: pandas.Series
            Aggregated annual model boardings. 
        fp: 
            Filepath in which to save final plot
        figsize: tuple(float) 
            Width and height of individual profile plot. Default is (8, 10)
        fontsize 
            font size of tick labels and legend text
        titlefontsize
            font size of title

    """
    fig, ax = plt.subplots(
        layout='constrained', figsize=figsize)
    ratio = reference_boardings / model_boardings
    npts = len(ratio)
    ax.plot(ratio.index, ratio, linestyle='', marker='+')

    xmax = ax.get_xlim()[1]
    ax.set_xlim(0, xmax)
    ref_lines = [
            ['All days', 365], 
            ['5 days/wk', 261], 
            ['3 days/wk', 156], 
            ['2 days/wk', 104]
    ]
    for a, b in ref_lines:
        ax.plot(ratio.index, [b]*npts, linestyle=':', label=a)
    ax.set_title(
        f'Model Daily Boarding Validation to Annual Reference', 
        fontsize=titlefontsize
    )
    
    ax.set_ylabel('Number of Boardings', fontsize=12)
    ax.set_title('Model Daily Boardings Validation vs Annual Count Data')

    # Write x labels
    for tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("right")
    ax.tick_params('x', rotation=45, labelsize=fontsize)
    ax.tick_params('y', labelsize=fontsize)
    ax.grid(axis='x')
    ax.legend()

    fig.savefig(fp)
    fig.clf()

def plot_labelled_XY_validation(
        x: pd.Series | pd.Index | np.ndarray,
        y: pd.Series | pd.Index | np.ndarray,
        labels: pd.Series | pd.Index | np.ndarray,
        title: str,
        fp: PathLike,
        *,
        figsize: Tuple=(8, 5),
        fontsize=12.0,
        titlefontsize=16.0
    ) -> None:
    """ Create a XY plot that compares values x vs y.
    
    Args:
        x: 
            Values to plot on the x-axis. Usually the validation data.
        y: 
            Values to plot on the y-axis. Usually the modelled data.
        labels: 
            Labels to annotate onto each point
        title: str,
        fp: PathLike
            Filepath in which to save final plot
        figsize: tuple(float) 
            Width and height of individual profile plot. Default is (8, 10)
        fontsize 
            font size of tick labels and legend text
        titlefontsize
            font size of title
    """
    if isinstance(x, pd.Series) or isinstance(x, pd.Index):
        x = x.to_numpy()
    if isinstance(y, pd.Series) or isinstance(y, pd.Index):
        y = y.to_numpy()
    if isinstance(labels, pd.Series) or isinstance(labels, pd.Index):
        labels = labels.to_numpy()
    n_pts = x.shape[0]
    if n_pts != y.shape[0] or n_pts != labels.shape[0]:
        raise ValueError(
            'x, y and labels must have the same number of elements.'
        )

    fig, ax = plt.subplots(figsize=[8,8])
    ax.plot(x, y, marker='o', linestyle='', markersize=fontsize + 2, 
            color='gray', alpha=0.5
    )
    xmax = ax.get_xlim()[1]
    ymax = ax.get_ylim()[1]
    xymax = max(xmax, ymax)
    # 45-degree line
    ax.plot([0, xymax], [0, xymax], linestyle=':', marker='', color='grey')
    # Add annotations to each point
    for i in range(0, n_pts):
        xi = x[i]
        yi = y[i]
        li = labels[i] 
        ax.annotate(li,
            # xy=(v + 0.005*xmax, mr + 0.005*ymax), 
            xy=(xi, yi), 
            xycoords='data',
            textcoords='data',
            horizontalalignment='center', 
            verticalalignment='center',
            # color=c,
            fontsize=fontsize
        )
    ax.set_xlabel('Validation', fontsize=fontsize)
    ax.set_ylabel('Model', fontsize=fontsize)
    ax.set_title(title, fontsize=titlefontsize)
    fig.savefig(fp)
    fig.clf()

def plot_barchart_validation(
        x: pd.Series | pd.Index | np.ndarray,
        y: pd.Series | pd.Index | np.ndarray,
        labels: pd.Series | pd.Index | np.ndarray,
        title: str,
        x_label: str,
        y_label: str,
        fp: PathLike,
        *,
        figsize: Tuple=(8, 5),
        fontsize=12.0,
        titlefontsize=16.0,
        x_label_rotation = 90
    ) -> None:
    """ 
    Create a side-by-size bar-chart plot that compares values x vs y.
        
    
    Args:
        x: 
            Values to plot on the x-axis. Usually the validation data.
        y: 
            Values to plot on the y-axis. Usually the modelled data.
        labels: 
            Labels to annotate onto each point
        title: str,
        x_label:
            x label to be applied in the plot legend
        y_label:
            y label to be applied in the plot legend
        fp:
            Filepath in which to save final plot
        figsize: tuple(float) 
            Width and height of individual profile plot. Default is (8, 10)
        fontsize 
            font size of tick labels and legend text
        titlefontsize
            font size of title
        x_label_rotation:
            Angle at which to rotate bar labels in degrees. Default is 90.
    """
    if isinstance(x, pd.Series) or isinstance(x, pd.Index):
        x = x.to_numpy()
    if isinstance(y, pd.Series) or isinstance(y, pd.Index):
        y = y.to_numpy()
    if isinstance(labels, pd.Series) or isinstance(labels, pd.Index):
        labels = labels.to_numpy()
    n_pts = x.shape[0]
    if n_pts != y.shape[0] or n_pts != labels.shape[0]:
        raise ValueError(
            'x, y and labels must have the same number of elements.'
        )
    cm = colormaps['tab10']
    fig, ax = plt.subplots(figsize=figsize, layout='constrained')
    xlocs = np.array(range(n_pts), dtype=np.float16)
    ax.bar(xlocs - 0.4, x, width=0.4, color=cm(0), edgecolor='black', 
           linewidth=1, label=x_label
    )
    ax.bar(xlocs, y, width=0.4, color=cm(1), edgecolor='black', 
           linewidth=1, label=y_label
    )
    # Write x labels, accepts optional angle to read long names
    # while taking up less vertical space.
    ax.set_xticks(xlocs)
    for  tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("right")
    ax.set_xticklabels(labels)
    ax.tick_params('x', rotation=x_label_rotation, labelsize=fontsize)
    ax.tick_params('y', labelsize=fontsize)
    
    ax.set_title(title, fontsize=titlefontsize)
    ax.legend(fontsize=fontsize)
    fig.savefig(fp)
    fig.clf()