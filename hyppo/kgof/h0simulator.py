from __future__ import division

from builtins import str, range, object
from past.utils import old_div

import autograd.numpy as np
from ._utils import outer_rows
from .base import GofTest
from .fssd import FSSD, list_simulate_spectral
from abc import ABC, abstractmethod
import logging

import scipy
import scipy.stats as stats
from numpy.random import default_rng


class H0Simulator(ABC):
    """
    An abstract class representing a simulator to draw samples from the
    null distribution. For some tests, these are needed to conduct the test.
    """

    def __init__(self, n_simulate, seed):
        """
        n_simulate: The number of times to simulate from the null distribution.
            Must be a positive integer.
        seed: a random seed

        From: https://github.com/wittawatj/fsic-test
        """
        assert n_simulate > 0
        self.n_simulate = n_simulate
        self.seed = seed

    @abstractmethod
    def simulate(self, gof, X):
        """
        gof: a GofTest
        dat: a Data (observed data)
        Simulate from the null distribution and return a dictionary.
        One of the item is
            sim_stats: a numpy array of stats.

        From: https://github.com/wittawatj/fsic-test
        """
        raise NotImplementedError()


class FSSDH0SimCovObs(H0Simulator):
    """
    An asymptotic null distribution simulator for FSSD.  Simulate from the
    asymptotic null distribution given by the weighted sum of chi-squares. The
    eigenvalues (weights) are computed from the covarince matrix wrt. the
    observed sample.
    This is not the correct null distribution; but has the correct asymptotic
    types-1 error at alpha.
    """

    def __init__(self, n_simulate=3000, seed=10):
        super(FSSDH0SimCovObs, self).__init__(n_simulate, seed)

    def simulate(self, gof, X, fea_tensor=None):
        """
        fea_tensor: n x d x J feature matrix
        """
        assert isinstance(gof, FSSD)
        n_simulate = self.n_simulate
        seed = self.seed
        if fea_tensor is None:
            _, fea_tensor = gof.statistic(X, return_feature_tensor=True)

        J = fea_tensor.shape[2]
        n = X.shape[0]
        # n x d*J
        Tau = fea_tensor.reshape(n, -1)
        # Make sure it is a matrix i.e, np.cov returns a scalar when Tau is
        # 1d.
        cov = np.cov(Tau.T) + np.zeros((1, 1))
        # cov = Tau.T.dot(Tau/n)

        arr_nfssd, eigs = list_simulate_spectral(cov, J, n_simulate, seed=self.seed)
        return {"sim_stats": arr_nfssd}


class FSSDH0SimCovDraw(H0Simulator):
    """
    An asymptotic null distribution simulator for FSSD.  Simulate from the
    asymptotic null distribution given by the weighted sum of chi-squares. The
    eigenvalues (weights) are computed from the covarince matrix wrt. the
    sample drawn from p (the density to test against).

    - The UnnormalizedDensity p is required to implement get_datasource() method.

    From: https://github.com/wittawatj/fsic-test
    """

    def __init__(self, n_draw=2000, n_simulate=3000, seed=10):
        """
        n_draw: number of samples to draw from the UnnormalizedDensity p
        """
        super(FSSDH0SimCovDraw, self).__init__(n_simulate, seed)
        self.n_draw = n_draw

    def simulate(self, gof, fea_tensor=None):
        """
        fea_tensor: n x d x J feature matrix
        This method does not use dat.

        From: https://github.com/wittawatj/fsic-test
        """
        # p = an UnnormalizedDensity
        p = gof.p
        ds = p.get_datasource()
        if ds is None:
            raise ValueError("DataSource associated with p must be available.")
        Xdraw = ds.sample(n=self.n_draw, seed=self.seed)
        _, fea_tensor = gof.statistic(Xdraw, return_feature_tensor=True)

        X = Xdraw
        J = fea_tensor.shape[2]
        n = self.n_draw
        # n x d*J
        Tau = fea_tensor.reshape(n, -1)
        # Make sure it is a matrix i.e, np.cov returns a scalar when Tau is
        # 1d.
        cov = old_div(Tau.T.dot(Tau), n) + np.zeros((1, 1))
        n_simulate = self.n_simulate

        arr_nfssd, eigs = list_simulate_spectral(cov, J, n_simulate, seed=self.seed)
        return {"sim_stats": arr_nfssd}
