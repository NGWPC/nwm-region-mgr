Parameter Regionalization
==========================

.. toctree::
   :maxdepth: 2


Data validation
 - check if both donors and receivers are all present in the attribute dataset
 - check if donors and receivers are all present in the spatial distance dataset
 - quantify percent nan in dataset
Check if this is a snow basin
setup algorithm config and base and main attributes
[run for each algo, then for each formulation]
for receiver in receivers

proximity pairer
   If snowy, only allow snowy donors (and vice versa). Hardcode spatial limit
   clip to ndonor max by spatial distance
   (can return empty DF if none within dist)
   if you passed in a dist_attr, log those dists
   concat all receivers

distance pairer
for attrs in base and main
while receivers
get valid attrs
 - select non donors
 - select receivers that haven't been processed
this whole pairing thing should be vectorized?
pair catchments with same missing attributes

clusterpairer
again, get groups w shared na vals
all the cluster pairers share the same pair function that just hands it off to the parent
line 81 _pair() funcs_cluster...just use the conditional???
I would do this cluster identification using the base algorithm.  If you need to subdivide, do that at the top level

use spatial proximity for final pairs.  Should have a field for whether this is applied.

assume any missing catchments are calibrated
