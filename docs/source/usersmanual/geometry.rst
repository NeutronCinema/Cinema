Geometry
==========

.. jupyter-execute::
   :raises:


   from neutron-cinema.Prompt import Launcher, Visualiser
   import matplotlib.pyplot as plt
   import numpy as np
   from neutron-cinema.Interface.Utils import findData
   import os

   inputfile='guide_1.gdml'
   printTraj=False

   if not os.path.isfile(inputfile):
      inputfile=findData(f'gdml/{inputfile}', '.')
      if not os.path.isfile(inputfile):
         raise IOError(f'The input GDML file is not found.')

   myLcher=Launcher()
   myLcher.loadGeometry(inputfile)
   visualize = True
   neutronNum = 100

   if visualize is True:
      v = Visualiser(None, printWorld=False, dumpMesh=True)
      for i in range(int(neutronNum)):
         myLcher.go(1, recordTrj=True)
         if printTraj:
            print(f'trajectory size {myLcher.getTrajSize()}')
         trj = myLcher.getTrajectory()
         try:
               v.addLine(trj)
         except ValueError:
               print("skip ValueError in File '/Prompt/scripts/promptpy', in <module>, v.addLine(trj)")
         if printTraj:
               print(trj)
      v.show()
   else:
      myLcher.go(int(neutronNum), recordTrj=False)

