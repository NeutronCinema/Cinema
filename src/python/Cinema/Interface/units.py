import numpy as np

aa = 1.
mm = 1.e7*aa
cm = 1.e8*aa
m = 1.e10*aa
barn = 1e-24*cm**2
fm = 1.e-13*cm
au = 0.529177249*aa

K = 1.
eV = 1.
MeV = 1e6*eV
meV = 1e-3*eV

s = 1.
ps = s*1e-12
fs = s*1e15
THz=1e12/s

c = 299792458*m/s
umass = 931.494095*MeV/c**2
kb = 8.6173324e-5*eV/K

planck = 4.13566769692386e-15  #(source: NIST/CODATA 2018) [eV*s]
hbar = planck*0.5/np.pi  #[eV*s]6.582119569509068e-16
radpsec2eV = hbar
eV2radpsec = 1./radpsec2eV
radpsec2meV = radpsec2eV*1e3
radpfs2meV = radpsec2meV*1e15

deg2rad = np.pi/180.
eV2kk = 1/2.072124652399821e-3
dalton2kg =  1.660539040e-27  # amu to kg (source: NIST/CODATA 2018)
dalton2eVc2 =  931494095.17  # amu to eV/c^2 (source: NIST/CODATA 2018)
avogadro = 6.022140857e23  # mol^-1 (source: NIST/CODATA 2018)
boltzmann = 8.6173303e-5   # eV/K
neutron_mass = 1.674927471e-24  #gram
neutron_mass_evc2 = 1.0454075098625835e-28  #eV/(Aa/s)^2
neutron_atomic_mass = 1.00866491588  #atomic unit
atomic_mass = neutron_mass_evc2/neutron_atomic_mass
ekin2v = np.sqrt(2.0/neutron_mass_evc2)  #multiply with sqrt(ekin) to get velocity in Aa/s
