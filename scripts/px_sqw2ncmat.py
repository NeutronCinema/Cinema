#!/usr/bin/env python3

import numpy as np
const_eV2kk = 1/2.072124652399821e-3
const_hbar = 6.582119569509068e-16
from Cinema.Interface import plotStyle

plotStyle()

import h5py
filename = 'qehist.h5'

with h5py.File(filename, "r") as f:
    en = f['en'][()]
    q = f['q'][()]
    sqw = f['s'][()]

kt = 0.0253
sqw *= np.exp(-0.5*en/kt)

en = np.append([0.], en)
sqw=np.concatenate((np.zeros([q.size, 1]), sqw), axis=1)


#################################################################################
import matplotlib.pyplot as plt
fig=plt.figure()
ax = fig.add_subplot(111)
H = sqw.T

X, Y = np.meshgrid(q, en)
import matplotlib.colors as colors
pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet,  norm=colors.LogNorm(vmin=H.max()*1e-4, vmax=H.max()),)
fig.colorbar(pcm, ax=ax)
plt.xlabel('Q, Aa^-1')
plt.ylabel('energy, eV')

# def flip(rawin, axis=0, factor=1.):
#     s = [slice(None)]*rawin.ndim
#     s[axis] = slice(-2,0,-1)
#     return  np.concatenate((rawin, rawin[tuple(s)]*factor),axis=axis)


# sqw = flip(sqw.T, 1, np.exp(-en[(en.size-1):-1]/kt) ).T
# # sqw=np.concatenate((sqw, upScatSqw),axis=1)

# en = flip(en,factor=-1)


#################################################################################

# enSize=100
# QSize=250
# maxQ=15

# #################################################################################
# import matplotlib.pyplot as plt
# fig=plt.figure()
# ax = fig.add_subplot(111)
# H = d2.T

# X, Y = np.meshgrid(q, en)
# import matplotlib.colors as colors
# pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet,  norm=colors.LogNorm(vmin=H.max()*1e-4, vmax=H.max()),)
# fig.colorbar(pcm, ax=ax)
# plt.xlabel('Q, Aa^-1')
# plt.ylabel('energy, eV')
# #################################################################################

        
def sqw2sab(sqw, Q, en, kt):
    alpha = Q*Q/(kt*const_eV2kk)
    beta = en/kt
    sab = sqw*0.5*kt*kt*const_eV2kk#/(2*np.pi)
    return sab, alpha, beta

sab, alpha, beta = sqw2sab(sqw, q, en, kt)
knl={}
knl['alphagrid'] = alpha
knl['betagrid'] = beta
knl['sab_scaled'] = sab

print(alpha.shape, beta.shape, sab.shape)
#################################################################################
import matplotlib.pyplot as plt
fig=plt.figure()
ax = fig.add_subplot(111)
H = sab.T

X, Y = np.meshgrid(alpha, beta)
pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet)#,  norm=colors.LogNorm(vmin=H.max()*1e-4, vmax=H.max()),)
fig.colorbar(pcm, ax=ax)
plt.xlabel('alpha')
plt.ylabel('beta')
plt.show()
#################################################################################


sumrule = []
for i in range(alpha.size):
    sumrule.append(np.trapz(sab[i], beta))
print(alpha)
plt.plot(alpha, sumrule )
plt.show()

import NCrystal.ncmat as ncncmat
import pathlib
_res="""NCMAT v5

@STATEOFMATTER
  liquid
  
@DENSITY
  1.0 atoms_per_aa3

@DYNINFO
  element  Si
  fraction 1
  type     scatknl
  temperature 300
  """
for n in ('alphagrid','betagrid','sab_scaled'):
    _res += ncncmat.formatVectorForNCMAT(n,knl[n])#NB: Hoping for no entries like 0r100 
pathlib.Path('cohsgl.ncmat').write_text(_res)
