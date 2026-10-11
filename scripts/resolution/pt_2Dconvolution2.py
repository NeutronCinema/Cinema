#!/usr/bin/env python3
from scipy.signal import unit_impulse
from scipy.signal import convolve, convolve2d
import matplotlib.pyplot as plt
from matplotlib.pyplot import imshow
import numpy as np
import os

aa = 1e-10 #m/aa
cm = 1e-2 #m/cm
const_aa2cm = aa / cm #cm/aa
const_neutron_mass = 1.674e-27 #kg
const_neutron_mass_amu = 1.00866491588
const_c  = 299792458
const_dalton2eVc2 =  931494095.17
const_neutron_mass_evc2 = const_neutron_mass_amu * const_dalton2eVc2 / (const_c*const_c); #[ eV/(Aa/s)^2 ]
const_intensity_inp = 1e6
const_planck = 4.135667662e-15 #eVs
hbar = const_planck * 0.5 / np.pi
pulse_loc = 0.02
sampleLength_z = 0.2 #cm
sample_density_aa3 = (1/3.82779)**3 #per aa3
sample_density_cm3 = sample_density_aa3 / (const_aa2cm**3) #n/aa3 / (cm/aa)^3 = n/cm^3

rangel = 0.11
rangeh = 0.12
e_low = int((rangel - 0.) * 1000)
e_high = int((rangeh - 0.) * 1000)



def get_ein_intergral(w, q, ein, i_inp, sample_density_cm3, sampleLength_z):
    iscat = 0
    for j in np.arange(len(ein)):
        iscat_ein = get_resolution(w, q, ein[j], i_inp[j], sample_density_cm3, sampleLength_z)
        iscat += iscat_ein 
    return iscat

# def get_resolution(w, q, ein, i_inp, sample_density_cm3, sampleLength_z):
#     if ein<=w:
#         return 0 
    
#     eout = ein - w
#     qmax = np.sqrt(ekin2k(eout) ** 2 + ekin2k(ein) ** 2 + 2 * ekin2k(eout) * ekin2k(ein))
#     qmin = np.sqrt(ekin2k(eout) ** 2 + ekin2k(ein) ** 2 - 2 * ekin2k(eout) * ekin2k(ein))
#     if q < qmin or q > qmax:
#         return 0
    
#     rwq = 0
#     numZ = 100
    
#     dz = (sampleLength_z - 0)/ numZ
#     for z in np.linspace(0, sampleLength_z, numZ):
#         # prob_noCollide = get_prob_noCollide(ein, eout, sample_density_cm3, z)
#         prob_collideInZp = get_macroXs(ein, sample_density_cm3, eout) * dz
#         rwq += i_inp * prob_collideInZp 
#         i_inp = i_inp * (1-prob_collideInZp)
#     return rwq

def get_resolution(numw, numq, ein, i_inp, sample_density_cm3, sampleLength_z):
    w = 0
    eout = ein - w
    # qmax = np.sqrt(ekin2k(eout) ** 2 + ekin2k(ein) ** 2 + 2 * ekin2k(eout) * ekin2k(ein))
    # qmin = np.sqrt(ekin2k(eout) ** 2 + ekin2k(ein) ** 2 - 2 * ekin2k(eout) * ekin2k(ein))
    qmax = get_Q(ein, eout, np.pi)
    qmin = get_Q(ein, eout, 0.)
    vq = np.linspace(qmin, qmax, numq)
    va = get_angle(ein, eout, vq)
    # print(va)
    
    vw = np.linspace(-0.1, 0.1, numw)
    # print(vw)
    numZ = 100
    rwq_ = np.zeros((numw, numq-1))
    for ww in np.arange(len(vw)):
        if vw[ww] != 0.:
            rwq_[ww, :] = 0
        else:
            for j in np.arange(len(vq)-1):
                rwq_z = integral_z(ein, eout, i_inp, sample_density_cm3, sampleLength_z, numZ) * (va[j]-va[j+1]) / np.pi
                rwq_[ww, j]=rwq_z
                # print(rwq_[ww, j])
    return vw, vq[1:], rwq_

def integral_z(ein, eout, i_inp, sample_density_cm3, sampleLength_z, numZ):
        dz = (sampleLength_z - 0)/ numZ
        rwq = 0
        for z in np.linspace(0, sampleLength_z, numZ):
            # prob_noCollide = get_prob_noCollide(ein, eout, sample_density_cm3, z)
            prob_collideInZp = get_macroXs(ein, sample_density_cm3, eout) * dz
            rwq += i_inp * prob_collideInZp
            i_inp = i_inp * (1-prob_collideInZp)
        return rwq


def get_Q(ein, eout, angle):
    return np.sqrt(ekin2k(eout) ** 2 + ekin2k(ein) ** 2 - 2 * ekin2k(eout) * ekin2k(ein) * np.cos(angle))

def get_angle(ein, eout, q):
    return np.arccos((q**2 - ekin2k(ein)**2 - ekin2k(eout)**2 ) * 0.5 / ekin2k(ein) / ekin2k(eout))

def ekin2k(ekin):
    return np.sqrt(ekin * 1.0/2.072124652399821e-3)

def get_prob_noCollide(ein, eout, density, z):
    return np.exp(- get_macroXs(ein, density, eout) * z)

def get_macroXs(e_in, density, e_out, Sw=1):
    microXs = np.sqrt(e_out/e_in) * Sw * 1e-24 #cm2
    return density * microXs

def get_scat_kernel(w, q, swq,  w_point, q_point, plot=False):
    from scipy.interpolate import RegularGridInterpolator
    ww, qq = np.meshgrid(w, q)
    f = RegularGridInterpolator((w, q), swq.T)
    # print(f)
    point = np.array([w_point, q_point])
    # print(f(point))
    if plot:
        from matplotlib.pyplot import pcolormesh
        im = pcolormesh(ww, qq, swq, cmap=plt.cm.jet, shading='auto')
        plt.show()
    return f

def plot_swq(w, q, swq, log=False):
    from matplotlib.pyplot import pcolormesh
    import matplotlib.colors as colors
    fig = plt.figure()
    ww, qq = np.meshgrid(w, q)

    if log:
        im = pcolormesh(qq, ww, swq, cmap=plt.cm.jet, norm=colors.LogNorm(vmin=swq.max()*1e-3, vmax=swq.max()), shading='auto')
    else:
        im = pcolormesh(qq, ww, swq, cmap=plt.cm.jet, shading='auto')
    plt.xlabel('q(aa-1)')
    plt.ylabel('w(eV)')
    # plt.legend()
    plt.colorbar(im)

def read_hdf5(file):
    import h5py
    f = h5py.File(file, 'r')
    neutrondata = f['neutron']
    w = neutrondata['energy'][()]
    q = neutrondata['q'][()]
    s = neutrondata['s'][()]
    return w, q, s

def create_delta(w, q, w_point=0.015, q_point=21):
    s = np.zeros((len(w), len(q)))
    index_w = get_cloest_index(w, w_point)
    index_q = get_cloest_index(q, q_point)
    s[index_w, index_q] = 1
    print(index_w, index_q)
    return w, q, s.T
    
def get_cloest_index(arr, value):
    diff = np.absolute(arr-value)
    index = np.argmin(diff)
    return index

def fix_range(w, q, s, ein):
    # print(w * (w<ein))
    qmax = get_Q(ein, ein-w, np.deg2rad(178.))
    qmin = get_Q(ein, ein-w, np.deg2rad(1.))
    s = (qmin<q.reshape((len(q),1)))*(q.reshape((len(q),1))<qmax) * s
    # s = s * np.ones((len(w), len(q))) * w[w>ein]
    return w, q, s

# S(Q,w) table from a phonon calculation: point CINEMA_SQW_FILE at it; when
# unset, fall back to a file of that name in the working directory, with a
# warning.
file = os.environ.get('CINEMA_SQW_FILE')
if not file:
    print('Warning: CINEMA_SQW_FILE is not set - falling back to the '
          "relative default 'c1_vol_77K.h5'")
    file = 'c1_vol_77K.h5'
w, q, s = read_hdf5(file)
print(w.shape, q.shape, w.max())
wf, qf, sf = fix_range(w,q,s,0.1)
qfInd = np.argmin(np.absolute(qf-15))
# plot_swq(wf, qf[:qfInd], sf[:qfInd,:], True)
plot_swq(w, q, s, True)
plt.xlabel(r'Q($\AA^{-1}$)')
plt.ylabel(r'$\omega$(eV)')
plt.title(r"S(Q,$\omega$)")
plt.savefig("test.png")
# w_point = 0.01
# q_point = 20
# get_scat_kernel(w, q, s, w_point, q_point)
# w1, q1, s1 = create_delta(w, q, 0., 0.)

numw = 21
numq = 20
# w_mesh = np.linspace(-0.1, 0.1, numw)
# q_mesh = np.linspace(1.e-1, 20, numq)
# ww, qq= np.meshgrid(w_mesh, q_mesh)
# gres = lambda x, y: get_resolution(x, y, 0.1, 1e6, sample_density_cm3, sampleLength_z)
# rwq = np.array(list(map(gres, ww.ravel(), qq.ravel()))).reshape(numw,numq)
# plot_swq(w_mesh, q_mesh, rwq)
# vw, vq, rwq = get_resolution(numw, numq, 0.1, 1e6, sample_density_cm3, sampleLength_z)
# rwq = np.array(rwq).reshape(49,1)
# print(rwq.sum())
# plot_swq(vw, vq, rwq.T, True)

# iwq = convolve2d(sf, rwq, mode='same')
# plot_swq(wf, qf[:qfInd], iwq[:qfInd,:], True)
# # iwqs = imshow(iwq)
# # plt.colorbar(iwqs)

def moveAxis(axis, deviation):
    for i in range(len(axis)):
        axis[i] = axis[i] + deviation
    return axis

def run():
    e_pulse = int((pulse_loc-0.)*1000)
    sw = unit_impulse(200, e_pulse)
    # print(sw)

    e_axi = np.arange(0,0.2,0.001)
    e_axi2 = np.zeros(len(e_axi))

    # incoming intensity
    i_inp = np.zeros(200)
    rw = np.zeros(200)
    i_ave = const_intensity_inp / (e_high-e_low)
    for i in range(e_low, e_high):
        i_inp[i] = i_ave



    w_axi = np.zeros(200)
    rw = np.zeros(100)
    for w in np.arange(0.,0.1,0.001):
        index = int(w/0.001)
        rw[index]=get_Rw(e_axi, i_inp, w)
    w_axi2 = np.zeros(len(w_axi))
    # iw_scattered = unit_impulse(45, e_pulse) * const_intensity_inp
    # rw = np.zeros(len(iw))
    # rw = np.flip(iw)
    for j in range(len(e_axi)):
        w_axi2[j] = -e_axi[-(j+1)]+pulse_loc
    # print(rw)
    cv = convolve(sw, rw, 'full')

    # plt.plot(e_axi, sw)
    plt.plot(e_axi, i_inp, label='Incident intensity I(E)')
    # plt.plot(e_axi2, rw)
    plt.plot(moveAxis(e_axi[1:101], 0.02), rw, label='Calculated by formulation R(w)')
    # plt.plot(e_axi, iw_scattered)
    # plt.plot(w_axi2, rw, label='Calculated Resolution function R(w)')
    cv_axi = np.arange(0, len(sw)+len(rw)-1) * 0.001 - 0.02
    plt.plot(cv_axi, cv, label='Convolution S*R(w)')
    # plt.plot(cv)
    plt.xticks(np.arange(-0.04,0.4,0.02))
    plt.xlabel('w(eV)')
    plt.ylabel('I')

    # plt.show()


# a = np.array([0,1,0])
# b = np.array([3,2,1,-1])
# c = convolve(a,b,'full')
# print(c)