import numpy as np
import legwork.utils as utils
import unittest
from scipy import integrate

from astropy import units as u


class Test(unittest.TestCase):
    """Tests that the code is functioning properly"""

    def test_keplers_laws(self):
        """check converters are working properly"""

        n_vals = 10000
        f_orb = 10**(np.random.uniform(-5, -1, n_vals)) * u.Hz
        m_1 = np.random.uniform(0, 50, n_vals) * u.Msun
        m_2 = np.random.uniform(0, 50, n_vals) * u.Msun

        # convert frequency to semi-major axis
        a = utils.get_a_from_f_orb(f_orb, m_1, m_2)

        # convert back to frequency
        should_be_f_orb = utils.get_f_orb_from_a(a, m_1, m_2)

        self.assertTrue(np.allclose(f_orb, should_be_f_orb))

    def test_bad_input(self):
        """check functions can deal with bad input"""
        n_vals = 10000
        f_orb_i = 10**(np.random.uniform(-5, -1, n_vals)) * u.Hz
        ecc_i = np.zeros(n_vals)
        m_1 = np.random.uniform(0, 50, n_vals) * u.Msun
        m_2 = np.random.uniform(0, 50, n_vals) * u.Msun

        # check the function doesn't crash if you don't give the chirp mass
        utils.determine_stationarity(f_orb_i=f_orb_i, t_evol=4 * u.yr,
                                     ecc_i=ecc_i, m_1=m_1, m_2=m_2)

        # check that it *does* crash when no masses supplied
        no_worries = True
        try:
            utils.determine_stationarity(f_orb_i=f_orb_i, t_evol=4 * u.yr,
                                         ecc_i=ecc_i)
        except ValueError:
            no_worries = False
        self.assertFalse(no_worries)

    def test_average_response(self):
        """make sure that response integrals are correct"""
        # based on Flanagan and Hughes 1998, the average responses <F_plus^2 a_plus^2>
        # and <F_cross^2 a_cross^2>, when averaged over the position (theta, phi),
        # polarization (psi) and inclination (inc) are equal to 1/5

        def integrand(theta, phi, psi, inc):
            intgl1 = 1 / (4 * np.pi) * (1 / (np.pi)) *\
                     utils.F_plus_squared(theta=theta, phi=phi, psi=psi) *\
                     np.sin(theta) * (1 + np.cos(inc) ** 2) / 2 * np.sin(inc)
            intgl2 = 1 / (4 * np.pi) * (1 / (np.pi)) *\
                     utils.F_cross_squared(theta=theta, phi=phi, psi=psi) *\
                     np.sin(theta) * (np.cos(inc)) * np.sin(inc)

            intgl = intgl1 + intgl2
            return intgl

        result, error = integrate.nquad(
            integrand,
            [[0, np.pi],  # theta
             [0, 2 * np.pi],  # phi
             [0, 2 * np.pi],  # psi
             [0, np.pi]])  # inc

        self.assertAlmostEqual(result, 2/5)
