#!/usr/bin/env python

## \file run_adjoint.py
#  \brief Python script to launch SU2_CFD_AD
#  \author Ruben Sanchez
#  \version 6.2.0 "Falcon"
#
# The current SU2 release has been coordinated by the
# SU2 International Developers Society <www.su2devsociety.org>
# with selected contributions from the open-source community.
#
# The main research teams contributing to the current release are:
#  - Prof. Juan J. Alonso's group at Stanford University.
#  - Prof. Piero Colonna's group at Delft University of Technology.
#  - Prof. Nicolas R. Gauger's group at Kaiserslautern University of Technology.
#  - Prof. Alberto Guardone's group at Polytechnic University of Milan.
#  - Prof. Rafael Palacios' group at Imperial College London.
#  - Prof. Vincent Terrapon's group at the University of Liege.
#  - Prof. Edwin van der Weide's group at the University of Twente.
#  - Lab. of New Concepts in Aeronautics at Tech. Institute of Aeronautics.
#
# Copyright 2012-2019, Francisco D. Palacios, Thomas D. Economon,
#                      Tim Albring, and the SU2 contributors.
#
# SU2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# SU2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with SU2. If not, see <http://www.gnu.org/licenses/>.

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import sys
import shutil
from optparse import OptionParser	# use a parser for configuration
import pysu2ad as pysu2          # imports the SU2 adjoint-wrapped module
from math import *

# -------------------------------------------------------------------
#  Main 
# -------------------------------------------------------------------

def main():

  # Command line options
  parser=OptionParser()
  parser.add_option("-f", "--file", dest="filename", help="Read config from FILE", metavar="FILE")
  parser.add_option("--nDim", dest="nDim", default=2, help="Define the number of DIMENSIONS",
                    metavar="DIMENSIONS")
  parser.add_option("--nZone", dest="nZone", default=1, help="Define the number of ZONES",
                    metavar="ZONES")
  parser.add_option("--parallel", action="store_true",
                    help="Specify if we need to initialize MPI", dest="with_MPI", default=False)

  parser.add_option("--fsi", dest="fsi", default="False", help="Launch the FSI driver", metavar="FSI")

  parser.add_option("--fem", dest="fem", default="False", help="Launch the FEM driver (General driver)", metavar="FEM")

  parser.add_option("--harmonic_balance", dest="harmonic_balance", default="False",
                    help="Launch the Harmonic Balance (HB) driver", metavar="HB")


  (options, args) = parser.parse_args()
  options.nDim  = int( options.nDim )
  options.nZone = int( options.nZone )
  options.fsi = options.fsi.upper() == 'TRUE'
  options.fem = options.fem.upper() == 'TRUE'
  options.harmonic_balance = options.harmonic_balance.upper() == 'TRUE'

  # Import mpi4py for parallel run
  if options.with_MPI == True:
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
  else:
    comm = 0 
    rank = 0

  # Initialize the corresponding driver of SU2, this includes solver preprocessing
  try:
    SU2Driver = pysu2.CDiscAdjSinglezoneDriver(options.filename, options.nZone, comm);
  except TypeError as exception:
    print('A TypeError occured in pysu2.CDriver : ',exception)
    if options.with_MPI == True:
      print('ERROR : You are trying to initialize MPI with a serial build of the wrapper. Please, remove the --parallel option that is incompatible with a serial build.')
    else:
      print('ERROR : You are trying to launch a computation without initializing MPI but the wrapper has been built in parallel. Please add the --parallel option in order to initialize MPI for the wrapper.')
    return

  MarkerID = None
  MarkerName = 'wallF'       # Specified by the user

  # Get all the boundary tags
  MarkerList = SU2Driver.GetAllBoundaryMarkersTag()

  # Get all the markers defined on this rank and their associated indices.
  allMarkerIDs = SU2Driver.GetAllBoundaryMarkers()

  #Check if the specified marker exists and if it belongs to this rank.
  if MarkerName in MarkerList and MarkerName in allMarkerIDs.keys():
    MarkerID = allMarkerIDs[MarkerName]

  # Number of vertices on the specified marker (per rank)
  nVertex_Marker = 0         #total number of vertices (physical + halo)
  nVertex_Marker_HALO = 0    #number of halo vertices
  nVertex_Marker_PHYS = 0    #number of physical vertices

  if MarkerID != None:
    nVertex_Marker = SU2Driver.GetNumberVertices(MarkerID)
    nVertex_Marker_HALO = SU2Driver.GetNumberHaloVertices(MarkerID)
    nVertex_Marker_PHYS = nVertex_Marker - nVertex_Marker_HALO

  # Time loop is defined in Python so that we have acces to SU2 functionalities at each time step
  if rank == 0:
    print("\n------------------------------ Begin Solver -----------------------------\n")
  sys.stdout.flush()
  if options.with_MPI == True:
    comm.Barrier()

  # Time iteration preprocessing
  SU2Driver.Preprocess(0)
  
  # Run one time-step (static: one simulation)
  SU2Driver.Run()
  
  # Postprocess
  SU2Driver.Postprocess()  
  
  # Update the solver for the next time iteration
  SU2Driver.Update()
  
  # Monitor the solver and output solution to file if required
  stopCalc = SU2Driver.Monitor(0)
  
  # Output the solution to file
  SU2Driver.Output(0)
  
  # Sensitivities of the marker
  print("\n------------------------------ Sensitivities -----------------------------\n")  
  for iVertex in range(nVertex_Marker):
    sensX, sensY, sensZ = SU2Driver.GetMeshDisp_Sensitivity(MarkerID, iVertex)
    
    if (iVertex == 30):
      print(1000,1000,iVertex, sensX, sensY, sensZ)

  # Postprocess the solver and exit cleanly
  SU2Driver.Postprocessing()

  if SU2Driver != None:
    del SU2Driver

  

# -------------------------------------------------------------------
#  Run Main Program
# -------------------------------------------------------------------

# this is only accessed if running from command prompt
if __name__ == '__main__':
    main()  