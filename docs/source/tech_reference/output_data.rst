Schemas
=======

attr_data_final
---------------

Final attribute data for all catchments after regionalization.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - divide_id
     - object
     - False

   * - is_donor
     - bool
     - False

   * - hlr_AQPERMNEW
     - float64
     - True

   * - hlr_TAVE
     - float64
     - True

   * - hlr_PPT
     - float64
     - True

   * - hlr_PET
     - float64
     - True

   * - hlr_PMPE
     - float64
     - True

   * - hlr_SAND
     - float64
     - True

   * - streamcat_BFI
     - float64
     - False

   * - streamcat_CanalDens
     - float64
     - False

   * - streamcat_DamDens
     - float64
     - False

   * - streamcat_DamNIDStor
     - float64
     - False

   * - streamcat_DamNrmStor
     - float64
     - False

   * - streamcat_Elev
     - float64
     - False

   * - streamcat_Perm
     - float64
     - False

   * - streamcat_Om
     - float64
     - False

   * - streamcat_RckDep
     - float64
     - False

   * - streamcat_WtDep
     - float64
     - False

   * - streamcat_AgKffact
     - float64
     - False

   * - streamcat_Kffact
     - float64
     - False

   * - streamcat_PctAlkIntruVol
     - float64
     - False

   * - streamcat_PctAlluvCoast
     - float64
     - False

   * - streamcat_PctCarbResid
     - float64
     - False

   * - streamcat_PctCoastCrs
     - float64
     - False

   * - streamcat_PctColluvSed
     - float64
     - False

   * - streamcat_PctEolCrs
     - float64
     - False

   * - streamcat_PctEolFine
     - float64
     - False

   * - streamcat_PctExtruVol
     - float64
     - False

   * - streamcat_PctGlacLakeCrs
     - float64
     - False

   * - streamcat_PctGlacLakeFine
     - float64
     - False

   * - streamcat_PctGlacTilClay
     - float64
     - False

   * - streamcat_PctGlacTilCrs
     - float64
     - False

   * - streamcat_PctGlacTilLoam
     - float64
     - False

   * - streamcat_PctHydric
     - float64
     - False

   * - streamcat_PctNonCarbResid
     - float64
     - False

   * - streamcat_PctSalLake
     - float64
     - False

   * - streamcat_PctSilicic
     - float64
     - False

   * - streamcat_PctWater
     - float64
     - False

   * - streamcat_Precip
     - float64
     - False

   * - streamcat_Tmax
     - float64
     - False

   * - streamcat_Tmean
     - float64
     - False

   * - streamcat_Tmin
     - float64
     - False

   * - streamcat_RdDens
     - float64
     - False

   * - streamcat_Runoff
     - float64
     - False

   * - streamcat_Clay
     - float64
     - False

   * - streamcat_Sand
     - float64
     - False

   * - streamcat_Precip_Minus_EVT
     - float64
     - False




formulations
------------

Formulation assignments for all catchments.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - vpu
     - object
     - False

   * - divide_id
     - object
     - False

   * - formulation
     - object
     - False

   * - huc_id
     - object
     - False

   * - total_score
     - float64
     - False

   * - summary_score
     - float64
     - False

   * - cost
     - int64
     - False

   * - num_gages
     - int64
     - False

   * - upscale_huc
     - object
     - False




formulations_pars
-----------------

Formulation parameters for all catchments.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - gage_id
     - object
     - False

   * - formulation
     - object
     - False

   * - MFSNO
     - float64
     - False

   * - CWP
     - float64
     - False

   * - VCMX25
     - float64
     - False

   * - MP
     - float64
     - False

   * - RSURF_SNOW
     - float64
     - False

   * - RSURF_EXP
     - float64
     - False

   * - SCAMAX
     - float64
     - False

   * - b
     - float64
     - True

   * - satdk
     - float64
     - True

   * - satpsi
     - float64
     - True

   * - slope
     - float64
     - True

   * - maxsmc
     - float64
     - True

   * - wltsmc
     - float64
     - True

   * - max_gw_storage
     - float64
     - True

   * - Cgw
     - float64
     - True

   * - expon
     - float64
     - True

   * - Kn
     - float64
     - True

   * - Klf
     - float64
     - True

   * - refkdt
     - float64
     - True

   * - mfmax
     - float64
     - True

   * - uadj
     - float64
     - True

   * - si
     - float64
     - True

   * - mfmin
     - float64
     - True

   * - scf
     - float64
     - True

   * - nmf
     - float64
     - True

   * - tipm
     - float64
     - True

   * - pxtemp
     - float64
     - True

   * - plwhc
     - float64
     - True

   * - daygm
     - float64
     - True

   * - smcmin
     - float64
     - True

   * - smcmax
     - float64
     - True

   * - van_genuchten_alpha
     - float64
     - True

   * - van_genuchten_n
     - float64
     - True

   * - hydraulic_conductivity
     - float64
     - True

   * - ponded_depth_max
     - float64
     - True

   * - field_capacity
     - float64
     - True

   * - df
     - float64
     - True

   * - cc
     - float64
     - True

   * - hcan
     - float64
     - True

   * - lai
     - float64
     - True

   * - subalb
     - float64
     - True

   * - ems
     - float64
     - True

   * - cg
     - float64
     - True

   * - zo
     - float64
     - True

   * - rho
     - float64
     - True

   * - rhog
     - float64
     - True

   * - Ks
     - float64
     - True

   * - de
     - float64
     - True

   * - avo
     - float64
     - True

   * - apr
     - float64
     - True

   * - a_Xinanjiang_inflection_point_parameter
     - float64
     - True

   * - b_Xinanjiang_shape_parameter
     - float64
     - True

   * - x_Xinanjiang_shape_parameter
     - float64
     - True

   * - uztwm
     - float64
     - True

   * - uzfwm
     - float64
     - True

   * - lztwm
     - float64
     - True

   * - lzfsm
     - float64
     - True

   * - lzfpm
     - float64
     - True

   * - adimp
     - float64
     - True

   * - uzk
     - float64
     - True

   * - lzpk
     - float64
     - True

   * - lzsk
     - float64
     - True

   * - zperc
     - float64
     - True

   * - rexp
     - float64
     - True

   * - pctim
     - float64
     - True

   * - pfree
     - float64
     - True

   * - riva
     - float64
     - True

   * - side
     - float64
     - True




pairs_gower
-----------

Gower distance pairs between donor and receiver catchments.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - divide_id
     - object
     - False

   * - tag
     - object
     - False

   * - donor
     - object
     - False

   * - distSpatial
     - int64
     - False

   * - donors
     - object
     - True

   * - distSpatials
     - object
     - True

   * - distAttr
     - float64
     - True

   * - distAttrs
     - object
     - True




pairs_kmeans
------------

K-means clustering pairs between donor and receiver catchments.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - divide_id
     - object
     - False

   * - tag
     - object
     - False

   * - donor
     - object
     - False

   * - distSpatial
     - int64
     - False

   * - donors
     - object
     - True

   * - distSpatials
     - object
     - True




pairs_msw
---------

Selected donor-receiver pairs for MSW-M regionalization.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - gage_id
     - int64
     - False

   * - divide_id
     - object
     - False




params
------

Parameters used for each formulation in the regionalization.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - gage_id
     - int64
     - False

   * - formulation
     - object
     - False

   * - MFSNO
     - float64
     - False

   * - CWP
     - float64
     - False

   * - VCMX25
     - float64
     - False

   * - MP
     - float64
     - False

   * - RSURF_SNOW
     - float64
     - False

   * - RSURF_EXP
     - float64
     - False

   * - SCAMAX
     - float64
     - False

   * - b
     - float64
     - True

   * - satdk
     - float64
     - True

   * - satpsi
     - float64
     - True

   * - slope
     - float64
     - True

   * - maxsmc
     - float64
     - True

   * - wltsmc
     - float64
     - True

   * - max_gw_storage
     - float64
     - True

   * - Cgw
     - float64
     - True

   * - expon
     - float64
     - True

   * - Kn
     - float64
     - True

   * - Klf
     - float64
     - True

   * - refkdt
     - float64
     - True

   * - mfmax
     - float64
     - True

   * - uadj
     - float64
     - True

   * - si
     - float64
     - True

   * - mfmin
     - float64
     - True

   * - scf
     - float64
     - True

   * - nmf
     - float64
     - True

   * - tipm
     - float64
     - True

   * - pxtemp
     - float64
     - True

   * - plwhc
     - float64
     - True

   * - daygm
     - float64
     - True

   * - smcmin
     - float64
     - True

   * - smcmax
     - float64
     - True

   * - van_genuchten_alpha
     - float64
     - True

   * - van_genuchten_n
     - float64
     - True

   * - hydraulic_conductivity
     - float64
     - True

   * - ponded_depth_max
     - float64
     - True

   * - field_capacity
     - float64
     - True

   * - df
     - float64
     - True

   * - cc
     - float64
     - True

   * - hcan
     - float64
     - True

   * - lai
     - float64
     - True

   * - subalb
     - float64
     - True

   * - ems
     - float64
     - True

   * - cg
     - float64
     - True

   * - zo
     - float64
     - True

   * - rho
     - float64
     - True

   * - rhog
     - float64
     - True

   * - Ks
     - float64
     - True

   * - de
     - float64
     - True

   * - avo
     - float64
     - True

   * - apr
     - float64
     - True

   * - a_Xinanjiang_inflection_point_parameter
     - float64
     - True

   * - b_Xinanjiang_shape_parameter
     - float64
     - True

   * - x_Xinanjiang_shape_parameter
     - float64
     - True

   * - uztwm
     - float64
     - True

   * - uzfwm
     - float64
     - True

   * - lztwm
     - float64
     - True

   * - lzfsm
     - float64
     - True

   * - lzfpm
     - float64
     - True

   * - adimp
     - float64
     - True

   * - uzk
     - float64
     - True

   * - lzpk
     - float64
     - True

   * - lzsk
     - float64
     - True

   * - zperc
     - float64
     - True

   * - rexp
     - float64
     - True

   * - pctim
     - float64
     - True

   * - pfree
     - float64
     - True

   * - riva
     - float64
     - True

   * - side
     - float64
     - True




summary_score
-------------

Summary scores for each catchment after regionalization.

.. list-table::
   :header-rows: 1

   * - Column
     - Type
     - Nullable
   * - gage_id
     - object
     - False

   * - formulation
     - object
     - False

   * - summary_score
     - float64
     - False




.. toctree::
   :maxdepth: 2