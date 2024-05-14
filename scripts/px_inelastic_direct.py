#!/usr/bin/env python3

import os
import logging
logging.basicConfig(filename='px_inel_dir.log', level=logging.INFO, format='%(asctime)s %(message)s')
logging.info('Starting a new calculation')
    
# Set environment variables
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['EUPHONIC_NUM_THREADS'] = '1'


import numpy as np
np.set_printoptions(suppress=True)
from Cinema.PiXiu.io.cell import QeXmlCell
import phonopy
import matplotlib.pyplot as plt
import pickle
import argparse
from Cinema.Interface.units import *
from Cinema.PiXiu.AtomInfo import getAtomMassBC
from phonopy.structure.brillouin_zone import BrillouinZone, get_qpoints_in_Brillouin_zone
import euphonic.util as util

import tqdm

from time import time
import vegas

def dumpObj2File(fn, obj):
    f = open (fn, 'wb')
    pickle.dump(obj, f)
    f.close()

class CohPhon:
    def __init__(self, yamlfile = 'phonopy.yaml', cellQeRelaxXml='out_relax.xml', temperature=300., en_cut = 1e-4) -> None:
        self.ph = phonopy.load(phonopy_yaml=yamlfile, log_level=1, symmetrize_fc=True)
        self.cell = QeXmlCell(cellQeRelaxXml) # this should be changed to the experimental crystal size for production runs
        self.pos=self.cell.reduced_pos.dot(self.cell.lattice)
        self.mass, self.bc, num = self.cell.getAtomInfo()
        self.sqMass = np.sqrt(self.mass)
        self.nAtom = len(self.sqMass)
        logging.info(f'lattice: {self.cell.lattice}')
        logging.info(f'reciprocal lattice: {self.cell.lattice_reci}')

        if any(self.ph.get_unitcell().get_atomic_numbers() != num):
            raise RuntimeError('Different unitcell in the DFT and phonon calculation ')

        self.temperature = temperature
        self.en_cut=en_cut
        meshsize = 100.
        self.ph.run_mesh(meshsize, is_mesh_symmetry=False, with_eigenvectors=True)
        self.ph.run_thermal_displacement_matrices(self.temperature, self.temperature+1, 2, freq_min=0.002)
        # get_thermal_displacement_matrices returns the temperatures and thermal_displacement_matrices
        self.disp = np.copy(self.ph.get_thermal_displacement_matrices()[1][0])
        Q=np.array([0,0,1])
        omega = np.copy(self.ph.get_mesh_dict()['frequencies'])
        self.maxHistEn = omega.max()*THz*2*np.pi*hbar + 0.005 #add 5meV as the energy margin

        import euphonic as eu
        self.eu = eu.ForceConstants.from_phonopy(summary_name='phonopy.yaml',
                                                fc_name='force_constants.hdf5',
                                                fc_format='hdf5')
        
        q_grid = util.mp_grid([11,11,11])
        phonons_grid = self.eu.calculate_qpoint_phonon_modes(q_grid, asr='reciprocal')
        # Now calculate the Debye-Waller exponent
        temperature = temperature*eu.ureg('K')
        dw = phonons_grid.calculate_debye_waller(temperature)
        self.disp = dw.debye_waller.to('angstrom ** 2').magnitude




    def getGammaPoint(self, Qin):
        Q = np.atleast_2d(Qin)
        Qred = self.cell.qabs2reduced(Q)
        ceil = np.ceil(Qred)
        floor = np.floor(Qred)

        gamma = np.zeros((len(Q), 3))

        for i, (low, up) in enumerate(zip(floor, ceil)):
            gpoints_reduced = np.array([[low[0], low[1], low[2]],
                                [low[0], low[1], up[2]],
                                [low[0], up[1], low[2]],
                                [low[0], up[1], up[2]],
                                [up[0], low[1], low[2]],
                                [up[0], low[1], up[2]],
                                [up[0], up[1], low[2]],
                                [up[0], up[1], up[2]]])
            gpoints = self.cell.qreduced2abs(gpoints_reduced)
            dist = gpoints-Q[i]
            dist = (dist*dist).sum(axis=1)
            # print('dist', dist, np.argmin(dist) )
            gamma[i] = gpoints[np.argmin(dist)]
        return gamma

    def calcMesh(self, meshsize):
        # # using iterator 
        # ph.init_mesh(10., is_mesh_symmetry=False, with_eigenvectors=True, use_iter_mesh=True)
        # for item in ph._mesh:
        #     q = ph._mesh._qpoints[ph._mesh._q_count-1]
        #     print('item',q, item)

        # keys are 'qpoints', 'weights', 'frequencies', 'eigenvectors'
        self.ph.run_mesh(meshsize, is_mesh_symmetry=False, with_eigenvectors=True)
        return self.ph.get_mesh_dict()
       
    def _calcPhonon(self, k):
        reducedK=self.cell.qabs2reduced(np.asarray(k))
        p = self.eu.calculate_qpoint_phonon_modes(reducedK, use_c=True, asr='reciprocal', n_threads=1)#, useparallel=False)
        return p.frequencies.magnitude*1e-3, p.eigenvectors

    
    def _calcFormFact(self, Qarr, eigvecss, en, tau=None):
        # note, W = 0.5*Q*Q*u*u = 0.5*Q*Q*MSD

        # w =  -0.5 * Q.dot(np.swapaxes( Q.dot(self.disp), 1,2 ) )
        # print(w)

        F = np.zeros((Qarr.shape[0], self.nAtom*3))
        
        for i, (Q, eigvec) in enumerate(zip(Qarr, eigvecss)):
            w =  - np.dot(np.dot(self.disp, Q), Q)

            # for testing
            # print('w', w, -0.5*self.disp[0,0,0]*np.linalg.norm(Q)**2)
            # print(self.disp[0])

            #summing for all atoms, F for each mode
            F[i]=np.abs((self.bc/self.sqMass * np.exp(w + 1j*self.pos.dot(Q)) *eigvec.dot(Q)).sum(axis=1))

        # print('eigvec', eigvec[1])
        n = 1./(np.exp(en/(self.temperature*boltzmann))-1.)
        return F*hbar*np.sqrt( (n+1)/en )
    
    def s(self, Qin, reduced=False):
        if reduced:
            Q = self.cell.qreduced2abs(np.asarray(Qin))
        else:
            Q = np.asarray(Qin)

        if Q.ndim==1: 
            Q= np.expand_dims(Q, axis = 0)

        en, eigvec = self._calcPhonon(Q)

        tinyphon = en < self.en_cut # in eV, cufoof small or negtive phonons
        en[tinyphon] = self.temperature*boltzmann # replease small phonon energy to a sensible value to avoid diveded by zero RuntimeWarning
        eigvec[tinyphon] = 1.
        
        Qmag = np.linalg.norm(Q, axis=1)  
        F = self._calcFormFact(Q, eigvec, en)

        # the unit is per atoms by not per reciprocal volume
        Smag = 0.5*F*F
        if tinyphon.any(): # fill zero for small phonons
            Smag[tinyphon] = 0.               

        return Qmag, en, Smag/self.nAtom # per atom  

class kernel(vegas.BatchIntegrand):
    def __init__(self, omegaBin=30, temp=300.) -> None:
        self.calc =  CohPhon(temperature=temp)
        self.omegaRange = [0, self.calc.maxHistEn] 
        self.bin = omegaBin

    def __call__(self, input):
        # x: rho, theta(0, 2pi), phi (0, pi)
        x=np.atleast_2d(input)
        r=x[:,0]#*self.rDelta + self.rmin
        theta=x[:,1]
        phi=x[:,2]
        
        # https://mathworld.wolfram.com/SphericalCoordinates.html
        sin_theta=np.sin(theta)
        cos_theta=np.cos(theta)
        sin_phi=np.sin(phi)
        cos_phi=np.cos(phi)

        pos = np.zeros_like(x)
        pos[:, 0] = cos_theta*sin_phi
        pos[:, 1] = sin_theta*sin_phi
        pos[:, 2] = cos_phi
        pos = (pos.T*r).T
        
        Q, en, S = self.calc.s(pos)
        if (S<0.).any():
            print('S<0.', pos, S)
            raise RuntimeError()

        factor = r*r*sin_phi        
        contr = (S.T*factor).T
        contr[np.isnan(contr)]=0.
        I = contr.sum(axis=1)
        
        # return I        
        dI = np.zeros((I.size, self.bin))
        for i in range(I.size):
            dI[i], _ = np.histogram(en[i], bins=self.bin, range=self.omegaRange, weights=contr[i])

        return dict(I=I, dI=dI)


def gen_parser():
    #parameters
    #temperature in kelvin
    #upper limit for the Q, maxQ, float
    #frequency bin size for the histogram, freSize, int
    #Q bin size for the histogram, QSize, int
    #stepping for the hkl, int
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--temperature', action='store', type=float,
                        dest='temp', help='temperature in kelvin', required=True)
    parser.add_argument('-l', '--lower-limit-Q', action='store', type=float, default=0.0,
                        dest='minQ', help='lower limit for the Q')
    parser.add_argument('-u', '--upper-limit-Q', action='store', type=float, default=10.0,
                        dest='maxQ', help='upper limit for the Q')
    parser.add_argument('-q', '--Q-bin-size', action='store', type=int, default=300,
                        dest='QSize', help='Q bin size for the histogram')
    parser.add_argument('-e', '--en-bin-size', action='store', type=int, default=200,
                        dest='enSize', help='energy bin size for the histogram')
    parser.add_argument('-o', '--output-file-name', action='store', default='qehist.h5',
                        dest='output', help='output file name')
    parser.add_argument('-n', '--neval', action='store', type=float, default=10000,
                    dest='neval', help='number of evaluation pre iterations')
    parser.add_argument('-p', '--partitions', action='store', type=int, default=1,
                    dest='partitions', help='number of partitions.')
    parser.add_argument('-s', '--save', action='store_true', dest='save', help='save vegas pickles')

    return parser
    
args=gen_parser().parse_args()
temp = args.temp #temperature in kelvin
minQ = args.minQ
maxQ = args.maxQ
enSize = args.enSize
qSize = args.QSize
output = args.output
partitions = args.partitions
neval=int(args.neval)
   

qEdge=np.linspace(minQ, maxQ, qSize+1)
Q = qEdge[:-1]+np.diff(qEdge)*0.5

# per reciprocal space
q_volume = qEdge**3*np.pi*4/3. # spher volumes
q_volume_diff = np.diff(q_volume)


k = kernel(enSize, temp)
enEdge = np.linspace(0, k.calc.maxHistEn, enSize+1 )
en = enEdge[:-1]+np.diff(enEdge)*0.5
# per energy
en_diff = np.diff(en).mean()
sqw = np.zeros([qSize, enSize])
sdev = np.zeros_like(sqw)


def run(i, save=False):
    logging.info(f'Launching the {i}th integration in the Q range of ({qEdge[i]:.3f}, {qEdge[i+1]:.3f}) ')
    logging.debug('run', i, k, k.calc)
    
    t1 = time()
    sqw_at_q = np.zeros(enSize)
    sdev_at_q = np.zeros_like(sqw_at_q)
    integ =  vegas.Integrator([[qEdge[i], qEdge[i+1]], [0, np.pi], [0, np.pi]])

    integ(k, nitn=10, neval=neval)
    result = integ(k, nitn=10, neval=neval, adapt = False)

    if save:
        dumpObj2File(f'result_{i}.pkl', result)

    for j in range(enSize):
        sqw_at_q[j] = (result['dI'][j]).mean
        sdev_at_q[j] = (result['dI'][j]).sdev

    scale = 4./(q_volume_diff[i]*en_diff) # factor 4 is because of the theata is only in the range between 0 and pi 
    sqw_at_q *= scale
    sdev_at_q *= scale 

    s=f'Run {i}: Q range ({qEdge[i]:.3f}, {qEdge[i+1]:.3f}), mean {np.mean([qEdge[i], qEdge[i+1]]):.3f},  executed in {(time()-t1):.2f}s, I=', result['I'], f', chi2={result.chi2/result.dof:.2f}, Q={result.Q:.4f} \n'
    logging.info(s)
    return sqw_at_q, sdev_at_q


from multiprocessing import Pool

if __name__ == '__main__':

    pool = Pool(partitions)
    start_time = time()

    with pool:        
        for i, res in enumerate(tqdm.tqdm(pool.imap(run, range(qSize)), total=qSize)):
            sqw[i] = res[0]
            sdev[i] = res[1]

    finish_time = time()
    logging.info(f"Program finished in {finish_time-start_time} seconds")



    # save data 
    import h5py
    f0=h5py.File(output,"w")

    ## coherent 
    f0.create_dataset("q", data=Q, compression="gzip")
    f0.create_dataset("en", data=en, compression="gzip")
    f0.create_dataset("s", data=sqw, compression="gzip")
    f0.create_dataset("sdev", data=sdev, compression="gzip")
    f0.close()


    import matplotlib.pyplot as plt
    import matplotlib.colors as colors
    from Cinema.Interface import plotStyle
    plotStyle()
    fig=plt.figure()
    ax = fig.add_subplot(111)
    H = sqw.T

    X, Y = np.meshgrid(Q, en)
    pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet, shading='auto')
    fig.colorbar(pcm, ax=ax)
    plt.grid()
    plt.savefig(fname='lin.pdf')

    fig=plt.figure()
    ax = fig.add_subplot(111)
    pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet, norm=colors.LogNorm(vmin=H.max()*1e-3, vmax=H.max()), shading='auto')
    fig.colorbar(pcm, ax=ax)
    plt.grid()
    plt.savefig(fname='log.pdf')

    # plt.show()
