#!/bin/bash

# Runs drburn use-case:
NDASSRC=https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas-delivery-dev/ATGB_tests/R5-DBGBuilds//driveworks_32672154_v2_usrlocal_20230301.tar.gz
./drburn --update-ndas --ndas-source=${NDASSRC} $@