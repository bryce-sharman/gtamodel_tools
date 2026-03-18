from matplotlib.axes import Axes
import numpy as np
import pandas as pd


def trumpet_diagram(
        counts: pd.Series, 
        model_volume: pd.Series, 
        *, 
        categories: pd.Series | list[pd.Series] | None = None,
        category_colours: dict[str | tuple, str] | None = None,
        category_markers: dict[str | tuple, str] | None = None, 
        label_format: str | None = None, 
        title: str = '',
        y_bounds: tuple[float, float] = (-2, 2), 
        ax: Axes | None = None, 
        x_label: str = "Count volume",
        legend: bool = True,  
        **kwargs) -> Axes:
    """
    Plots an auto volumes "trumpet" diagram of relative error vs. target count, 
    and will draw min/max error curves based on FHWA guidelines. Can be used to 
    plot different categories of count locations.

    Args:
        counts: 
            Target counts. Each item represents a different 
            count location. Index does not need to be unique.
        model_volume: 
            Modelled volumes for each location. The index must match the counts 
            Series.
        categories: 
            Optional classification of each count location. Must match the index 
            of the count Series. Can be provided as a list of Series (which all 
            must match the count index) to enable tuple-based categorization. 
            Default is None.
        category_colours 
            Mapping of each category to a colour, specified as a hex 
            string. Only used when categories are provided. Missing categories 
            revert to None, using the default colour for the style.
            Default is None.
        category_markers:  
            Mapping of each category to a matplotlib marker string 
            (see https://matplotlib.org/api/markers_api.html for options). Only 
            used when categories are provided. Missing categories revert to 
            None, using the default marker for the style. Default is None.
        label_format:
            Used to convert plot category values (especially tuples) into 
            readable strings for the legend. The relevant line of code is 
            "current_label = label_format % category_key". Only used when 
            categories are provided.
        title:
            The title to set on the plot. Default is an empty string.
        y_bounds: 
            Limit of the Y-Axis. This is needed because relative errors can be 
            very high close to the y-intercept of the plot.
            Default is ``(-2, 2)``, or (-200%, 200%). 
        ax:
            Sub-Axes to add this plot to, if using ``subplots()``.
            Defaults is None.
        x_label: 
            Label to use for the X-axis. The Y-axis is always "Relative Error". 
            Default is "Count volume".
        legend: 
            Flag to add a legend. Default is True.
        **kwargs: 
            Additional kwargs to pass to ``DataFrame.plot.scatter()``

    Returns:
        matplotlib.Axes:
            The Axes object generated from the plot. For most use cases, 
            this is not really needed.

    Notes: 
        This function was graciously provided by WSP Canada. 
    """

    assert model_volume.index.equals(counts.index)

    n_categories = 0
    if categories is not None:
        if isinstance(categories, list):
            for s in categories:
                assert s.index.equals(model_volume.index)
            if label_format is None:
                label_format = '-'.join(['%s'] * len(categories))
            categories = pd.MultiIndex.from_arrays(categories)
            n_categories = len(categories.unique())
        else:
            assert categories.index.equals(model_volume.index)
            n_categories = categories.nunique()

        if category_colours is None:
            category_colours = {}
        if category_markers is None:
            category_markers = {}
    if label_format is None:
        label_format = "%s"

    df = pd.DataFrame({'Model Volume': model_volume, 'Count Volume': counts})
    df['Error'] = df['Model Volume'] - df['Count Volume']
    df['% Error'] = df['Error'] / df['Count Volume']

    if n_categories > 1:
        for category_key, subset in df.groupby(categories):
            current_label = label_format % category_key
            current_color = category_colours[category_key] if \
                category_key in category_colours else None
            current_marker = category_markers[category_key] if \
                category_key in category_markers else None

            ax = subset.plot.scatter(
                x='Count Volume', y='% Error', ax=ax, c=current_color,
                marker=current_marker, label=current_label, **kwargs)
    else:
        ax = df.plot.scatter(x='Count Volume', y='% Error', ax=ax, **kwargs)

    # Add 5% to the top, to give some visual room on the right side
    top = counts.max() * 1.05  
    xs = np.arange(1, top, 10)
    pos_ys = (-13.7722 + (555.1382 * xs ** -0.26025)) / 100.
    neg_ys = pos_ys * -1

    ax.plot(xs, np.zeros(len(xs)), color='black')
    ax.plot(xs, pos_ys, color='red', linewidth=1, zorder=1)
    ax.plot(xs, neg_ys, color='red', linewidth=1, zorder=1)

    ax.set_xlim(0, top)

    bottom, top = y_bounds
    ax.set_ylim(bottom, top)
    ax.set_yticks(np.arange(bottom, top, 0.25))

    ax.set_title(title)
    ax.set_ylabel("Relative Error")
    ax.set_xlabel(x_label)
    if legend:
        ax.legend()

    return ax


def scatterplot(
    counts: pd.Series, 
    model_volume: pd.Series, 
    *, 
    categories: pd.Series | list[pd.Series] | None = None,            
    category_colours: dict[str | tuple, str] | None = None,
    category_markers: dict[str | tuple, str] | None = None, 
    label_format: str | None = None, 
    title: str = '',
    ax: Axes | None = None, 
    x_label: str = "Count volume",
    legend: bool = True, **kwargs) -> Axes:
    """Plots an auto volumes "trumpet" diagram of relative error vs. target count, and will draw min/max error curves
    based on FHWA guidelines. Can be used to plot different categories of count locations.

    Args:
        counts: 
            Target counts. Each item represents a different count location. 
            Index does not need to be unique.
        model_volume: 
            Modelled volumes for each location. The index must match the counts 
            Series.
        categories: 
            Optional classification of each count location. Must match the index 
            of the count Series. Can be provided as a list of Series (which
            all must match the count index) to enable tuple-based 
            categorization. Default is None.
        category_colours: 
            Mapping of each category to a colour, specified as a hex string. 
            Only used when categories are provided. Missing categories revert to
            None, using the default colour for the style. Default is None.
        category_markers: 
            Mapping of each category to a matplotlib marker string (see 
            https://matplotlib.org/api/markers_api.html for options). Only used 
            when categories are provided. Missing categories revert to None, 
            using the default marker for the style. Default is None.
        label_format:
            Used to convert category values (especially tuples) into readable
            strings for the plot legend. The relevant line of code is
            ``current_label = label_format % category_key``. 
            Only used when categories are provided. Default is None.
        title: 
            The title to set on the plot. Default is an empty string.
        ax: 
            Sub-Axes to add this plot to, if using ``subplots()``. 
            Default is None.
        x_label: 
            Label to use for the X-axis. Note that the Y-axis is always 
            "Model volume". Default is "Count volume". 
        legend: 
            Flag to add a legend. Default is True.
        **kwargs: 
            Additional kwargs to pass to ``DataFrame.plot.scatter()``

    Returns:
        matplotlib.Axes:
            The Axes object generated from the plot. For most use cases, this is not really needed.

    Notes:
        This function was based off the trumpet_diagram function, which was
        graciously provided by WSP Canada. 
    """
    index_errmsg = '%s and %s indices do not match'
    if not model_volume.index.equals(counts.index):
        raise index_errmsg % ('counts', 'model_volume')

    n_categories = 0
    if categories is not None:
        if isinstance(categories, list):
            for s in categories:
                if not model_volume.index.equals(counts.index):
                    raise index_errmsg % ('categories', 'model_volume')

            if label_format is None:
                label_format = '-'.join(['%s'] * len(categories))
            categories = pd.MultiIndex.from_arrays(categories)
            n_categories = len(categories.unique())
        else:
            if not model_volume.index.equals(counts.index):
                raise index_errmsg % ('categories', 'model_volume')
            n_categories = categories.nunique()

        if category_colours is None:
            category_colours = {}
        if category_markers is None:
            category_markers = {}
    if label_format is None:
        label_format = "%s"

    df = pd.DataFrame({'Model Volume': model_volume, 'Count Volume': counts})

    if n_categories > 1:
        for category_key, subset in df.groupby(categories):
            current_label = label_format % category_key
            current_color = category_colours[category_key] if \
                category_key in category_colours else None
            current_marker = category_markers[category_key] if \
                category_key in category_markers else None

            ax = subset.plot.scatter(
                x='Count Volume', y='Model Volume', ax=ax, c=current_color,
                marker=current_marker, label=current_label, **kwargs)
    else:
        ax = df.plot.scatter(
            x='Count Volume', y='Model Volume', ax=ax, **kwargs)

    # Set plot extents
    max_val = max(counts.max(), model_volume.max())
    top = max_val * 1.05  
    ax.plot([0, top], [0, top], color='red', linewidth=1, zorder=1)
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    ax.grid(visible=True, which='major', axis='both')

    ax.set_title(title)
    ax.set_ylabel("Model volume")
    ax.set_xlabel(x_label)
    if legend and n_categories > 1:
        ax.legend()

    return ax