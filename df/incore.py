#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import copy
import time
import ctypes
import _ctypes
import numpy
import scipy.linalg
import pyscf.lib
from pyscf.lib import logger
from pyscf import gto
from pyscf.df import _ri

libri = pyscf.lib.load_library('libri')
def _fpointer(name):
    return ctypes.c_void_p(_ctypes.dlsym(libri._handle, name))

def format_aux_basis(mol, auxbasis='weigend'):
    '''Generate a fake Mole object which uses the density fitting auxbasis as
    the basis sets
    '''
    pmol = copy.copy(mol)  # just need shallow copy
    if isinstance(auxbasis, str):
        uniq_atoms = set([a[0] for a in mol._atom])
        pmol._basis = pmol.format_basis(dict([(a, auxbasis)
                                              for a in uniq_atoms]))
    else:
        pmol._basis = pmol.format_basis(auxbasis)
    pmol._atm, pmol._bas, pmol._env = \
            pmol.make_env(mol._atom, pmol._basis, mol._env[:gto.PTR_ENV_START])
    pmol.natm = len(pmol._atm)
    pmol.nbas = len(pmol._bas)
    pmol._built = True
    logger.debug(mol, 'aux basis %s, num shells = %d, num cGTO = %d',
                 auxbasis, pmol.nbas, pmol.nao_nr())
    return pmol


# (ij|L)
def aux_e2(mol, auxmol, intor='cint3c2e_sph', aosym='s1', comp=1, hermi=0,
           mol1=None):
    '''3-center AO integrals (ij|L), where L is the auxiliary basis.
    '''
    atm, bas, env = gto.mole.conc_env(mol._atm, mol._bas, mol._env,
                                      auxmol._atm, auxmol._bas, auxmol._env)
    if 'cart' in intor:
        iloc = jloc = _ri.make_loc(0, mol.nbas, _ri._cgto_cart(bas))
    else:
        iloc = jloc = _ri.make_loc(0, mol.nbas, _ri._cgto_spheric(bas))
    if mol1 is None:
        basrange = (0, mol.nbas, 0, mol.nbas, mol.nbas, auxmol.nbas)
    else:
# Append mol1 next to auxmol
        atm, bas, env = gto.mole.conc_env(atm, bas, env,
                                          mol1._atm, mol1._bas, mol1._env)
        basrange = (0, mol.nbas, mol.nbas+auxmol.nbas, mol1.nbas,
                    mol.nbas, auxmol.nbas)
        jloc = _ri.make_loc(0, mol1.nbas, _ri._cgto_spheric(mol1._bas))
    eri = _ri.nr_auxe2(intor, basrange,
                       atm, bas, env, aosym, comp, iloc=iloc, jloc=jloc)
    return eri


# (L|ij)
def aux_e1(mol, auxmol, intor='cint3c2e_sph', aosym='s1', comp=1, hermi=0):
    '''3-center 2-electron AO integrals (L|ij), where L is the auxiliary basis.
    '''
    eri = aux_e2(mol, auxmol, intor, aosym, comp, hermi)
    naux = eri.shape[1]
    return pyscf.lib.transpose(eri.reshape(-1,naux))


def fill_2c2e(mol, auxmol, intor='cint2c2e_sph'):
    '''2-center 2-electron AO integrals (L|ij), where L is the auxiliary basis.
    '''
    c_atm = numpy.asarray(auxmol._atm, dtype=numpy.int32, order='C')
    c_bas = numpy.asarray(auxmol._bas, dtype=numpy.int32, order='C')
    c_env = numpy.asarray(auxmol._env, dtype=numpy.double, order='C')
    natm = ctypes.c_int(c_atm.shape[0])
    nbas = ctypes.c_int(c_bas.shape[0])

    naoaux = auxmol.nao_nr()
    eri = numpy.empty((naoaux,naoaux))
    libri.RInr_fill2c2e_sph(eri.ctypes.data_as(ctypes.c_void_p),
                            ctypes.c_int(0), ctypes.c_int(auxmol.nbas),
                            c_atm.ctypes.data_as(ctypes.c_void_p), natm,
                            c_bas.ctypes.data_as(ctypes.c_void_p), nbas,
                            c_env.ctypes.data_as(ctypes.c_void_p))
    return eri


def cholesky_eri(mol, auxbasis='weigend', verbose=0):
    '''
    Returns:
        2D array of (naux,nao*(nao+1)/2) in C-contiguous
    '''
    t0 = (time.clock(), time.time())
    if isinstance(verbose, logger.Logger):
        log = verbose
    else:
        log = logger.Logger(mol.stdout, verbose)
    auxmol = format_aux_basis(mol, auxbasis)

    j2c = fill_2c2e(mol, auxmol, intor='cint2c2e_sph')
    log.debug('size of aux basis %d', j2c.shape[0])
    t1 = log.timer('2c2e', *t0)
    low = scipy.linalg.cholesky(j2c, lower=True)
    j2c = None
    t1 = log.timer('Cholesky 2c2e', *t1)

    j3c = aux_e2(mol, auxmol, intor='cint3c2e_sph', aosym='s2ij')
    t1 = log.timer('3c2e', *t1)
    cderi = scipy.linalg.solve_triangular(low, j3c.T, lower=True,
                                          overwrite_b=True)
    j3c = None
    # solve_triangular return cderi in Fortran order
    cderi = pyscf.lib.transpose(cderi.T)
    log.timer('cholesky_eri', *t0)
    return cderi



if __name__ == '__main__':
    from pyscf import scf
    from pyscf import ao2mo
    mol = gto.Mole()
    mol.verbose = 0
    mol.output = None

    mol.atom.extend([
        ["H", (0,  0, 0  )],
        ["H", (0,  0, 1  )],
    ])
    mol.basis = 'cc-pvdz'
    mol.build()

    auxmol = format_aux_basis(mol)
    j3c = aux_e2(mol, auxmol, intor='cint3c2e_sph', aosym='s1')
    nao = mol.nao_nr()
    naoaux = auxmol.nao_nr()
    j3c = j3c.reshape(nao,nao,naoaux)

    atm, bas, env = \
            gto.mole.conc_env(mol._atm, mol._bas, mol._env,
                              auxmol._atm, auxmol._bas, auxmol._env)
    eri0 = numpy.empty((nao,nao,naoaux))
    pi = 0
    for i in range(mol.nbas):
        pj = 0
        for j in range(mol.nbas):
            pk = 0
            for k in range(mol.nbas, mol.nbas+auxmol.nbas):
                shls = (i, j, k)
                buf = gto.moleintor.getints_by_shell('cint3c2e_sph',
                                                     shls, atm, bas, env)
                di, dj, dk = buf.shape
                eri0[pi:pi+di,pj:pj+dj,pk:pk+dk] = buf
                pk += dk
            pj += dj
        pi += di
    print(numpy.allclose(eri0, j3c))

    j2c = fill_2c2e(mol, auxmol)
    eri0 = numpy.empty_like(j2c)
    pi = 0
    for i in range(mol.nbas, len(bas)):
        pj = 0
        for j in range(mol.nbas, len(bas)):
            shls = (i, j)
            buf = gto.moleintor.getints_by_shell('cint2c2e_sph',
                                                 shls, atm, bas, env)
            di, dj = buf.shape
            eri0[pi:pi+di,pj:pj+dj] = buf
            pj += dj
        pi += di
    print(numpy.allclose(eri0, j2c))

    j3c = aux_e2(mol, auxmol, intor='cint3c2e_sph', aosym='s2ij')
    cderi = cholesky_eri(mol)
    eri0 = numpy.einsum('pi,pk->ik', cderi, cderi)
    eri1 = numpy.einsum('ik,kl->il', j3c, numpy.linalg.inv(j2c))
    eri1 = numpy.einsum('ip,kp->ik', eri1, j3c)
    print(numpy.allclose(eri1, eri0))
    eri0 = pyscf.ao2mo.restore(1, eri0, nao)

    mf = scf.RHF(mol)
    ehf0 = mf.scf()

    nao = mf.mo_energy.size
    eri1 = ao2mo.restore(1, mf._eri, nao)
    print(numpy.linalg.norm(eri1-eri0))

    mf._eri = ao2mo.restore(8, eri0, nao)
    ehf1 = mf.scf()

    mf = scf.density_fit(scf.RHF(mol))
    ehf2 = mf.scf()
    print(ehf0, ehf1, ehf2)
