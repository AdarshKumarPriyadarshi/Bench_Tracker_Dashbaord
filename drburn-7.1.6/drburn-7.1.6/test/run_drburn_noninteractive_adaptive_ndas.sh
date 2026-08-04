#!/bin/bash

# Runs drburn use-case:
ADAPTIVESRC=https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas/ATG-B/R5/Engineering-Drops/ED26/f41083dae8/bin_aarch64_opt_qnx_idc_entry_base_st35.tar.gz
NDASSRC=https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas-delivery-dev/ATGB_tests/R5-DBGBuilds//driveworks_32672154_v2_usrlocal_20230301.tar.gz

./drburn --update-adaptive --adaptive-source=${ADAPTIVESRC} --update-ndas --ndas-source=${NDASSRC} $@

