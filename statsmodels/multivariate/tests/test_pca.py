from __future__ import print_function, division

from unittest import TestCase
import warnings

import numpy as np
from numpy.testing import assert_allclose, assert_equal, assert_raises
from numpy.testing.decorators import skipif
import pandas as pd

try:
    import matplotlib.pyplot as plt
    missing_matplotlib = False
except ImportError:
    missing_matplotlib = True

from statsmodels.multivariate.pca import PCA
from statsmodels.multivariate.tests.results.datamlw import data, princomp1, princomp2
from statsmodels.compat.numpy import nanmean

DECIMAL_5 = .00001


class TestPCA(TestCase):
    @classmethod
    def setUpClass(cls):
        rs = np.random.RandomState()
        rs.seed(1234)
        k = 3
        n = 100
        t = 200
        lam = 2

        norm_rng = rs.standard_normal
        e = norm_rng((t, n))
        f = norm_rng((t, k))
        b = rs.standard_gamma(lam, size=(k, n)) / lam
        cls.x = f.dot(b) + e
        cls.x_copy = cls.x + 0.0
        cls.rs = rs

        k = 3
        n = 300
        t = 200
        lam = 2

        norm_rng = rs.standard_normal
        e = norm_rng((t, n))
        f = norm_rng((t, k))
        b = rs.standard_gamma(lam, size=(k, n)) / lam
        cls.x_wide = f.dot(b) + e

    @skipif(missing_matplotlib)
    def test_smoke_plot_and_repr(self):
        pc = PCA(self.x)
        fig = pc.plot_scree()
        fig = pc.plot_scree(ncomp=10)
        fig = pc.plot_scree(log_scale=False)
        fig = pc.plot_scree(cumulative=True)
        fig = pc.plot_rsquare()
        fig = pc.plot_rsquare(ncomp=5)
        # Additional smoke test
        pc.__repr__()
        pc = PCA(self.x, standardize=False)
        pc.__repr__()
        pc = PCA(self.x, standardize=False, demean=False)
        pc.__repr__()
        # Check data for no changes
        assert_equal(self.x, pc.data)

    def test_eig_svd_equiv(self):
        """
        Test leading components since the tail end can differ
        """
        pc_eig = PCA(self.x)
        pc_svd = PCA(self.x, method='svd')

        assert_allclose(pc_eig.projection, pc_svd.projection)
        assert_allclose(np.abs(pc_eig.factors[:, :2]),
                        np.abs(pc_svd.factors[:, :2]))
        assert_allclose(np.abs(pc_eig.coeff[:2, :]),
                        np.abs(pc_svd.coeff[:2, :]))
        assert_allclose(pc_eig.eigenvals,
                        pc_svd.eigenvals)
        assert_allclose(np.abs(pc_eig.eigenvecs[:, :2]),
                        np.abs(pc_svd.eigenvecs[:, :2]))

        pc_svd = PCA(self.x, method='svd', ncomp=2)
        pc_nipals = PCA(self.x, method='nipals', ncomp=2)
        assert_allclose(np.abs(pc_nipals.factors),
                        np.abs(pc_svd.factors),
                        atol=DECIMAL_5)
        assert_allclose(np.abs(pc_nipals.coeff),
                        np.abs(pc_svd.coeff),
                        atol=DECIMAL_5)
        assert_allclose(pc_nipals.eigenvals,
                        pc_svd.eigenvals,
                        atol=DECIMAL_5)
        assert_allclose(np.abs(pc_nipals.eigenvecs),
                        np.abs(pc_svd.eigenvecs),
                        atol=DECIMAL_5)
        # Check data for no changes
        assert_equal(self.x, pc_svd.data)
        # Check data for no changes
        assert_equal(self.x, pc_eig.data)
        # Check data for no changes
        assert_equal(self.x, pc_nipals.data)

    def test_options(self):
        pc = PCA(self.x)
        pc_no_norm = PCA(self.x, normalize=False)
        assert_allclose(pc.factors.dot(pc.coeff),
                        pc_no_norm.factors.dot(pc_no_norm.coeff))
        princomp = pc.factors
        assert_allclose(princomp.T.dot(princomp), np.eye(100), atol=1e-5)
        weights = pc_no_norm.coeff
        assert_allclose(weights.T.dot(weights), np.eye(100), atol=1e-5)

        pc_10 = PCA(self.x, ncomp=10)
        assert_allclose(pc.factors[:, :10], pc_10.factors)
        assert_allclose(pc.coeff[:10, :], pc_10.coeff)
        assert_allclose(pc.rsquare[:(10 + 1)], pc_10.rsquare)
        assert_allclose(pc.eigenvals[:10], pc_10.eigenvals)
        assert_allclose(pc.eigenvecs[:, :10], pc_10.eigenvecs)

        pc = PCA(self.x, standardize=False, normalize=False)
        mu = self.x.mean(0)
        xdm = self.x - mu
        xpx = xdm.T.dot(xdm)
        val, vec = np.linalg.eigh(xpx)
        ind = np.argsort(val)
        ind = ind[::-1]
        val = val[ind]
        vec = vec[:, ind]
        assert_allclose(xdm, pc.transformed_data)
        assert_allclose(val, pc.eigenvals)
        assert_allclose(np.abs(vec), np.abs(pc.eigenvecs))
        assert_allclose(np.abs(pc.factors), np.abs(xdm.dot(vec)))
        assert_allclose(pc.projection, xdm + mu)

        pc = PCA(self.x, standardize=False, demean=False, normalize=False)
        x = self.x
        xpx = x.T.dot(x)
        val, vec = np.linalg.eigh(xpx)
        ind = np.argsort(val)
        ind = ind[::-1]
        val = val[ind]
        vec = vec[:, ind]
        assert_allclose(x, pc.transformed_data)
        assert_allclose(val, pc.eigenvals)
        assert_allclose(np.abs(vec), np.abs(pc.eigenvecs))
        assert_allclose(np.abs(pc.factors), np.abs(x.dot(vec)))

    def test_against_reference(self):
        """
        Test against MATLAB, which by default demeans but does not standardize        
        """
        x = data.xo / 1000.0
        pc = PCA(x, normalize=False, standardize=False)

        ref = princomp1
        assert_allclose(np.abs(pc.factors), np.abs(ref.factors))
        assert_allclose(pc.factors.dot(pc.coeff) + x.mean(0), x)
        assert_allclose(np.abs(pc.coeff), np.abs(ref.coef.T))
        assert_allclose(pc.factors.dot(pc.coeff),
                        ref.factors.dot(ref.coef.T))

        pc = PCA(x[:20], normalize=False, standardize=False)
        mu = x[:20].mean(0)
        ref = princomp2
        assert_allclose(np.abs(pc.factors), np.abs(ref.factors))
        assert_allclose(pc.factors.dot(pc.coeff) + mu, x[:20])
        assert_allclose(np.abs(pc.coeff), np.abs(ref.coef.T))
        assert_allclose(pc.factors.dot(pc.coeff),
                        ref.factors.dot(ref.coef.T))

    def test_warnings_and_errors(self):
        with warnings.catch_warnings(record=True) as w:
            pc = PCA(self.x, ncomp=300)
            assert_equal(len(w), 1)

        with warnings.catch_warnings(record=True) as w:
            rs = self.rs
            x = rs.standard_normal((200, 1)) * np.ones(200)
            pc = PCA(x, method='eig')
            assert_equal(len(w), 1)

        assert_raises(ValueError, PCA, self.x, method='unknown')
        assert_raises(ValueError, PCA, self.x, missing='unknown')
        assert_raises(ValueError, PCA, self.x, tol=2.0)
        assert_raises(ValueError, PCA, np.nan * np.ones((200,100)), tol=2.0)

    @skipif(missing_matplotlib)
    def test_pandas(self):
        pc = PCA(pd.DataFrame(self.x))
        pc1 = PCA(self.x)
        assert_equal(pc.factors.values, pc1.factors)
        fig = pc.plot_scree()
        fig = pc.plot_scree(ncomp=10)
        fig = pc.plot_scree(log_scale=False)
        fig = pc.plot_rsquare()
        fig = pc.plot_rsquare(ncomp=5)
        proj = pc.project(2)
        PCA(pd.DataFrame(self.x), ncomp=4, gls=True)
        PCA(pd.DataFrame(self.x), ncomp=4, standardize=False)

    def test_gls_and_weights(self):
        assert_raises(ValueError, PCA, self.x, gls=True)
        assert_raises(ValueError, PCA, self.x, weights=np.array([1.0, 1.0]))

        # Pre-standardize to make comparison simple
        x = (self.x - self.x.mean(0))
        x = x / (x ** 2.0).mean(0)
        pc_gls = PCA(x, ncomp=1, standardize=False, demean=False, gls=True)
        pc = PCA(x, ncomp=1, standardize=False, demean=False)
        errors = x - pc.projection
        var = (errors ** 2.0).mean(0)
        weights = 1.0 / var
        weights = weights / np.sqrt((weights ** 2.0).mean())

        assert_allclose(weights, pc_gls.weights)
        assert_equal(x, pc_gls.data)
        assert_equal(x, pc.data)

        pc_weights = PCA(x, ncomp=1, standardize=False, demean=False, weights=weights)

        assert_allclose(weights, pc_weights.weights)
        assert_allclose(np.abs(pc_weights.factors), np.abs(pc_gls.factors))

    def test_wide(self):
        pc = PCA(self.x_wide)
        assert_equal(pc.factors.shape[1], self.x_wide.shape[0])
        assert_equal(pc.eigenvecs.shape[1], min(np.array(self.x_wide.shape)))

        pc = PCA(pd.DataFrame(self.x_wide))
        assert_equal(pc.factors.shape[1], self.x_wide.shape[0])
        assert_equal(pc.eigenvecs.shape[1], min(np.array(self.x_wide.shape)))

    def test_projection(self):
        pc = PCA(self.x, ncomp=5)
        mu = self.x.mean(0)
        demean_x = self.x - mu
        coef = np.linalg.pinv(pc.factors).dot(demean_x)
        direct = pc.factors.dot(coef)
        assert_allclose(pc.projection, direct + mu)

        pc = PCA(self.x, standardize=False, ncomp=5)
        coef = np.linalg.pinv(pc.factors).dot(demean_x)
        direct = pc.factors.dot(coef)
        assert_allclose(pc.projection, direct + mu)

        pc = PCA(self.x, standardize=False, demean=False, ncomp=5)
        coef = np.linalg.pinv(pc.factors).dot(self.x)
        direct = pc.factors.dot(coef)
        assert_allclose(pc.projection, direct)

        pc = PCA(self.x, ncomp=5, gls=True)
        mu = self.x.mean(0)
        demean_x = self.x - mu
        coef = np.linalg.pinv(pc.factors).dot(demean_x)
        direct = pc.factors.dot(coef)
        assert_allclose(pc.projection, direct + mu)

        pc = PCA(self.x, standardize=False, ncomp=5)
        coef = np.linalg.pinv(pc.factors).dot(demean_x)
        direct = pc.factors.dot(coef)
        assert_allclose(pc.projection, direct + mu)

        pc = PCA(self.x, standardize=False, demean=False, ncomp=5, gls=True)
        coef = np.linalg.pinv(pc.factors).dot(self.x)
        direct = pc.factors.dot(coef)
        assert_allclose(pc.projection, direct)

        # Test error for too many factors
        project = pc.project
        assert_raises(ValueError, project, 6)

    def test_replace_missing(self):
        x = self.x.copy()
        x[::5, ::7] = np.nan

        pc = PCA(x, missing='drop-row')
        x_dropped_row = x[np.logical_not(np.any(np.isnan(x), 1))]
        pc_dropped = PCA(x_dropped_row)
        assert_equal(pc.projection, pc_dropped.projection)
        assert_equal(x, pc.data)

        pc = PCA(x, missing='drop-col')
        x_dropped_col = x[:, np.logical_not(np.any(np.isnan(x), 0))]
        pc_dropped = PCA(x_dropped_col)
        assert_equal(pc.projection, pc_dropped.projection)
        assert_equal(x, pc.data)

        pc = PCA(x, missing='drop-min')
        if x_dropped_row.size > x_dropped_col.size:
            x_dropped_min = x_dropped_row
        else:
            x_dropped_min = x_dropped_col
        pc_dropped = PCA(x_dropped_min)
        assert_equal(pc.projection, pc_dropped.projection)
        assert_equal(x, pc.data)

        pc = PCA(x, ncomp=3, missing='fill-em')
        missing = np.isnan(x)
        mu = nanmean(x, axis=0)
        errors = x - mu
        sigma = np.sqrt(nanmean(errors ** 2, axis=0))
        x_std = errors / sigma
        x_std[missing] = 0.0
        last = x_std[missing]
        delta = 1.0
        count = 0
        while delta > 5e-8:
            pc_temp = PCA(x_std, ncomp=3, standardize=False, demean=False)
            x_std[missing] = pc_temp.projection[missing]
            current = x_std[missing]
            diff = current - last
            delta = np.sqrt(np.sum(diff ** 2)) / np.sqrt(np.sum(current ** 2))
            last = current
            count += 1
        x = self.x + 0.0
        projection = pc_temp.projection * sigma + mu
        x[missing] = projection[missing]
        assert_allclose(pc._adjusted_data, x)
        # Check data for no changes
        assert_equal(self.x, self.x_copy)

        x = self.x
        pc = PCA(x)
        pc_dropped = PCA(x, missing='drop-row')
        assert_allclose(pc.projection, pc_dropped.projection, atol=DECIMAL_5)

        pc_dropped = PCA(x, missing='drop-col')
        assert_allclose(pc.projection, pc_dropped.projection, atol=DECIMAL_5)

        pc_dropped = PCA(x, missing='drop-min')
        assert_allclose(pc.projection, pc_dropped.projection, atol=DECIMAL_5)

        pc = PCA(x, ncomp=3)
        pc_dropped = PCA(x, ncomp=3, missing='fill-em')
        assert_allclose(pc.projection, pc_dropped.projection, atol=DECIMAL_5)

        # Test too many missing for missing='fill-em'
        x = self.x.copy()
        x[:, :] = np.nan
        assert_raises(ValueError, PCA, x, missing='drop-row')
        assert_raises(ValueError, PCA, x, missing='drop-col')
        assert_raises(ValueError, PCA, x, missing='drop-min')
        assert_raises(ValueError, PCA, x, missing='fill-em')

    def test_rsquare(self):
        x = self.x + 0.0
        mu = x.mean(0)
        x_demean = x - mu
        std = np.std(x, 0)
        x_std = x_demean / std

        pc = PCA(self.x)
        nvar = x.shape[1]
        rsquare = np.zeros(nvar + 1)
        tss = np.sum(x_std ** 2)
        for i in range(nvar + 1):
            errors = x_std - pc.project(i, transform=False, unweight=False)
            rsquare[i] = 1.0 - np.sum(errors ** 2) / tss
        assert_allclose(rsquare, pc.rsquare)

        pc = PCA(self.x, standardize=False)
        tss = np.sum(x_demean ** 2)
        for i in range(nvar + 1):
            errors = x_demean - pc.project(i, transform=False, unweight=False)
            rsquare[i] = 1.0 - np.sum(errors ** 2) / tss
        assert_allclose(rsquare, pc.rsquare)

        pc = PCA(self.x, standardize=False, demean=False)
        tss = np.sum(x ** 2)
        for i in range(nvar + 1):
            errors = x - pc.project(i, transform=False, unweight=False)
            rsquare[i] = 1.0 - np.sum(errors ** 2) / tss
        assert_allclose(rsquare, pc.rsquare)
