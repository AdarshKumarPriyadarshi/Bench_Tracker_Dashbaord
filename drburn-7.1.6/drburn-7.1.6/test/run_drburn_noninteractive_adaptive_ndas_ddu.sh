#!/bin/bash

# Runs drburn use-case:
ADAPTIVESRC=https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas/ATG-B/R5/Engineering-Drops/ED26/f41083dae8/bin_aarch64_opt_qnx_idc_entry_base_st35.tar.gz
NDASSRC=https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas-delivery-dev/ATGB_tests/R5-DBGBuilds//driveworks_32672154_v2_usrlocal_20230301.tar.gz
DDUSRC=https://artifact.swf.i.mercedes-benz.com/artifactory/adasdai-delivery-release/R5/qnx_idc/Engineering_drops/2023-03-02_5.1.2_ED_I_fbf52fba/my-ddu-ota-pkg_vertical_qnx_z8084-c0v1-d_entry_2023-03-02_18-04-39.tgz



./drburn --update-adaptive --adaptive-source=${ADAPTIVESRC} --update-ndas --ndas-source=${NDASSRC} --update-ddu --ddu-source=${DDUSRC} $@

