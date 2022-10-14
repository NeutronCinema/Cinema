Geometry
==========

Arbitrary_trapezoid
-------------------

Usage
^^^^^^^^^^
.. jupyter-kernel:: 
    :id: arbitrary_trapezoid

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <arb8 
            lunit="mm" 
            name="Arb8Solid" 
            v1x="-30" v1y="-60" 
            v2x="30" v2y="-60" 
            v3x="50" v3y="60" 
            v4x="-50" v4y="60" 
            v5x="-30" v5y="-60" 
            v6x="30" v6y="-60" 
            v7x="50" v7y="60" 
            v8x="-50" v8y="60" 
            dz="70"
            />

      - ..  jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('arbitrary_trapezoid.gdml')

Parameters
^^^^^^^^^^
 ============= ====================== 
  Parameters    Descriptions          
 ============= ====================== 
  v1x           vertex 1 x position   
  v1y           vertex 1 y position   
  v2x           vertex 2 x position   
  v2y           vertex 2 y position   
  v3x           vertex 3 x position   
  v3y           vertex 3 y position   
  v4x           vertex 4 x position   
  v4y           vertex 4 y position   
  v5x           vertex 5 x position   
  v5y           vertex 5 y position   
  v6x           vertex 6 x position   
  v6y           vertex 6 y position   
  v7x           vertex 7 x position   
  v7y           vertex 7 y position   
  v8x           vertex 8 x position   
  v8y           vertex 8 y position   
  dz            half z length         
 ============= ====================== 


Box
----

Usage
^^^^^
.. jupyter-kernel:: 
    :id: box

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <box 
            lunit="mm" 
            name="BoxSolid" 
            x="100.0" 
            y="100.0" 
            z="100.0" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('box.gdml')

Parameters
^^^^^^^^^
 ============= ============================= 
  Parameters    Descriptions          
 ============= =============================
  x             half length in x direction   
  y             half length in y direction
  z             half length in z direction
 ============= =============================

Cone
----

Usage
^^^^^^
.. jupyter-kernel:: 
    :id: cone

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <cone 
            aunit="deg" 
            lunit="mm" 
            name="ConeSolid" 
            rmin1="0.0" 
            rmax1="50.0" 
            rmin2="0.0" 
            rmax2="10.0" 
            z="120.0" 
            deltaphi="360.0" 
            startphi="0.0" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('cone.gdml')

Parameters
^^^^^^^^^^
 ============= =============================== 
  Parameters    Descriptions                   
 ============= =============================== 
  rmin1         inner radius at base of cone   
  rmax1         outer radius at base of cone   
  rmin2         inner radius at top of cone    
  rmax2         outer radius at top of cone    
  z             height of cone segment         
  startphi      start angle of the segment     
  deltaphi      angle of the segment           
 ============= =============================== 


CutTube
-------

Usage
^^^^^
.. jupyter-kernel:: 
    :id: cutTube

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <cutTube 
            aunit="deg" 
            lunit="mm" 
            name="CutTubeSolid" 
            rmin="0.0" rmax="25.0" 
            z="50.0" 
            deltaphi="360.0" startphi="0.0" 
            lowX="-10" lowY="-10" lowZ="-10" 
            highX="10" highY="10" highZ="10"
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('cutTube.gdml')

Parameters
^^^^^^^^^^
 ============= ============================================= 
  Parameters    Descriptions                                 
 ============= ============================================= 
  z             length along z axis                          
  rmin          inner radius, default 0.0                    
  rmax          outer radius                                 
  startphi      starting phi angle of segment, default 0.0   
  deltaphi      delta phi of angle                           
  lowX          normal at lower z plane                      
  lowY          normal at lower z plane                      
  lowZ          normal at lower z plane                      
  highX         normal at upper z plane                      
  highY         normal at upper z plane                      
  highZ         normal at upper z plane                      
 ============= ============================================= 

Extruded_solid_notsure
-----

Usage
^^^^^
.. jupyter-kernel:: 
    :id: extruded_solid_notsure

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <xtru lunit="mm" name="XtruSolid"  >
                <twoDimVertex x="30" y="90" />
                <twoDimVertex x="10" y="50" />
                <twoDimVertex x="20" y="40" />
                <section 
                zOrder="10" 
                zPosition="20" 
                xOffset="5" 
                yOffset="3" 
                scalingFactor="3" 
                />
                <section 
                zOrder="20" 
                zPosition="50" 
                xOffset="3" 
                yOffset="5" 
                scalingFactor="1" 
                />
            </xtru>

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('extruded_solid_notsure.gdml')

Parameters
^^^^^^^^^^
+---------------------------+----------------+-------------------------------------------------+
| Attributes                | Parameters     | Descriptions                                    |
+===========================+================+=================================================+
|| twoDimVertex:            | x              | x coordinate of the vertex                      |
|| vertices of an           +----------------+-------------------------------------------------+
|| unbound blueprint polygon| y              | y coordinate of the vertex                      |
+---------------------------+----------------+-------------------------------------------------+
| section: z sections       | zOrder         || index of the section, must be between 0 and n-1|
|                           |                || where n is the number of sections              |
|                           +----------------+-------------------------------------------------+
|                           | zPosition      | distance from the plane z=0                     |
|                           +----------------+-------------------------------------------------+
|                           | xOffset        | x offset from centre point of original plane    |
|                           +----------------+-------------------------------------------------+
|                           | yOffset        | y offset from centre point of original plane    |
|                           +----------------+-------------------------------------------------+
|                           | scalingFactor  | proportion to original blueprint                |
+---------------------------+----------------+-------------------------------------------------+


General_trapezoid
-----------------

Usage
^^^^^
.. jupyter-kernel:: 
    :id: general_trapezoid

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <trap 
            lunit="mm" 
            name="TrapSolid" 
            z="130" 
            thata="45" 
            phi="45" 
            y1="60" 
            x1="40" 
            x2="40" 
            alpha1="45" 
            y2="60" 
            x3="40" 
            x4="40" 
            alpha2="45"  
            />
    
      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('general_trapezoid.gdml')

Parameters
^^^^^^^^^^
+-------------+--------------------------------------------------+
| Parameters  | Descriptions                                     |
+=============+==================================================+
| z           | length along z axis                              |
+-------------+--------------------------------------------------+
| theta       | polar angle to faces joining at -/+z             |
+-------------+--------------------------------------------------+
| phi         || azimuthal angle of line                         |
|             || joining centre of –z face to centre of +z face  |
+-------------+--------------------------------------------------+
| y1          | length along y at the face -z                    |
+-------------+--------------------------------------------------+
| x1          | length along x at side y = -y1 of the face at -z |
+-------------+--------------------------------------------------+
| x2          | length along x at side y = +y1 of the face at -z |
+-------------+--------------------------------------------------+
| alpha1      || angle with respect to the y axis                |
|             || from the centre of side at y = -y1              |
|             || to centre of y = +y1 of the face at -z          |
+-------------+--------------------------------------------------+
| y2          | length along y at the face +z                    |
+-------------+--------------------------------------------------+
| x3          | length along x at side y = -y1 of the face at +z |
+-------------+--------------------------------------------------+
| x4          | length along x at side y = +y1 of the face at +z |
+-------------+--------------------------------------------------+
| alpha2      || angle with respect to the y axis                |
|             || from the centre of side at y = -y2              |
|             || to centre of y = +y2 of the face at +z          |
+-------------+--------------------------------------------------+


Hyperbolic_tube
----------------

Usage
^^^^^^
.. jupyter-kernel:: 
    :id: hyperbolic_tube

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <hype 
            lunit="mm" 
            name="HypeSolid" 
            rmin="0" 
            rmax="20" 
            z="100" 
            inst="3" 
            outst="4" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('hyperbolic_tube.gdml')

Parameters
^^^^^^^^^^
 ============= ======================== 
  Parameters    Descriptions            
 ============= ======================== 
  rmin          inside radius of tube   
  rmax          outside radius of tube  
  inst          inner stereo            
  outst         outer stereo            
  z             z length                
 ============= ======================== 

Orb
----

Usage
^^^^^
.. jupyter-kernel:: 
    :id: orb

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <orb 
            lunit="mm" 
            name="OrbSolid" 
            r="50" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('orb.gdml')

Parameters
^^^^^^^^^^
 ============= ======================== 
  Parameters    Descriptions            
 ============= ======================== 
  r             radius         
 ============= ======================== 

Paraboloid
----------

Usage
^^^^^
.. jupyter-kernel:: 
    :id: paraboloid

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <paraboloid 
            lunit="mm" 
            name="ParaboloidSolid" 
            rlo="0.0" 
            rhi="60.0" 
            dz="60.0" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('paraboloid.gdml')

Parameters
^^^^^^^^^^
 ============= =============== 
  Parameters    Descriptions   
 ============= =============== 
  rlo           radius at -z   
  rhi           radius at +z   
  dz            z length       
 ============= =============== 

Polycone
--------

Usage
^^^^^^
.. jupyter-kernel:: 
    :id: polycone

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <polycone 
            aunit="deg" 
            lunit="mm" 
            name="PolyconeSolid" 
            deltaphi="360.0" 
            startphi="0.0" >
                <zplane rmin="10.0" rmax="20.0" z="-50" />
                <zplane rmin="30.0" rmax="50.0" z="60" />
            </polycone>

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('polycone.gdml')

Parameters
^^^^^^^^^^
+-------------+-------------------------------------------------------------+
| Parameters  | Sub-parameters and descriptions                             |
+=============+=============================================================+
| startphi    || start angle of the segment                                 |
|             || if not given 0.0 is defaulted                              |
+-------------+-------------------------------------------------------------+
| deltaphi    | angle of the segment                                        |
+-------------+------+------------------------------------------------------+
| zplane      | rmin || inner radius of cone at this point                  |
|             |      || if not given 0.0 is defaulted                       |
|             +------+------------------------------------------------------+
|             | rmax | outer radius of cone at this point                   |
|             +------+------------------------------------------------------+
|             | z    | z coordinate of the plane                            |
+-------------+------+------------------------------------------------------+

Polyhedra
----------

Usage
^^^^^^
.. jupyter-kernel:: 
    :id: polyhedra

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <polyhedra 
            aunit="deg" 
            lunit="mm" 
            name="PolyhedraSolid" 
            deltaphi="360.0" startphi="0.0" 
            numsides="6" >
                <zplane rmin="0.0" rmax="20.0" z="-50" />
                <zplane rmin="0.0" rmax="50.0" z="60" />
            </polyhedra>

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('polyhedra.gdml')

Parameters
^^^^^^^^^^
+-------------+--------------------------------------------+
| Parameters  | Descriptions                               |
+=============+============================================+
| startphi    | start angle of the segment                 |
+-------------+--------------------------------------------+
| deltaphi    | angle of the segment                       |
+-------------+--------------------------------------------+
| numsides    | number of sides                            |
+-------------+------+-------------------------------------+
| zplane      | rmin || inner radius of cone at this point |
|             |      || if not given 0.0 is defaulted      |
|             +------+-------------------------------------+
|             | rmax | outer radius of cone at this point  |
|             +------+-------------------------------------+
|             | z    | z coordinate of the plane           |
+-------------+------+-------------------------------------+


Sphere
------

Usage
^^^^^
.. jupyter-kernel:: 
    :id: sphere

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <sphere 
            aunit="deg" 
            lunit="mm" 
            name="SphereSolid" 
            rmin="0.0" 
            rmax="60.0" 
            deltaphi="180.0" 
            startphi="0.0" 
            deltatheta="90.0" 
            starttheta="0.0" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('sphere.gdml')

Parameters
^^^^^^^^^^
+-------------+--------------------------------+
| Parameters  | Descriptions                   |
+=============+================================+
| rmin        || inner radius                  |
|             || if not given 0.0 is defaulted |
+-------------+--------------------------------+
| rmax        | outer radius                   |
+-------------+--------------------------------+
| startphi    || starting angle of the segment |
|             || if not given 0.0 is defaulted |
+-------------+--------------------------------+
| deltaphi    | delta angle of the segment     |
+-------------+--------------------------------+
| starttheta  || starting angle of the segment |
|             || if not given 0.0 is defaulted |
+-------------+--------------------------------+
| deltatheta  | delta angle of the segment     |
+-------------+--------------------------------+

Tetrahedron
-----------

Usage
^^^^^

.. jupyter-kernel:: 
    :id: tetrahedron

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <define>
                <position name="v1" x="-70" y="-70" z="-60"/>
                <position name="v2" x="70" y="-40" z="-60"/>
                <position name="v3" x="0.0" y="60" z="-60"/>
                <position name="v4" x="0" y="0" z="60"/>
            </define>
            <tet 
            name="TetrahedronSolid" 
            vertex1="v1" 
            vertex2="v2" 
            vertex3="v3" 
            vertex4="v4"
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('tetrahedron.gdml')

Parameters
^^^^^^^^^^
 ============= ====================== 
  Parameters    Descriptions          
 ============= ====================== 
  vertex1        vertex 1 position   
  vertex2        vertex 2 position   
  vertex3        vertex 3 position   
  vertex4        vertex 4 position   
 ============= ====================== 

Trapezoid
---------

Usage
^^^^^^
.. jupyter-kernel:: 
    :id: trapezoid

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <trd 
            lunit="mm" 
            name="TrdSolid"  
            x1="50" 
            x2="100" 
            y1="60" 
            y2="80" 
            z="130" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('trapezoid.gdml')

Parameters
^^^^^^^^^^
 ============= ================= 
  Parameters    Descriptions     
 ============= ================= 
  x1            x length at -z   
  x2            x length at +z   
  y1            y length at -z   
  y2            y length at +z   
  z             z length         
 ============= ================= 


Tube
-----

Usage
^^^^^
.. jupyter-kernel:: 
    :id: tube

.. list-table::
    :width: 100%

    * - .. code-block:: xml

            <tube
            aunit="deg" 
            lunit="mm" 
            name="TubeSolid" 
            rmin="0.0" 
            rmax="50.0" 
            z="120.0" 
            deltaphi="360.0" 
            startphi="0.0" 
            />

      - .. jupyter-execute:: 
            :raises:
            :hide-code:

            import cinema_plot
            cinema_plot.tutorial('tube.gdml')

Parameters
^^^^^^^^^^
+-------------+-------------------------------------------------------------------------+
| Parameters  | Descriptions                                                            |
+=============+=========================================================================+
| rmin        || inside radius of segment                                               |
|             || if not given 0.0 is defaulted                                          |
+-------------+-------------------------------------------------------------------------+
| rmax        | outside radius of segment                                               |
+-------------+-------------------------------------------------------------------------+
| z           | z length of tube segment                                                |
+-------------+-------------------------------------------------------------------------+
| startphi    || starting phi position angle of segment                                 |
|             || if not given 0.0 is defaulted                                          |
+-------------+-------------------------------------------------------------------------+
| deltaphi    | delta angle of segment                                                  |
+-------------+-------------------------------------------------------------------------+

