# -*- coding: utf-8 -*-

from __future__ import division, print_function

from itertools import product

import numpy as np

import pytest

from emcee import backends, EnsembleSampler

__all__ = ["test_backend", "test_reload"]

all_backends = backends.get_test_backends()[1:]
dtypes = [
    None,
    [("log_prior", float), ("mean", int)]
]


def normal_log_prob(params):
    return -0.5 * np.sum(params**2), 0.1, int(5)


def run_sampler(backend, nwalkers=32, ndim=3, nsteps=25, seed=1234, thin_by=1,
                dtype=None):
    if seed is not None:
        np.random.seed(seed)
    coords = np.random.randn(nwalkers, ndim)
    sampler = EnsembleSampler(nwalkers, ndim, normal_log_prob,
                              backend=backend, blobs_dtype=dtype)
    sampler.run_mcmc(coords, nsteps, thin_by=thin_by)
    return sampler


def _custom_allclose(a, b):
    if a.dtype.fields is None:
        assert np.allclose(a, b)
    else:
        for n in a.dtype.names:
            assert np.allclose(a[n], b[n])


@pytest.mark.parametrize("backend,dtype", product(all_backends, dtypes))
def test_backend(backend, dtype):
    # Run a sampler with the default backend.
    sampler1 = run_sampler(backends.Backend(), dtype=dtype)

    with backend() as be:
        sampler2 = run_sampler(be, dtype=dtype)

        # Check all of the components.
        for k in ["chain", "log_prob", "blobs"]:
            a = getattr(sampler1, "get_" + k)()
            b = getattr(sampler2, "get_" + k)()
            _custom_allclose(a, b)

        last1 = sampler1.get_last_sample()
        last2 = sampler2.get_last_sample()
        assert len(last1) == len(last2)
        assert np.allclose(last1[0], last2[0])
        assert np.allclose(last1[1], last2[1])
        assert all(np.allclose(l1, l2) for l1, l2 in zip(last1[2][1:],
                                                         last2[2][1:]))
        _custom_allclose(last1[3], last2[3])

        a = sampler1.acceptance_fraction
        b = sampler2.acceptance_fraction
        assert np.allclose(a, b), "inconsistent acceptance fraction"


@pytest.mark.parametrize("backend,dtype", product(all_backends, dtypes))
def test_reload(backend, dtype):
    with backend() as backend1:
        run_sampler(backend1, dtype=dtype)

        # Test the state
        state = backend1.random_state
        np.random.set_state(state)

        # Load the file using a new backend object.
        backend2 = backends.HDFBackend(backend1.filename, backend1.name,
                                       read_only=True)

        with pytest.raises(RuntimeError):
            backend2.reset(32, 3)

        assert state[0] == backend2.random_state[0]
        assert all(np.allclose(a, b)
                   for a, b in zip(state[1:], backend2.random_state[1:]))

        # Check all of the components.
        for k in ["chain", "log_prob", "blobs"]:
            a = backend1.get_value(k)
            b = backend2.get_value(k)
            _custom_allclose(a, b)

        last1 = backend1.get_last_sample()
        last2 = backend2.get_last_sample()
        assert len(last1) == len(last2)
        assert np.allclose(last1[0], last2[0])
        assert np.allclose(last1[1], last2[1])
        assert all(np.allclose(l1, l2) for l1, l2 in zip(last1[2][1:],
                                                         last2[2][1:]))
        _custom_allclose(last1[3], last2[3])

        a = backend1.accepted
        b = backend2.accepted
        assert np.allclose(a, b), "inconsistent accepted"


@pytest.mark.parametrize("backend,dtype", product(all_backends, dtypes))
def test_restart(backend, dtype):
    # Run a sampler with the default backend.
    b = backends.Backend()
    run_sampler(b, dtype=dtype)
    sampler1 = run_sampler(b, seed=None, dtype=dtype)

    with backend() as be:
        run_sampler(be, dtype=dtype)
        sampler2 = run_sampler(be, seed=None, dtype=dtype)

        # Check all of the components.
        for k in ["chain", "log_prob", "blobs"]:
            a = getattr(sampler1, "get_" + k)()
            b = getattr(sampler2, "get_" + k)()
            _custom_allclose(a, b)

        last1 = sampler1.get_last_sample()
        last2 = sampler2.get_last_sample()
        assert len(last1) == len(last2)
        assert np.allclose(last1[0], last2[0])
        assert np.allclose(last1[1], last2[1])
        assert all(np.allclose(l1, l2) for l1, l2 in zip(last1[2][1:],
                                                         last2[2][1:]))
        _custom_allclose(last1[3], last2[3])

        a = sampler1.acceptance_fraction
        b = sampler2.acceptance_fraction
        assert np.allclose(a, b), "inconsistent acceptance fraction"
