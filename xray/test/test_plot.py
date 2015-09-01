import unittest

import numpy as np
import pandas as pd

from xray import DataArray

import xray.plot as xplt
from xray.plot.plot import (_infer_interval_breaks,
                            _determine_cmap_params,
                            _build_discrete_cmap,
                            _color_palette)

from . import TestCase, requires_matplotlib

try:
    import matplotlib as mpl
    # Using a different backend makes Travis CI work.
    mpl.use('Agg')
    # Order of imports is important here.
    import matplotlib.pyplot as plt
except ImportError:
    pass


def text_in_fig():
    '''
    Return the set of all text in the figure
    '''
    alltxt = [t.get_text() for t in plt.gcf().findobj(mpl.text.Text)]
    # Set comprehension not compatible with Python 2.6
    return set(alltxt)


def substring_in_axes(substring, ax):
    '''
    Return True if a substring is found anywhere in an axes
    '''
    alltxt = set([t.get_text() for t in ax.findobj(mpl.text.Text)])
    for txt in alltxt:
        if substring in txt:
            return True
    return False


def easy_array(shape, start=0, stop=1):
    '''
    Make an array with desired shape using np.linspace

    shape is a tuple like (2, 3)
    '''
    a = np.linspace(start, stop, num=np.prod(shape))
    return a.reshape(shape)


@requires_matplotlib
class PlotTestCase(TestCase):

    def tearDown(self):
        # Remove all matplotlib figures
        plt.close('all')

    def pass_in_axis(self, plotmethod):
        fig, axes = plt.subplots(ncols=2)
        plotmethod(ax=axes[0])
        self.assertTrue(axes[0].has_data())

    def imshow_called(self, plotmethod):
        plotmethod()
        images = plt.gca().findobj(mpl.image.AxesImage)
        return len(images) > 0

    def contourf_called(self, plotmethod):
        plotmethod()
        paths = plt.gca().findobj(mpl.collections.PathCollection)
        return len(paths) > 0


class TestPlot(PlotTestCase):

    def setUp(self):
        self.darray = DataArray(np.arange(2*3*4).reshape(2, 3, 4))

    def test1d(self):
        self.darray[:, 0, 0].plot()

    def test_2d_before_squeeze(self):
        a = DataArray(np.arange(5).reshape(1, 5))
        a.plot()

    def test2d_uniform_calls_imshow(self):
        self.assertTrue(self.imshow_called(self.darray[:, :, 0].plot))

    def test2d_nonuniform_calls_contourf(self):
        a = self.darray[:, :, 0]
        a.coords['dim_1'] = [2, 1, 89]
        self.assertTrue(self.contourf_called(a.plot))

    def test3d(self):
        self.darray.plot()

    def test_can_pass_in_axis(self):
        self.pass_in_axis(self.darray.plot)

    def test__infer_interval_breaks(self):
        self.assertArrayEqual([-0.5, 0.5, 1.5], _infer_interval_breaks([0, 1]))
        self.assertArrayEqual([-0.5, 0.5, 5.0, 9.5, 10.5],
                              _infer_interval_breaks([0, 1, 9, 10]))
        self.assertArrayEqual(pd.date_range('20000101', periods=4) - np.timedelta64(12, 'h'),
                              _infer_interval_breaks(pd.date_range('20000101', periods=3)))


class TestPlot1D(PlotTestCase):

    def setUp(self):
        d = [0, 1.1, 0, 2]
        self.darray = DataArray(d, coords={'period': range(len(d))})

    def test_xlabel_is_index_name(self):
        self.darray.plot()
        self.assertEqual('period', plt.gca().get_xlabel())

    def test_no_label_name_on_y_axis(self):
        self.darray.plot()
        self.assertEqual('', plt.gca().get_ylabel())

    def test_ylabel_is_data_name(self):
        self.darray.name = 'temperature'
        self.darray.plot()
        self.assertEqual(self.darray.name, plt.gca().get_ylabel())

    def test_wrong_dims_raises_valueerror(self):
        twodims = DataArray(np.arange(10).reshape(2, 5))
        with self.assertRaises(ValueError):
            twodims.plot.line()

    def test_format_string(self):
        self.darray.plot.line('ro')

    def test_can_pass_in_axis(self):
        self.pass_in_axis(self.darray.plot.line)

    def test_nonnumeric_index_raises_typeerror(self):
        a = DataArray([1, 2, 3], {'letter': ['a', 'b', 'c']})
        with self.assertRaisesRegexp(TypeError, r'[Pp]lot'):
            a.plot.line()

    def test_primitive_returned(self):
        p = self.darray.plot.line()
        self.assertTrue(isinstance(p[0], mpl.lines.Line2D))

    def test_plot_nans(self):
        self.darray[1] = np.nan
        self.darray.plot.line()

    def test_x_ticks_are_rotated_for_time(self):
        time = pd.date_range('2000-01-01', '2000-01-10')
        a = DataArray(np.arange(len(time)), {'t': time})
        a.plot.line()
        rotation = plt.gca().get_xticklabels()[0].get_rotation()
        self.assertFalse(rotation == 0)

    def test_slice_in_title(self):
        self.darray.coords['d'] = 10
        self.darray.plot.line()
        title = plt.gca().get_title()
        self.assertEqual('d = 10', title)


class TestPlotHistogram(PlotTestCase):

    def setUp(self):
        self.darray = DataArray(easy_array((2, 3, 4)))

    def test_3d_array(self):
        self.darray.plot.hist()

    def test_title_no_name(self):
        self.darray.plot.hist()
        self.assertEqual('', plt.gca().get_title())

    def test_title_uses_name(self):
        self.darray.name = 'testpoints'
        self.darray.plot.hist()
        self.assertIn(self.darray.name, plt.gca().get_title())

    def test_ylabel_is_count(self):
        self.darray.plot.hist()
        self.assertEqual('Count', plt.gca().get_ylabel())

    def test_can_pass_in_kwargs(self):
        nbins = 5
        self.darray.plot.hist(bins=nbins)
        self.assertEqual(nbins, len(plt.gca().patches))

    def test_can_pass_in_axis(self):
        self.pass_in_axis(self.darray.plot.hist)

    def test_primitive_returned(self):
        h = self.darray.plot.hist()
        self.assertTrue(isinstance(h[-1][0], mpl.patches.Rectangle))

    def test_plot_nans(self):
        self.darray[0, 0, 0] = np.nan
        self.darray.plot.hist()


@requires_matplotlib
class TestDetermineCmapParams(TestCase):
    def setUp(self):
        self.data = np.linspace(0, 1, num=100)

    def test_robust(self):
        cmap_params = _determine_cmap_params(self.data, robust=True)
        self.assertEqual(cmap_params['vmin'], np.percentile(self.data, 2))
        self.assertEqual(cmap_params['vmax'], np.percentile(self.data, 98))
        self.assertEqual(cmap_params['cmap'].name, 'viridis')
        self.assertEqual(cmap_params['extend'], 'both')
        self.assertIsNone(cmap_params['levels'])
        self.assertIsNone(cmap_params['cnorm'])

    def test_center(self):
        cmap_params = _determine_cmap_params(self.data, center=0.5)
        self.assertEqual(cmap_params['vmax'] - 0.5, 0.5 - cmap_params['vmin'])
        self.assertEqual(cmap_params['cmap'], 'RdBu_r')
        self.assertEqual(cmap_params['extend'], 'neither')
        self.assertIsNone(cmap_params['levels'])
        self.assertIsNone(cmap_params['cnorm'])

    def test_integer_levels(self):
        data = self.data + 1
        cmap_params = _determine_cmap_params(data, levels=5, vmin=0, vmax=5,
                                             cmap='Blues')
        self.assertEqual(cmap_params['vmin'], cmap_params['levels'][0])
        self.assertEqual(cmap_params['vmax'], cmap_params['levels'][-1])
        self.assertEqual(cmap_params['cmap'].name, 'Blues')
        self.assertEqual(cmap_params['extend'], 'neither')
        self.assertEqual(cmap_params['cmap'].N, 5)
        self.assertEqual(cmap_params['cnorm'].N, 6)

        cmap_params = _determine_cmap_params(data, levels=5,
                                             vmin=0.5, vmax=1.5)
        self.assertEqual(cmap_params['cmap'].name, 'viridis')
        self.assertEqual(cmap_params['extend'], 'max')

    def test_list_levels(self):
        data = self.data + 1

        orig_levels = [0, 1, 2, 3, 4, 5]
        # vmin and vmax should be ignored if levels are explicitly provided
        cmap_params = _determine_cmap_params(data, levels=orig_levels,
                                             vmin=0, vmax=3)
        self.assertEqual(cmap_params['vmin'], 0)
        self.assertEqual(cmap_params['vmax'], 5)
        self.assertEqual(cmap_params['cmap'].N, 5)
        self.assertEqual(cmap_params['cnorm'].N, 6)

        for wrap_levels in [list, np.array, pd.Index, DataArray]:
            cmap_params = _determine_cmap_params(
                data, levels=wrap_levels(orig_levels))
            self.assertArrayEqual(cmap_params['levels'], orig_levels)


@requires_matplotlib
class TestDiscreteColorMap(TestCase):
    def setUp(self):
        x = np.arange(start=0, stop=10, step=2)
        y = np.arange(start=9, stop=-7, step=-3)
        xy = np.dstack(np.meshgrid(x, y))
        distance = np.linalg.norm(xy, axis=2)
        self.darray = DataArray(distance, list(zip(('y', 'x'), (y, x))))
        self.data_min = distance.min()
        self.data_max = distance.max()

    def test_recover_from_seaborn_jet_exception(self):
        pal = _color_palette('jet', 4)
        self.assertTrue(type(pal) == np.ndarray)
        self.assertEqual(len(pal), 4)

    def test_build_discrete_cmap(self):
        for (cmap, levels, extend, filled) in [('jet', [0, 1], 'both', False),
                                               ('hot', [-4, 4], 'max', True)]:
            ncmap, cnorm = _build_discrete_cmap(cmap, levels, extend, filled)
            self.assertEqual(ncmap.N, len(levels) - 1)
            self.assertEqual(len(ncmap.colors), len(levels) - 1)
            self.assertEqual(cnorm.N, len(levels))
            self.assertArrayEqual(cnorm.boundaries, levels)
            self.assertEqual(max(levels), cnorm.vmax)
            self.assertEqual(min(levels), cnorm.vmin)
            if filled:
                self.assertEqual(ncmap.colorbar_extend, extend)
            else:
                self.assertEqual(ncmap.colorbar_extend, 'neither')

    def test_discrete_colormap_list_of_levels(self):
        for extend, levels in [('max', [-1, 2, 4, 8, 10]),
                               ('both', [2, 5, 10, 11]),
                               ('neither', [0, 5, 10, 15]),
                               ('min', [2, 5, 10, 15])]:
            for kind in ['imshow', 'pcolormesh', 'contourf', 'contour']:
                primitive = getattr(self.darray.plot, kind)(levels=levels)
                self.assertArrayEqual(levels, primitive.norm.boundaries)
                self.assertEqual(max(levels), primitive.norm.vmax)
                self.assertEqual(min(levels), primitive.norm.vmin)
                if kind != 'contour':
                    self.assertEqual(extend, primitive.cmap.colorbar_extend)
                else:
                    self.assertEqual('neither', primitive.cmap.colorbar_extend)
                self.assertEqual(len(levels) - 1, len(primitive.cmap.colors))

    def test_discrete_colormap_int_levels(self):
        for extend, levels, vmin, vmax in [('neither', 7, None, None),
                                           ('neither', 7, None, 20),
                                           ('both', 7, 4, 8),
                                           ('min', 10, 4, 15)]:
            for kind in ['imshow', 'pcolormesh', 'contourf', 'contour']:
                primitive = getattr(self.darray.plot, kind)(levels=levels,
                                                            vmin=vmin,
                                                            vmax=vmax)
                self.assertGreaterEqual(levels,
                                        len(primitive.norm.boundaries) - 1)
                if vmax is None:
                    self.assertGreaterEqual(primitive.norm.vmax, self.data_max)
                else:
                    self.assertGreaterEqual(primitive.norm.vmax, vmax)
                if vmin is None:
                    self.assertLessEqual(primitive.norm.vmin, self.data_min)
                else:
                    self.assertLessEqual(primitive.norm.vmin, vmin)
                if kind != 'contour':
                    self.assertEqual(extend, primitive.cmap.colorbar_extend)
                else:
                    self.assertEqual('neither', primitive.cmap.colorbar_extend)
                self.assertGreaterEqual(levels, len(primitive.cmap.colors))

    def test_discrete_colormap_list_levels_and_vmin_or_vmax(self):
        levels = [0, 5, 10, 15]
        primitive = self.darray.plot(levels=levels, vmin=-3, vmax=20)
        self.assertEqual(primitive.norm.vmax, max(levels))
        self.assertEqual(primitive.norm.vmin, min(levels))


class Common2dMixin:
    """
    Common tests for 2d plotting go here.

    These tests assume that a staticmethod for `self.plotfunc` exists.
    Should have the same name as the method.
    """
    def setUp(self):
        self.darray = DataArray(easy_array((10, 15), start=-1), dims=['y', 'x'])
        self.plotmethod = getattr(self.darray.plot, self.plotfunc.__name__)

    def test_label_names(self):
        self.plotmethod()
        self.assertEqual('x', plt.gca().get_xlabel())
        self.assertEqual('y', plt.gca().get_ylabel())

    def test_1d_raises_valueerror(self):
        with self.assertRaisesRegexp(ValueError, r'[Dd]im'):
            self.plotfunc(self.darray[0, :])

    def test_3d_raises_valueerror(self):
        a = DataArray(easy_array((2, 3, 4)))
        with self.assertRaisesRegexp(ValueError, r'[Dd]im'):
            self.plotfunc(a)

    def test_nonnumeric_index_raises_typeerror(self):
        a = DataArray(easy_array((3, 2)),
                      coords=[['a', 'b', 'c'], ['d', 'e']])
        with self.assertRaisesRegexp(TypeError, r'[Pp]lot'):
            self.plotfunc(a)

    def test_can_pass_in_axis(self):
        self.pass_in_axis(self.plotmethod)

    def test_xyincrease_false_changes_axes(self):
        self.plotmethod(xincrease=False, yincrease=False)
        xlim = plt.gca().get_xlim()
        ylim = plt.gca().get_ylim()
        diffs = xlim[0] - 14, xlim[1] - 0, ylim[0] - 9, ylim[1] - 0
        self.assertTrue(all(abs(x) < 1 for x in diffs))

    def test_xyincrease_true_changes_axes(self):
        self.plotmethod(xincrease=True, yincrease=True)
        xlim = plt.gca().get_xlim()
        ylim = plt.gca().get_ylim()
        diffs = xlim[0] - 0, xlim[1] - 14, ylim[0] - 0, ylim[1] - 9
        self.assertTrue(all(abs(x) < 1 for x in diffs))

    def test_plot_nans(self):
        x1 = self.darray[:5]
        x2 = self.darray.copy()
        x2[5:] = np.nan

        clim1 = self.plotfunc(x1).get_clim()
        clim2 = self.plotfunc(x2).get_clim()
        self.assertEqual(clim1, clim2)

    def test_viridis_cmap(self):
        cmap_name = self.plotmethod(cmap='viridis').get_cmap().name
        self.assertEqual('viridis', cmap_name)

    def test_default_cmap(self):
        cmap_name = self.plotmethod().get_cmap().name
        self.assertEqual('RdBu_r', cmap_name)

        cmap_name = self.plotfunc(abs(self.darray)).get_cmap().name
        self.assertEqual('viridis', cmap_name)

    def test_seaborn_palette_as_cmap(self):
        try:
            import seaborn
            cmap_name = self.plotmethod(
                    levels=2, cmap='husl').get_cmap().name
            self.assertEqual('husl', cmap_name)
        except ImportError:
            pass

    def test_can_change_default_cmap(self):
        cmap_name = self.plotmethod(cmap='Blues').get_cmap().name
        self.assertEqual('Blues', cmap_name)

    def test_diverging_color_limits(self):
        artist = self.plotmethod()
        vmin, vmax = artist.get_clim()
        self.assertAlmostEqual(-vmin, vmax)

    def test_xy_strings(self):
        self.plotmethod('y', 'x')
        ax = plt.gca()
        self.assertEqual('y', ax.get_xlabel())
        self.assertEqual('x', ax.get_ylabel())

    def test_positional_x_string(self):
        self.plotmethod('y')
        ax = plt.gca()
        self.assertEqual('y', ax.get_xlabel())
        self.assertEqual('x', ax.get_ylabel())

    def test_y_string(self):
        self.plotmethod(y='x')
        ax = plt.gca()
        self.assertEqual('y', ax.get_xlabel())
        self.assertEqual('x', ax.get_ylabel())

    def test_bad_x_string_exception(self):
        with self.assertRaisesRegexp(KeyError, r'y'):
            self.plotmethod('not_a_real_dim')

    def test_default_title(self):
        a = DataArray(easy_array((4, 3, 2, 1)), dims=['a', 'b', 'c', 'd'])
        self.plotfunc(a.isel(c=1))
        title = plt.gca().get_title()
        self.assertEqual('c = 1, d = 0', title)

    def test_default_title(self):
        a = DataArray(easy_array((4, 3, 2)), dims=['a', 'b', 'c'])
        a.coords['d'] = 10
        self.plotfunc(a.isel(c=1))
        title = plt.gca().get_title()
        self.assertEqual('c = 1, d = 10', title)

    def test_colorbar_label(self):
        self.darray.name = 'testvar'
        self.plotmethod()
        self.assertIn(self.darray.name, text_in_fig())

    def test_no_labels(self):
        self.darray.name = 'testvar'
        self.plotmethod(add_labels=False)
        alltxt = text_in_fig()
        for string in ['x', 'y', 'testvar']:
            self.assertNotIn(string, alltxt)

    def test_facetgrid(self):
        a = easy_array((10, 15, 3))
        d = DataArray(a, dims=['y', 'x', 'z'])
        g = xplt.FacetGrid(d, col='z')
        g.map_dataarray(self.plotfunc, 'x', 'y')
        for ax in g:
            self.assertTrue(ax.has_data())


class TestContourf(Common2dMixin, PlotTestCase):

    plotfunc = staticmethod(xplt.contourf)

    def test_contourf_called(self):
        # Having both statements ensures the test works properly
        self.assertFalse(self.contourf_called(self.darray.plot.imshow))
        self.assertTrue(self.contourf_called(self.darray.plot.contourf))

    def test_primitive_artist_returned(self):
        artist = self.plotmethod()
        self.assertTrue(isinstance(artist, mpl.contour.QuadContourSet))

    def test_extend(self):
        artist = self.plotmethod()
        self.assertEqual(artist.extend, 'neither')

        self.darray[0, 0] = -100
        self.darray[-1, -1] = 100
        artist = self.plotmethod(robust=True)
        self.assertEqual(artist.extend, 'both')

        self.darray[0, 0] = 0
        self.darray[-1, -1] = 0
        artist = self.plotmethod(vmin=-0, vmax=10)
        self.assertEqual(artist.extend, 'min')

        artist = self.plotmethod(vmin=-10, vmax=0)
        self.assertEqual(artist.extend, 'max')

    def test_levels(self):
        artist = self.plotmethod(levels=[-0.5, -0.4, 0.1])
        self.assertEqual(artist.extend, 'both')

        artist = self.plotmethod(levels=3)
        self.assertEqual(artist.extend, 'neither')


class TestContour(Common2dMixin, PlotTestCase):

    plotfunc = staticmethod(xplt.contour)

    def test_colors(self):
        # matplotlib cmap.colors gives an rgbA ndarray
        # when seaborn is used, instead we get an rgb tuble
        def _color_as_tuple(c):
            return tuple(c[:3])
        artist = self.plotmethod(colors='k')
        self.assertEqual(
                _color_as_tuple(artist.cmap.colors[0]),
                (0.0,0.0,0.0))

        artist = self.plotmethod(colors=['k','b'])
        self.assertEqual(
                _color_as_tuple(artist.cmap.colors[1]),
                (0.0,0.0,1.0))

    def test_cmap_and_color_both(self):
        with self.assertRaises(ValueError):  
            self.plotmethod(colors='k', cmap='RdBu')

    def list_of_colors_in_cmap_deprecated(self):
        with self.assertRaises(DeprecationError):
            self.plotmethod(cmap=['k','b'])

class TestPcolormesh(Common2dMixin, PlotTestCase):

    plotfunc = staticmethod(xplt.pcolormesh)

    def test_primitive_artist_returned(self):
        artist = self.plotmethod()
        self.assertTrue(isinstance(artist, mpl.collections.QuadMesh))

    def test_everything_plotted(self):
        artist = self.plotmethod()
        self.assertEqual(artist.get_array().size, self.darray.size)


class TestImshow(Common2dMixin, PlotTestCase):

    plotfunc = staticmethod(xplt.imshow)

    def test_imshow_called(self):
        # Having both statements ensures the test works properly
        self.assertFalse(self.imshow_called(self.darray.plot.contourf))
        self.assertTrue(self.imshow_called(self.darray.plot.imshow))

    def test_xy_pixel_centered(self):
        self.darray.plot.imshow()
        self.assertTrue(np.allclose([-0.5, 14.5], plt.gca().get_xlim()))
        self.assertTrue(np.allclose([9.5, -0.5], plt.gca().get_ylim()))

    def test_default_aspect_is_auto(self):
        self.darray.plot.imshow()
        self.assertEqual('auto', plt.gca().get_aspect())

    def test_can_change_aspect(self):
        self.darray.plot.imshow(aspect='equal')
        self.assertEqual('equal', plt.gca().get_aspect())

    def test_primitive_artist_returned(self):
        artist = self.plotmethod()
        self.assertTrue(isinstance(artist, mpl.image.AxesImage))

    def test_seaborn_palette_needs_levels(self):
        try:
            import seaborn
            with self.assertRaises(ValueError):
                self.plotmethod(cmap='husl')
        except ImportError:
            pass


class TestFacetGrid(PlotTestCase):

    def setUp(self):
        d = np.arange(10 * 15 * 3).reshape(10, 15, 3)
        self.darray = DataArray(d, dims=['y', 'x', 'z'])
        self.g = xplt.FacetGrid(self.darray, col='z')

    def test_no_args(self):
        self.g.map_dataarray(xplt.contourf)
        for ax in self.g:
            self.assertTrue(ax.has_data())

            # Font size should be small
            fontsize = ax.title.get_size()
            self.assertLessEqual(fontsize, 12)

    def test_names_appear_somewhere(self):
        self.darray.name = 'testvar'
        self.g.map_dataarray(xplt.contourf, 'x', 'y')
        for i, ax in enumerate(self.g):
            self.assertEqual('z = {0}'.format(i), ax.get_title())

        alltxt = text_in_fig()
        self.assertIn(self.darray.name, alltxt)
        for label in ['x', 'y']:
            self.assertIn(label, alltxt)

    def test_text_not_super_long(self):
        self.darray.coords['z'] = [100 * letter for letter in 'abc']
        g = xplt.FacetGrid(self.darray, col='z')
        g.map_dataarray(xplt.contour, 'x', 'y')
        alltxt = text_in_fig()
        maxlen = max(len(txt) for txt in alltxt)
        self.assertLess(maxlen, 50)

        t0 = g.axes[0, 0].get_title()
        self.assertTrue(t0.endswith('...'))

    def test_colorbar(self):
        vmin = self.darray.values.min()
        vmax = self.darray.values.max()
        expected = np.array((vmin, vmax))

        self.g.map_dataarray(xplt.imshow, 'x', 'y')

        for image in plt.gcf().findobj(mpl.image.AxesImage):
            clim = np.array(image.get_clim())
            self.assertTrue(np.allclose(expected, clim))

        # There's only one colorbar
        cbar = plt.gcf().findobj(mpl.collections.QuadMesh)
        self.assertEqual(1, len(cbar))
        
    def test_empty_cell(self):
        g = xplt.FacetGrid(self.darray, col='z', col_wrap=2)
        g.map_dataarray(xplt.imshow, 'x', 'y')
        
        bottomright = g.axes[-1, -1]
        self.assertFalse(bottomright.has_data())

    def test_row_and_col_shape(self):
        a = np.arange(10 * 15 * 3 * 2).reshape(10, 15, 3, 2)
        d = DataArray(a, dims=['y', 'x', 'col', 'row'])

        d.coords['col'] = np.array(['col' + str(x) for x in
            d.coords['col'].values])
        d.coords['row'] = np.array(['row' + str(x) for x in
            d.coords['row'].values])

        g = xplt.FacetGrid(d, col='col', row='row')
        self.assertEqual((2, 3), g.axes.shape)

        g.map_dataarray(xplt.imshow, 'x', 'y')

        # Rightmost column should be labeled
        for label, ax in zip(d.coords['row'].values, g.axes[:, -1]):
            self.assertTrue(substring_in_axes(label, ax))

        # Top row should be labeled
        for label, ax in zip(d.coords['col'].values, g.axes[0, :]):
            self.assertTrue(substring_in_axes(label, ax))

    def test_norow_nocol_error(self):
        with self.assertRaisesRegexp(ValueError, r'[Rr]ow'):
            xplt.FacetGrid(self.darray)

    def test_groups(self):
        self.g.map_dataarray(xplt.imshow, 'x', 'y')
        upperleft_dict = self.g.name_dicts[0, 0]
        upperleft_array = self.darray[upperleft_dict]
        z0 = self.darray.isel(z=0)

        self.assertDataArrayEqual(upperleft_array, z0)
        # Not sure if we need to expose this in this way
        #self.assertDataArrayEqual(self.facet_data[0, 0], z0)

    def test_float_index(self):
        self.darray.coords['z'] = [0.1, 0.2, 0.4]
        g = xplt.FacetGrid(self.darray, col='z')
        g.map_dataarray(xplt.imshow, 'x', 'y')

    def test_nonunique_index_error(self):
        self.darray.coords['z'] = [0.1, 0.2, 0.2]
        with self.assertRaisesRegexp(ValueError, r'[Uu]nique'):
            g = xplt.FacetGrid(self.darray, col='z')

    def test_robust(self):
        z = np.zeros((20, 20, 2))
        darray = DataArray(z, dims=['y', 'x', 'z'])
        darray[:, :, 1] = 1
        darray[2, 0, 0] = -1000
        darray[3, 0, 0] = 1000
        g = xplt.FacetGrid(darray, col='z')
        g.map_dataarray(xplt.imshow, 'x', 'y', robust=True)

        # Color limits should be 0, 1
        # The largest number displayed in the figure should be less than 21
        numbers = set()
        alltxt = text_in_fig()
        for txt in alltxt:
            try:
                numbers.add(float(txt))
            except ValueError:
                pass
        largest = max(abs(x) for x in numbers)
        self.assertLess(largest, 21)

    def test_can_set_vmin_vmax(self):
        vmin, vmax = 50.0, 1000.0
        expected = np.array((vmin, vmax))
        self.g.map_dataarray(xplt.imshow, 'x', 'y', vmin=vmin, vmax=vmax)

        for image in plt.gcf().findobj(mpl.image.AxesImage):
            clim = np.array(image.get_clim())
            self.assertTrue(np.allclose(expected, clim))
