#!/bin/bash

# Runs drburn use-case:
DDUSRC=https://artifact.swf.i.mercedes-benz.com/artifactory/adasdai/tmp/R7_Beta_standaloneIdc/my-ddu-ota-pkg_vertical_qnx_z8084-c0v1-d_entry_71ff57b_2023-06-08_14-51-47.tgz

./drburn --update-ddu --ddu-source=${DDUSRC} $@
