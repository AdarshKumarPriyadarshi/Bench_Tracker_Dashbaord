# Dr. Burn

Dr. Burn is a Python tool for easy updating ADAPTIVE, NDAS and DDU on an IDC via SSH. It automates the entire flashing process including

- file retrieval from local path or download from artifactory
- file validation
- backing up and restoring commissioning files
- termination and restart of the ADAPTIVE stack
- software update
- IDC power cycle after successful flashing (in case of DS-PC hosts)

The tool is designed to support different host platforms, primarily DS-PC and MTTF bench.

Per default, Dr. Burn retrieves relevant information from the user in an interactive manner. Additionally, CLI arguments can be used for direct configuration.

## Installation

Dr. Burn can be installed either as [binary](./docs/getting-started.md#binary) (recommended), from [source](./docs/getting-started.md#source) or run as [Docker container](./docs/getting-started.md#docker) (experimental)

### Binary

Find the latest binary on Dr. Burn's [GitLab Releases](https://git.swf.daimler.com/adasdai/drburn/-/releases) Page and
download from artifactory.

1. Make `drburn` executable
   ```ssh
   chmod +x drburn
   ```
2. Run `drburn`
   ```ssh
   ./drburn
   ```

> [Read more about getting started](./docs/getting-started.md#binary)

## CLI

```
usage: drburn    [-h] [--config CONFIG] [--debug] [--download] [--interactive] [--non-interactive] [--verbose] [--logdir OUTPUT_LOGDIR]
                 [--localstorage OUTPUT_LOCALSTORAGE] [--workspace OUTPUT_WORKSPACE] [--artifactory-uri ARTIFACTORY_URI]
                 [--artifactory-user ARTIFACTORY_USER] [--artifactory-password ARTIFACTORY_PASSWORD] [--idc-ip IDC_IP] [--idc-port IDC_PORT]
                 [--update-ddu] [--update-ndas] [--update-rrdata] [--update-adaptive] [--update-bundle] [--clear-adaptive-persistency]
                 [--ndas-source NDAS_SOURCE] [--rrdata-source RRDATA_SOURCE] [--adaptive-source ADAPTIVE_SOURCE]
                 [--adaptive-adaptive ADAPTIVE_ADAPTIVE] [--adaptive-persistency ADAPTIVE_PERSISTENCY] [--adaptive-stub_libs ADAPTIVE_STUB_LIBS]
                 [--ddu-source DDU_SOURCE] [--ddu-script DDU_SCRIPT] [--bundle-source BUNDLE_SOURCE]

optional arguments:
  -h, --help                                    show this help message and exit
  --config CONFIG                               JSON config file
  --debug                                       debug mode without modifying flashed software
  --download                                    download only
  --interactive                                 mode that guides the user step by step
  --non-interactive                             disables interactive mode
  --verbose                                     increase output verbosity

output:
  --logdir OUTPUT_LOGDIR                        path for log files
  --localstorage OUTPUT_LOCALSTORAGE            path for downloaded files
  --workspace OUTPUT_WORKSPACE                  path for temporary files

artifactory:
  --artifactory-uri ARTIFACTORY_URI             artifactory uri
  --artifactory-user ARTIFACTORY_USER           artifactory user
  --artifactory-password ARTIFACTORY_PASSWORD   artifactory password

idc:
  --idc-ip IDC_IP                               IP adress of IDC
  --idc-port IDC_PORT                           Port number of IDC

update:
  --update-ddu                                  update idc via ddu flashing
  --update-ndas                                 update ndas
  --update-rrdata                               update ndas
  --update-adaptive                             update adaptive
  --update-bundle                               update DDU bundle

clear:
  --clear-adaptive-persistency                  clear '/var/lib/adaptive'

ndas:
  --ndas-source NDAS_SOURCE                     local path or url of NDAS tar file

rrdata:
  --rrdata-source RRDATA_SOURCE                 local path or url of NDAS RR DATA tar file

adaptive:
  --adaptive-source ADAPTIVE_SOURCE             local path or url of ADAPTIVE tar file or directory
  --adaptive-adaptive ADAPTIVE_ADAPTIVE         local path or url of ADAPTIVE adaptive partition tar file
  --adaptive-persistency ADAPTIVE_PERSISTENCY   local path or url of ADAPTIVE persistency partition tar file
  --adaptive-stub_libs ADAPTIVE_STUB_LIBS       local path or url of ADAPTIVE stub_libs partition tar file

ddu:
  --ddu-source DDU_SOURCE                       local path or url of DDU tar file
  --ddu-script DDU_SCRIPT                       local path or url flash_ddu.sh

bundle:
  --bundle-source BUNDLE_SOURCE                 local path or url to DDU bundle
```

## Release Notes

### Version 1.1.0

- New name "Dr. Burn"
- NDAS RR Data update
- DDU flashing from MTTF bench (only in interactive mode)
- Path completion for file input
- Backup of commissioning files
- Download only option

### Version 2.0.0

- Code refactoring
- JSON configuration
- Improved download
- Improved logging and reporting
- Dummy SSH module for testing
- Deactivated NDAS RR Data update
