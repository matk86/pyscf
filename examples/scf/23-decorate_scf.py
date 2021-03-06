#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import numpy
from pyscf import gto
from pyscf import scf

'''
Mixing decoration, for density fitting, scalar relativistic effects, and
second order (Newton-Raphson) SCF.

Density fitting and scalar relativistic effects can be applied together,
regardless to the order you apply the decoration.

NOTE the second order SCF (New in version 1.1) decorating operation are not
commutable with scf.density_fit operation
        [scf.density_fit, scf.sfx2c      ] == 0
        [scf.newton     , scf.sfx2c      ] == 0
        [scf.newton     , scf.density_fit] != 0
* scf.density_fit(scf.newton(scf.RHF(mol))) is the SOSCF for regular 2e
  integrals, but with density fitting integrals for the Hessian.  It's an
  approximate SOSCF optimization method;
* scf.newton(scf.density_fit(scf.RHF(mol))) is the exact second order
  optimization for the given scf object which is a density-fitted-scf method.
  The SOSCF is not an approximate scheme.
* scf.density_fit(scf.newton(scf.density_fit(scf.RHF(mol))), auxbasis='ahlrichs')
  is an approximate SOSCF scheme for the given density-fitted-scf method.
  Here we use small density fitting basis (ahlrichs cfit basis) to approximate
  the Hessian for the large-basis-density-fitted-scf scheme.
'''

mol = gto.Mole()
mol.build(
    verbose = 0,
    atom = '''8  0  0.     0
              1  0  -0.757 0.587
              1  0  0.757  0.587''',
    basis = 'ccpvdz',
)

mf = scf.density_fit(scf.sfx2c(scf.RHF(mol)))
energy = mf.kernel()
print('E = %.12f, ref = -76.075115837941' % energy)

mf = scf.sfx2c(scf.density_fit(scf.RHF(mol)))
energy = mf.kernel()
print('E = %.12f, ref = -76.075115837941' % energy)

mo_init = mf.eig(mf.get_hcore(), mf.get_ovlp())[1]
mocc_init = numpy.zeros(mo_init.shape[1])
mocc_init[:mol.nelectron//2] = 2

mf = scf.newton(scf.RHF(mol))
energy = mf.kernel(mo_init, mocc_init)
print('E = %.12f, ref = -76.026765673091' % energy)

mf = scf.density_fit(scf.newton(scf.RHF(mol)))
energy = mf.kernel(mo_init, mocc_init)
print('E = %.12f, ref = -76.026765673091' % energy)

mf = scf.newton(scf.density_fit(scf.RHF(mol)))
energy = mf.kernel(mo_init, mocc_init)
print('E = %.12f, ref = -76.025936299674' % energy)

mf = scf.density_fit(scf.newton(scf.density_fit(scf.RHF(mol))), 'ahlrichs')
energy = mf.kernel(mo_init, mocc_init)
print('E = %.12f, ref = -76.025936299674' % energy)

