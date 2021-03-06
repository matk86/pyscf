#!/usr/bin/env python

import unittest
import numpy
from pyscf import gto
from pyscf import scf
from pyscf import df
from pyscf import ao2mo
from pyscf import mcscf

b = 1.4
mol = gto.M(
verbose = 5,
output = '/dev/null',
atom = [
    ['N',(  0.000000,  0.000000, -b/2)],
    ['N',(  0.000000,  0.000000,  b/2)], ],
basis = {'N': 'ccpvdz', },
max_memory = 1,
)
m = scf.RHF(mol)
m.conv_tol = 1e-9
m.scf()

molsym = gto.M(
verbose = 5,
output = '/dev/null',
atom = [
    ['N',(  0.000000,  0.000000, -b/2)],
    ['N',(  0.000000,  0.000000,  b/2)], ],
basis = {'N': 'ccpvdz', },
max_memory = 1,
symmetry = True,
)
msym = scf.RHF(molsym)
msym.conv_tol = 1e-9
msym.scf()


class KnowValues(unittest.TestCase):
    def test_mc1step_4o4e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(m, 4, 4))
        emc = mc.mc1step()[0]
        self.assertAlmostEqual(emc, -108.913786407955, 7)
        self.assertAlmostEqual(numpy.linalg.norm(mc.analyze()),
                               2.7015375913946591, 4)

    def test_mc2step_4o4e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(m, 4, 4))
        emc = mc.mc2step()[0]
        self.assertAlmostEqual(emc, -108.913786407955, 7)
        self.assertAlmostEqual(numpy.linalg.norm(mc.analyze()),
                               2.7015375913946591, 4)

    def test_mc1step_6o6e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(m, 6, 6))
        emc = mc.mc1step()[0]
        self.assertAlmostEqual(emc, -108.980105451388, 7)

    def test_mc2step_6o6e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(m, 6, 6))
        emc = mc.mc2step()[0]
        self.assertAlmostEqual(emc, -108.980105451388, 7)

    def test_mc1step_symm_4o4e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(msym, 4, 4))
        emc = mc.mc1step()[0]
        self.assertAlmostEqual(emc, -108.913786407955, 7)
        self.assertAlmostEqual(numpy.linalg.norm(mc.analyze()),
                               2.7015375913946591, 4)

    def test_mc2step_symm_4o4e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(msym, 4, 4))
        emc = mc.mc2step()[0]
        self.assertAlmostEqual(emc, -108.913786407955, 7)
        self.assertAlmostEqual(numpy.linalg.norm(mc.analyze()),
                               2.7015375913946591, 4)

    def test_mc1step_symm_6o6e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(msym, 6, 6))
        emc = mc.mc1step()[0]
        self.assertAlmostEqual(emc, -108.980105451388, 7)

    def test_mc2step_symm_6o6e(self):
        mc = mcscf.density_fit(mcscf.CASSCF(msym, 6, 6))
        emc = mc.mc2step()[0]
        self.assertAlmostEqual(emc, -108.980105451388, 7)

    def test_casci_4o4e(self):
        mc = mcscf.CASCI(m, 4, 4)
        emc = mc.casci()[0]
        self.assertAlmostEqual(emc, -108.8896744464714, 7)
        self.assertAlmostEqual(numpy.linalg.norm(mc.analyze()),
                               2.6910276344981119, 4)

    def test_casci_symm_4o4e(self):
        mc = mcscf.CASCI(msym, 4, 4)
        emc = mc.casci()[0]
        self.assertAlmostEqual(emc, -108.8896744464714, 7)
        self.assertAlmostEqual(numpy.linalg.norm(mc.analyze()),
                               2.6910276344981119, 4)

#    def test_casci_uhf(self):
#        mf = scf.UHF(mol)
#        mf.scf()
#        mc = mcscf.CASCI(mf, 4, 4)
#        emc = mc.casci()[0]
#        self.assertAlmostEqual(emc, -108.8896744464714, 7)
#        self.assertAlmostEqual(numpy.linalg.norm(mc.analyze()), 0, 7)
#
#    def test_casci_uhf(self):
#        mf = scf.UHF(mol)
#        mf.scf()
#        mc = mcscf.density_fit(mcscf.CASSCF(mf, 4, 4))
#        emc = mc.mc1step()[0]
#        self.assertAlmostEqual(emc, -108.913786407955, 7)
#        emc = mc.mc2step()[0]
#        self.assertAlmostEqual(emc, -108.913786407955, 7)

    def test_df_ao2mo(self):
        mf = scf.density_fit(msym)
        mf.max_memory = 100
        mf.kernel()
        mc = mcscf.CASSCF(mf, 4, 4)
        eri0 = numpy.dot(mf._cderi.T, mf._cderi)
        nmo = mc.mo_coeff.shape[1]
        ncore = mc.ncore
        nocc = ncore + mc.ncas
        eri0 = ao2mo.restore(1, ao2mo.kernel(eri0, mc.mo_coeff), nmo)
        eris = mc.ao2mo(mc.mo_coeff)
        self.assertTrue(numpy.allclose(eri0[:,:,ncore:nocc,ncore:nocc], eris.ppaa))
        self.assertTrue(numpy.allclose(eri0[:,ncore:nocc,:,ncore:nocc], eris.papa))

if __name__ == "__main__":
    print("Full Tests for density fitting N2")
    unittest.main()

