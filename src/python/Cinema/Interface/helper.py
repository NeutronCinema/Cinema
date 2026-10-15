import numpy as np
from Cinema.Interface.units import *
import time
import multiprocessing
import os
from functools import partial
import h5py
import scipy


try:
    from pyfftw.interfaces import numpy_fft as fft
    import pyfftw
    pyfftw.interfaces.cache.enable()
    # print('using pyfftw for fft')
except ImportError:
    from numpy import fft
    # print('using numpy for fft')

#default units:
#energy eV
#wavelength angstrom
#time second
#wavenumber angstrom^-1
#angle degree
from scipy.signal import kaiserord, lfilter, firwin, freqz
from scipy import interpolate

def takfft(input, dt=1., fftsize=None, conversion=2*np.pi):
    return fft.fftshift(fft.fft((input), n=fftsize))*dt/conversion

def takifft(input, dt=1., fftsize=None, conversion=2*np.pi):
    return fft.fftshift(fft.ifft((input), n=fftsize))/dt*conversion

def findDataUnder(fn, path='/', absPath=False):
    """Walk *path* and return the first full path whose filename matches *fn*.

    *path* is used as-is when absPath=True, otherwise it is prefixed with
    $TAKPATH. Renamed from ``findData``: Cinema.Interface.Utils.findData is
    the canonical locator for the repository data/ tree, and the same-name
    incompatible signature here was a porting trap.
    """
    if absPath:
        pxpath = path
    else:
        takpath = os.getenv('TAKPATH')
        if not takpath:
            raise RuntimeError('findDataUnder needs the TAKPATH environment '
                               'variable when absPath=False; pass absPath=True '
                               'with an explicit path, or use '
                               'Cinema.Interface.Utils.findData for files under '
                               'the repository data/ tree.')
        pxpath = takpath + path
    for root, dirs, files in os.walk(pxpath):
        if fn in files:
            return os.path.join(root, fn)
    raise FileNotFoundError(f'{fn} not found under {pxpath}')

def smooth(input, x):
    sample_rate = 100
    nyq_rate = sample_rate / 2.0
    width = 5.0/nyq_rate
    ripple_db = 100.0
    N, beta = kaiserord(ripple_db, width)
    cutoff_hz = 10.0
    taps = firwin(N, cutoff_hz/nyq_rate, window=('kaiser', beta))
    filtered = lfilter(taps, 1.0, input)
    delay = 0.5 * (N-1) * (x[1]-x[0])
    f = interpolate.interp1d(x[N-1:]-delay , filtered[N-1:], fill_value= 'extrapolate' )
    return f(x)

def smoothVdos(vdos, omega, cut=0.):
    omegaflip = np.flip(omega)
    vdosflip = np.flip(vdos)

    x = np.concatenate((-omegaflip[:-1], omega))
    y = np.concatenate((vdosflip[:-1], vdos))

    ####################################
    sample_rate = 100
    nyq_rate = sample_rate / 2.0
    width = 10.0/nyq_rate
    ripple_db = 120.0 #in dB
    N, beta = kaiserord(ripple_db, width)
    cutoff_hz = 1.0
    taps = firwin(N, cutoff_hz/nyq_rate, window=('kaiser', beta))
    filtered = lfilter(taps, 1.0, y)
    delay = 0.5 * (N-1) * (x[1]-x[0])
    f = interpolate.interp1d(x[12*N-1:]-delay , filtered[12*N-1:], fill_value= 'extrapolate' )
    if (cut):
        omegaSize = int(omega.size*cut)
        return  np.flip(f(omega))[:omegaSize], omega[:omegaSize]
    return (f(omega)), omega
    # return filtered[12*N-1:], x[12*N-1:]-delay


# Note: Cinema.convertor hosts the canonical (C-backed) copies of
# eKin2k/angleCosine2Q and the strict _units wrappers; keep the two
# implementations consistent when editing either.
def angularFre2eKin(fre):
    return fre*radpsec2eV

def eKin2AngularFre(en):
    return en*eV2radpsec

def eKin2k(eV):
    return np.sqrt(eV*eV2kk)

def k2eKin(wn):
    return wn*wn/eV2kk

def q2Alpha(Q, kt):
    return Q*Q/(kt*eV2kk)

def alpha2Q(alpha,kt):
    return np.sqrt(alpha*kt*eV2kk)

def angleCosine2Q(angleCosine, enin_eV, enout_eV):
    ratio = enout_eV/enin_eV
    k0=eKin2k(enin_eV)
    scale = np.sqrt(1.+ ratio - 2*angleCosine*np.sqrt(ratio) )
    return k0*scale
    
def angle2Q(angle_deg, enin_eV, enout_eV):
    ratio = enout_eV/enin_eV
    k0=eKin2k(enin_eV)
    scale = np.sqrt(1.+ ratio - 2*np.cos(angle_deg*deg2rad) *np.sqrt(ratio) )
    return k0*scale

def angle2Alpha(angle, enin_eV, enout_eV, kt):
   return (enin_eV + enout_eV - 2*np.sqrt(enin_eV * enout_eV)*np.cos(angle*deg2rad))/kt

def nextGoodNumber(n):
    return int(2**np.ceil(np.log2(n)))

#fixme: slow
def calHKL(maxNum, jump=1):
    results = {results: [] for results in range(maxNum+1)}
    for h in range(0,maxNum,jump):  # half a space
        for k in range(-maxNum,maxNum,jump):
            for l in range(-maxNum,maxNum,jump):
                if h==0:
                    if k<0:
                        continue #half a plane
                    elif k==0 and l<=0: #half an axis and remove singularity
                        continue
                dis = np.sqrt(h*h + k*k + l*l)
                if dis>maxNum:
                    continue
                if np.abs(dis-round(dis)) < 1e-10:
                    results[int(dis)].append(np.array([h,k,l]))
    return results

def autoCorrSpectrum(rawin, rawin2 = None, n=None):
    if rawin.ndim!=1:
        raise ValueError('input of autoCorrelation must be 1 dimensional')
    if n:
        if rawin.size*2 > n:
            raise ValueError('autoCorrSpectrum: fft length is too small')
        fftsize = n
    else:
        fftsize = rawin.size*2

    #As suggested in G.R. Kneller Comp. Phys. Comm., 1995,
    #input is padded with zero to double the size
    fft1=fft.fft(fft.fftshift(rawin), n=fftsize)
    if rawin2 is not None:
        fft2=fft.fft(fft.fftshift(rawin2), n=fftsize)
        return np.abs(fft.fftshift(((np.conjugate(fft1)*fft2).real)))
    else:
        return np.abs(fft.fftshift(((np.conjugate(fft1)*fft1).real)))

def parallel(func, x, returnNumpy=True):
    pool = multiprocessing.Pool(processes=os.cpu_count())
    result = pool.map(func, x)
    if returnNumpy:
        return np.array(result)
    else:
        return result

def expand(input, axis=0, neg_factor=1., pos_factor=1.):
    s = [slice(None)]*input.ndim
    s[axis] = slice(-2,0,-1)
    return np.concatenate((input[tuple(s)].conjugate()*neg_factor,input*pos_factor),axis=axis)


def fftEvenConjugate( rawin, deltaT=1., scaleFreq = 1., axis=0, halfInput = True, highPrecision = False):
    scale = deltaT/scaleFreq
    if halfInput:
        s = [slice(None)]*rawin.ndim
        s[axis] = slice(-2,0,-1)
        fftin = np.concatenate((rawin[tuple(s)].conjugate(),rawin),axis=axis)
    else:
        fftin = rawin

    s = [np.newaxis]*fftin.ndim
    s[axis] = slice(None)

    if highPrecision:
        fftin = fftin.astype(np.complex256)
    fftout = fft.fftshift(fft.fft(fft.fftshift(fftin, axes=axis),axis=axis),axes=axis)*scale
    if highPrecision:
        fftin = fftin.astype(np.complex128)

    fre=fft.fftshift(fft.fftfreq(fftout.shape[axis]))/scale

    fftSize=fftout.shape[axis]
    s = [slice(None)]*fftin.ndim
    s[axis] = slice(fftSize//4, fftSize//4*3, 1)
    fftout=fftout[tuple(s)]
    fre = fre[fftSize//4:fftSize//4*3]

    return fre, fftout

def nd2str(arr):
    return ' '.join(map(str,arr))

def genLogSpacing(n, estSize, doubleSized = True):
    if doubleSized:
        #array include negtive parts
        idx = np.logspace(0,np.log10(n//2), estSize).astype(np.intp)
        idx=np.unique(idx)#remove repetitive numbers
        upidx=idx+n//2
        upidx=np.insert(idx, 0, 0)#positive idx
        lowidx=np.flip(upidx[0]-idx)
        slicing=np.concatenate((lowidx,upidx))
        slicing-=slicing[0]#index should be start from 0
        return slicing
    else:
        idx = np.logspace(0,np.log10(n), estSize).astype(np.intp)
        idx=np.unique(idx)
        slicing=np.insert(idx, 0, 0) #begin with 0
        return slicing

def minMaxQ(enin_eV, enout_eV):
    if enout_eV.min()<0:
        raise RuntimeError('Negative energy')
    ratio = enout_eV/enin_eV
    k0=eKin2k(enin_eV)
    qmin = k0*np.sqrt(1.+ ratio - 2*np.sqrt(ratio) )
    qmax = k0*np.sqrt(1.+ ratio + 2*np.sqrt(ratio) )
    return qmin, qmax

def incoherentSqw2ncmat(fname, Q, fre, sqw, kt=0.0253, plot=False):
    fo = open(fname, "w")
    header = """NCMAT v2

@DENSITY
  1.0 atoms_per_aa3

@DYNINFO
  element  O
  fraction 1/3
  type     freegas

@DYNINFO
  #dummy small free gas kernel
  element  H
  fraction 2/3
  type     scatknl
  temperature 300

  """

    alpha = q2Alpha(Q, kt)
    beta = (fre*hbar/kt)
    # sqw *= np.exp(-beta*0.5)
    knl = sqw.swapaxes(0,1)*0.5*kt*kt*eV2kk/(2*np.pi)
    if plot:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(alpha, np.trapz(knl.T, beta))
        plt.title('zeroth of sab')
        plt.show()
    print('Zeroth momentum',np.trapz(knl.T, beta))

    fo.write( header )
    fo.write('alphagrid ')
    fo.write(nd2str(alpha))
    fo.write('\n')
    print('Alpha', q2Alpha(Q, kt))
    fo.write('betagrid ')
    fo.write(nd2str(beta))
    fo.write('\n')

    fo.write('sab ')

    for line in knl:
        fo.write(nd2str(line))
        fo.write('\n')

    # sab = nd2str(knl).replace('[', ' ')
    # sab = sab.replace(']', ' ')
    # fo.write(sab)

    fo.close()

def writeDynInfo(fo, element, alpha, beta,  fraction, temperature, knl):
    dynInfo_str = """\n@DYNINFO
              \nelement  {element}
              \nfraction {fraction}
              \ntype     scatknl
              \ntemperature {temperature}
              \nalphagrid {alpha}
              \nbetagrid {beta}
              \nsab """
    fo.write(dynInfo_str.format(alpha=nd2str(alpha), beta=nd2str(beta),
            element=element, fraction=fraction, temperature=temperature))

    for line in knl:
        fo.write(nd2str(line))
        fo.write('\n')
    fo.write('\n')

def gaussSqw2ncmat(fname, density, elements, Qs, fres, sqws, fractions, temperature=293., plot=False):
    kt = temperature*boltzmann

    density_str = """@DENSITY
      {density} atoms_per_aa3\n
      """
    fo = open(fname, "w")
    fo.write('NCMAT v2\n')
    fo.write(density_str.format(density=density))

    for Q, element, fre, sqw, fraction in zip(Qs, elements, fres, sqws, fractions):
        alpha = q2Alpha(Q, kt)
        beta = (fre*hbar/kt)
        knl = sqw.swapaxes(0,1)*0.5*kt*kt*eV2kk/(2*np.pi)

        if plot:
            import matplotlib.pyplot as plt
            plt.figure()
            plt.plot(alpha, np.trapz(knl.T, beta))
            plt.title('zeroth of sab')
            plt.show()

        print('Zeroth momentum for element', element, ':', np.trapz(knl.T, beta))

        writeDynInfo(fo, element, alpha, beta, fraction, temperature, knl)

    fo.close()

def getOmegaFromTime(tsize, dt):
    #angular freqency
    fre = fft.fftshift(fft.fftfreq(tsize, dt))*2*np.pi
    return fre[1]-fre[0], fre


def saveArrInDat(fname,x,y):
    f=open(fname,"w")
    for i in range(x.size):
        f.write("%f %f"%(x[i],y[i]))
        f.write("\n")
    f.close()
#
def saveArrInH5(filename,infoDict,writeType="w"):
    f0=h5py.File(filename,writeType)
    for item in infoDict:
        f0.create_dataset(item, data=infoDict[item], compression="gzip")
    f0.close()

def readArrInH5(filename,nameList):
    dataDict={}
    f0=h5py.File(filename,"r")
    for name in nameList:
        dataDict[name]=f0[name][()]
    f0.close()
    return dataDict

def convOmT(tsize, dt, negtiveAxis=True):
    #angular freqency
    dataRange=2*np.pi/dt
    dataItv=dataRange/(tsize-1)
    data=np.linspace(0,dataRange, tsize)
    if negtiveAxis:
        data=-np.flip(data)
    return dataItv, data

# from scipy.optimize import curve_fit
def Lorentz(x,y0,A,xc,w):
    #y = y0 + (2*A/np.pi)*(w/(4*(x-xc)**2 + w**2))
    y = y0+(2*A/np.pi)*(w/((x-xc)**2 + w**2))
    return y

def Gaussian(x,y0,xc,sigma,height):
    #fwhm=2.355*sigma
    y= y0+height*np.exp(-(x-xc)**2.0/(2*sigma**2))
    return y

def PsdVoigt(x,y0,A,xc,w,mu):
    y = y0+A*(mu*2/np.pi*(w/(4*(x-xc)**2+w**2))+(1-mu)*(np.sqrt(4*np.log(2))/(np.sqrt(np.pi)*w))*np.exp(-(4*np.log(2)/w**2)*(x-xc)**2))
    return y


def seed(begin, num=10):
    x=np.logspace(np.log10(begin),np.log10(begin*np.sqrt(2.)), num)
    #skip the last one, as it can be calc using x[0]**sqrt(2.)
    return x[:-1]

# this function finds a suitable Q to calculate exp(-0.5*Q*Q*gamma)
# by trying to get the maxima of the exponent to a certain value
def findSeed4Gamma(gamma, targetExponent=20., num=10):
    exponentMax = np.max(0.5*np.abs(gamma))
    Qpow = targetExponent/exponentMax
    return seed(np.sqrt(Qpow), num)

def brewSeed(seed, power):
    return seed*np.sqrt(2.)**power

def calBrewNum(seed,qvalue):
    if qvalue<seed[0]:
        s = seed[0]
    else:
        s = seed[-1]
    return int(np.floor(np.log2(qvalue/s))*2)

def interpLog(xraw,yraw,xnew):
    logs = np.log(yraw)
    ynew = np.interp(xnew,xraw,logs)
    return np.exp(ynew)
