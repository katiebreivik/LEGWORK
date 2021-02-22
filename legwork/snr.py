"""Functions to calculate signal-to-noise ratio in four different cases"""

import numpy as np
import legwork.strain as strain
import legwork.lisa as lisa
import legwork.utils as utils
import legwork.evol as evol
import astropy.units as u

__all__ = ['snr_circ_stationary', 'snr_ecc_stationary', 'snr_circ_evolving',
           'snr_ecc_evolving']


def snr_circ_stationary(m_c, f_orb, dist, t_obs, interpolated_g=None,
                        interpolated_sc=None):
    """Computes SNR for circular and stationary sources

    Parameters
    ----------
    m_c : `float/array`
        chirp mass

    f_orb : `float/array`
        orbital frequency

    dist : `float/array`
        distance to the source

    t_obs : `float`
        total duration of the observation

    interpolated_g : `function`
        A function returned by scipy.interpolate.interp2d that
        computes g(n,e) from Peters (1964). The code assumes
        that the function returns the output sorted as with the
        interp2d returned functions (and thus unsorts).
        Default is None and uses exact g(n,e) in this case.

    interpolated_sn : `function`
        A function returned by scipy.interpolate.interp1d that computes the
        LISA sensitivity curve. Default is None and uses exact values. Note:
        take care to ensure that your interpolated function has the same LISA
        observation time as ``t_obs``.

    Returns
    -------
    snr : `float/array`
        snr for each binary
    """

    # only need to compute n=2 harmonic for circular
    h_0_circ_2 = strain.h_0_n(m_c=m_c, f_orb=f_orb,
                              ecc=np.zeros_like(f_orb).value, n=2, dist=dist,
                              interpolated_g=interpolated_g).flatten()**2

    h_f_src_circ_2 = h_0_circ_2 * t_obs
    if interpolated_sc is not None:
        h_f_lisa_2 = interpolated_sc(2 * f_orb)
    else:
        h_f_lisa_2 = lisa.power_spectral_density(f=2 * f_orb, t_obs=t_obs)
    snr = (h_f_src_circ_2 / (4 * h_f_lisa_2))**0.5

    return snr.decompose()


def snr_ecc_stationary(m_c, f_orb, ecc, dist, t_obs, max_harmonic,
                       interpolated_g=None, interpolated_sc=None):
    """Computes SNR for eccentric and stationary sources

    Parameters
    ----------
    m_c : `float/array`
        chirp mass

    f_orb : `float/array`
        orbital frequency

    ecc : `float/array`
        eccentricity

    dist : `float/array`
        distance to the source

    t_obs : `float`
        total duration of the observation

    max_harmonic : `integer`
        maximum integer harmonic to compute

    interpolated_g : `function`
        A function returned by scipy.interpolate.interp2d that
        computes g(n,e) from Peters (1964). The code assumes
        that the function returns the output sorted as with the
        interp2d returned functions (and thus unsorts).
        Default is None and uses exact g(n,e) in this case.

    interpolated_sn : `function`
        A function returned by scipy.interpolate.interp1d that computes the
        LISA sensitivity curve. Default is None and uses exact values. Note:
        take care to ensure that your interpolated function has the same LISA
        observation time as ``t_obs``.

    Returns
    -------
    snr : `float/array`
        snr for each binary
    """
    # define range of harmonics
    n_range = np.arange(1, max_harmonic + 1).astype(int)

    # calculate source signal
    h_0_ecc_n_2 = strain.h_0_n(m_c=m_c, f_orb=f_orb,
                               ecc=ecc, n=n_range, dist=dist,
                               interpolated_g=interpolated_g)**2

    # reshape the output since only one timestep
    h_0_ecc_n_2 = h_0_ecc_n_2.reshape(len(m_c), max_harmonic)
    h_f_src_ecc_2 = h_0_ecc_n_2 * t_obs

    # calculate harmonic frequencies and noise
    f_n = n_range[np.newaxis, :] * f_orb[:, np.newaxis]
    if interpolated_sc is not None:
        h_f_lisa_n_2 = interpolated_sc(f_n.flatten())
        h_f_lisa_n_2 = h_f_lisa_n_2.reshape(f_n.shape)
    else:
        h_f_lisa_n_2 = lisa.power_spectral_density(f=f_n, t_obs=t_obs)

    # calculate the signal-to-noise ratio
    snr = (np.sum(h_f_src_ecc_2 / (4 * h_f_lisa_n_2), axis=1))**0.5
    return snr.decompose()


def snr_circ_evolving(m_1, m_2, f_orb_i, dist, t_obs, n_step,
                      interpolated_g=None, interpolated_sc=None):
    """Computes SNR for circular and stationary sources

    Parameters
    ----------
    m_1 : `float/array`
        primary mass

    m_2 : `float/array`
        secondary mass

    f_orb_i : `float/array`
        initial orbital frequency

    dist : `float/array`
        distance to the source

    t_obs : `float`
        total duration of the observation

    n_step : `int`
        number of time steps during observation duration

    interpolated_g : `function`
        A function returned by scipy.interpolate.interp2d that
        computes g(n,e) from Peters (1964). The code assumes
        that the function returns the output sorted as with the
        interp2d returned functions (and thus unsorts).
        Default is None and uses exact g(n,e) in this case.

    interpolated_sn : `function`
        A function returned by scipy.interpolate.interp1d that computes the
        LISA sensitivity curve. Default is None and uses exact values. Note:
        take care to ensure that your interpolated function has the same LISA
        observation time as ``t_obs``.

    Returns
    -------
    sn : `float/array`
        snr for each binary
    """
    m_c = utils.chirp_mass(m_1=m_1, m_2=m_2)

    # calculate minimum of observation time and merger time
    t_merge = evol.get_t_merge_circ(m_1=m_1,
                                    m_2=m_2,
                                    f_orb_i=f_orb_i)
    t_evol = np.minimum(t_merge, t_obs)

    # get f_orb evolution
    f_orb_evol = evol.evol_circ(t_evol=t_evol,
                                n_step=n_step,
                                m_1=m_1,
                                m_2=m_2,
                                f_orb_i=f_orb_i)

    # calculate the characteristic power
    h_c_n_2 = strain.h_c_n(m_c=m_c,
                           f_orb=f_orb_evol,
                           ecc=np.zeros_like(f_orb_evol).value,
                           n=2,
                           dist=dist,
                           interpolated_g=interpolated_g)**2
    h_c_n_2 = h_c_n_2.reshape(len(m_c), n_step)

    # calculate the characteristic noise power
    if interpolated_sc is not None:
        h_f_lisa_2 = interpolated_sc(2 * f_orb_evol.flatten())
        h_f_lisa_2 = h_f_lisa_2.reshape(f_orb_evol.shape)
    else:
        h_f_lisa_2 = lisa.power_spectral_density(f=2 * f_orb_evol, t_obs=t_obs)
    h_c_lisa_2 = 4 * (2 * f_orb_evol)**2 * h_f_lisa_2

    snr = np.trapz(y=h_c_n_2 / h_c_lisa_2, x=2 * f_orb_evol, axis=1)**0.5

    return snr.decompose()


def snr_ecc_evolving(m_1, m_2, f_orb_i, dist, ecc, max_harmonic, t_obs, n_step,
                     interpolated_g=None, interpolated_sc=None, n_proc=1):
    """Computes SNR for eccentric and evolving sources.

    Note that this function will not work for exactly circular (ecc = 0.0)
    binaries.

    Parameters
    ----------
    m_1 : `float/array`
        primary mass

    m_2 : `float/array`
        secondary mass

    f_orb_i : `float/array`
        initial orbital frequency

    dist : `float/array`
        distance to the source

    ecc : `float/array`
        eccentricity

    max_harmonic : `int`
        maximum integer harmonic to compute

    t_obs : `float`
        total duration of the observation

    n_step : `int`
        number of time steps during observation duration

    interpolated_g : `function`
        A function returned by scipy.interpolate.interp2d that
        computes g(n,e) from Peters (1964). The code assumes
        that the function returns the output sorted as with the
        interp2d returned functions (and thus unsorts).
        Default is None and uses exact g(n,e) in this case.

    interpolated_sn : `function`
        A function returned by scipy.interpolate.interp1d that computes the
        LISA sensitivity curve. Default is None and uses exact values. Note:
        take care to ensure that your interpolated function has the same LISA
        observation time as ``t_obs``.

    n_proc : `int`
        Number of processors to split eccentricity evolution over, where
        the default is n_proc=1

    Returns
    -------
    snr : `array`
        snr for each binary
    """
    m_c = utils.chirp_mass(m_1=m_1, m_2=m_2)
    # calculate minimum of observation time and merger time
    t_merge = evol.get_t_merge_ecc(m_1=m_1, m_2=m_2,
                                   f_orb_i=f_orb_i, ecc_i=ecc)
    t_evol = np.minimum(t_merge, t_obs).to(u.s)

    # get eccentricity and f_orb evolutions
    e_evol, f_orb_evol = evol.evol_ecc(ecc_i=ecc, t_evol=t_evol, n_step=n_step,
                                       m_1=m_1, m_2=m_2, f_orb_i=f_orb_i, n_proc=n_proc)

    # create harmonics list and multiply for nth frequency evolution
    harms = np.arange(1, max_harmonic + 1).astype(int)
    f_n_evol = harms[np.newaxis, np.newaxis, :] * f_orb_evol[..., np.newaxis]

    # calculate the characteristic strain
    h_c_n_2 = strain.h_c_n(m_c=m_c, f_orb=f_orb_evol, ecc=e_evol, n=harms,
                           dist=dist, interpolated_g=interpolated_g)**2

    # calculate the characteristic noise power
    if interpolated_sc is not None:
        h_f_lisa = interpolated_sc(f_n_evol.flatten())
    else:
        h_f_lisa = lisa.power_spectral_density(f=f_n_evol.flatten(),
                                               t_obs=t_obs)
    h_f_lisa = h_f_lisa.reshape(f_n_evol.shape)
    h_c_lisa_2 = 4 * f_n_evol**2 * h_f_lisa

    # integrate, sum and square root to get SNR
    snr_n_2 = np.trapz(y=h_c_n_2 / h_c_lisa_2, x=f_n_evol, axis=1)
    snr_2 = snr_n_2.sum(axis=1)
    snr = np.sqrt(snr_2)

    return snr
