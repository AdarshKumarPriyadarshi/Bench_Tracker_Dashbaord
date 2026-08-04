#!/bin/bash

#############################################################################################################################################################
#  FILE DESCRIPTION
#  -----------------------------------------------------------------------------------------------------------------
#
#           \file     flash_ddu.sh
#           \brief    script to flash Direct Drive Update package on IDC6 Orin hardware
#           \author   abenham
#
#############################################################################################################################################################

#############################################################################################################################################################
# Input Parameters/Configuration
#############################################################################################################################################################
FLASH_DDU_PATH=$(dirname "$(realpath -s "${BASH_SOURCE[0]}")")

HW_TYPE="z8084-b02"
NVIDIA_USB_ID="0955"
TIMEOUT_MAX="10"
DEFINE_AURIX_PORT="false"
CLEAN_PARTITIONS="false"
FORCE_REMOVE="false"
WRITE_CUSTOMER_DATA="false"
SKIP_DOCKER_RUN="false"
PARTITION_TO_UPDATE="default"
SIGNED_HEADERS="false"
DEBUG_LOGGING="false"
STATE_ON="on"
STATE_OFF="off"
USE_DOCKER="true"
FORCE_DOCKER="true"

# Colors
NO_COLOR='\033[0m'
RED_COLOR='\033[31m'
GREEN_COLOR='\033[32m'
YELLOW_COLOR='\033[33m'

#############################################################################################################################################################
# Functions
#############################################################################################################################################################
# Usage help
function usage {
  echo "Usage:"
  echo "        $0 [OPTIONS]..."
  echo
  echo "Flash DDU package on IDC6 Orin hardware"
  echo
  echo "Options:"
  echo "    -a, --aurix-port <argument>           Specify aurix port to use. eg: ttyUSB0"
  echo "    -d, --bsp-dir <argument>              Specify the directory path where DDU package is located, DDU package could be a tarball file or a directory"
  echo "    -t, --tar-path <argument>             Specify the absolute path of DDU tarball file"
  echo "    -u, --update-partition <argument>     Pass the name of partition to update. eg: adaptive, per, ndas, factory, fsi ..."
  echo "    -c, --clean-partitions                Erase all of QSPI and EMMC partitions"
  echo "    -f, --force-remove                    Force the removal of existing flashing container"
  echo "    -w, --write-data                      Write customer data json file, no argument required"
  echo "    -nd, --no-docker                      Run the flash environment without the docker container/environment"
  echo "    -fd, --docker-in-docker               Force to run the flash environment with the docker container/environment, useful for Docker-in-Docker setup"
  echo "    -sh, --signed-headers                 To flash encrypted bootchains with signed headers"
  echo "    -D, --debug                           Enable debug logging"
  echo "    -h, --help                            Show this help text, no argument required"
  echo ""
  echo "Notes:"
  echo
  echo "* For ease of use, place this script in the same directory as the DDU package. In this case you don't need to pass -d or --bsp-dir."
  echo "* If -a or --aurix-port is specified, then the flash script sets recovery mode automatically on condition that aurix port is accessible."
  echo "* Relative path can be used if this script and the pathname are located in the same parent directory."
  echo "* To write customer data, flash_ddu.sh and customer_data.json must be present in the same directory and -u or --update-partition option should not be used."
  echo ""
  echo "Please refer to README.md to get more information."
  exit 1
}

# Print info message
function log_info_msg {
  echo -e "${GREEN_COLOR}INFO:${NO_COLOR} $1"
}

# Print warning message
function log_warn_msg {
  echo -e "${YELLOW_COLOR}WARNING: $1${NO_COLOR}"
}

# Print error message
function log_error_msg {
  echo -e "${RED_COLOR}ERROR: ${1}${NO_COLOR}"
}

# Check if the given Aurix port is valid
function check_aurix_port {
  # Check if aurix port is valid
  if [[ -c "/dev/${AURIX_PORT}" ]]; then
    log_info_msg "Aurix Port: ${AURIX_PORT}"
  else
    log_info_msg "/dev/${AURIX_PORT} does not exist"
    exit 1
  fi
}

# Switch on/off recovery mode
function switch_recovery_mode {
  local state=$1
  local dev_ttyUSB=$2
  # Set Serial port
  if [[ "${state}" == "${STATE_ON}" ]]; then
    # Apply UART settings
    stty -F ${dev_ttyUSB} speed 115200 -ixon -ixoff -hupcl -crtscts -echo icanon &>/dev/null
  fi
  # Enable/Disable devmode on Aurix (Activate devmode on Aurix to prevent IPC errors while low level flashing)
  echo "devmode${state}" >${dev_ttyUSB}
  sleep 1
  # Enable/Disable recovery mode with tegrarecovery and tegrareset commands
  echo "tegrarecovery x1 ${state}" >${dev_ttyUSB}
  sleep 1
  echo "tegrareset x1" >${dev_ttyUSB}
  sleep 1
}

# Automate recovery mode
function automate_recovery_mode {
  local state=$1
  log_info_msg "Trying to switch ${state} recovery mode"
  # Default use case: The flash tool assumes that Aurix port is one of the ttyUSB devices present in host machine
  # So, it loops through all ttyUSB devices and sends recovery mode
  if [[ -z "${AURIX_PORT}" ]]; then
    for ttyUSB in ${LIST_TTYUSB}; do
      switch_recovery_mode ${state} ${ttyUSB}
    done
  else
    # Use the given Aurix port to set recovery mode
    switch_recovery_mode ${state} "/dev/${AURIX_PORT}"
  fi
}

# Send tegrareset x1
function tegra_reset {
  log_info_msg "Trying to reset Orin"
  # Default use case: The flash tool assumes that Aurix port is one of the ttyUSB devices present in host machine
  # So, it loops through all ttyUSB devices and sends "tegrareset x1"
  if [[ -z "${AURIX_PORT}" ]]; then
    for ttyUSB in ${LIST_TTYUSB}; do
      echo "tegrareset x1" >${ttyUSB}
    done
  else
    # Use the given Aurix port to set recovery mode
    echo "tegrareset x1" >"/dev/${AURIX_PORT}"
  fi
}

# Check if Nvidia USB device is ready
function check_usb_device {
  local duration=0
  local cmd_out=1
  log_info_msg "Checking for USB device"
  while [[ $duration -le $TIMEOUT_MAX && $cmd_out != 0 ]]; do
    sleep 1
    lsusb -d "${NVIDIA_USB_ID}": >/dev/null
    cmd_out=$?
    duration=$(($duration + 1))
  done
  if [[ $duration -gt $TIMEOUT_MAX ]]; then
    log_error_msg "No recovery-target found. Missing USB device for low level flashing"
    log_warn_msg "Make sure the target is connected to the host and Aurix firmware is up and running"
    if [[ ! -z "${AURIX_PORT}" ]]; then
      log_warn_msg "Make sure Aurix port is correct"
    fi
    exit 1
  else
    log_info_msg "USB device is ready for low level flashing"
  fi
}

# *** Function for the No-Docker-Container approach ***
# Check the Python version in use.
function version_check {
  local version=$(python -V 2>&1 | grep -Po "(?<=Python )(.+)")

  if [[ -z "$version" ]]; then
    echo "The command 'python' does not link to a Python executable."
    echo "Please install a Python version between 3.7 and 3.9 and link it to the 'python' command:"
    echo "$ sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.x 10"
    echo "Stop the Orin flashing..."
    exit 1
  else
    version_comp "${version}" 3.10 "<"
    if [[ $? == 2 ]]; then
      echo "Detected sufficient Python version ${version}"
    else
      echo "Detected insufficient Python verion ${version}. It should be below version 3.10"
      echo "Stop the Orin flashing..."
      exit 1
    fi
  fi
}

# Compare the version numbers seperated by dots.
function version_comp {
  if [[ $1 == $2 ]]; then
    return 0
  fi
  local IFS=.
  local i ver1=($1) ver2=($2)
  # fill empty fields in ver1 with zeros
  for ((i = ${#ver1[@]}; i < ${#ver2[@]}; i++)); do
    ver1[i]=0
  done
  for ((i = 0; i < ${#ver1[@]}; i++)); do
    if [[ -z "${ver2[i]}" ]]; then
      # fill empty fields in ver2 with zeros
      ver2[i]=0
    fi
    if ((10#${ver1[i]} > 10#${ver2[i]})); then
      return 1
    fi
    if ((10#${ver1[i]} < 10#${ver2[i]})); then
      return 2
    fi
  done
  return 0
}

# Check, if the script runs in a docker container already.
function docker_env_detect {

  DOCKERFILE=/.dockerenv

  if [[ -f "$DOCKERFILE" ]]; then
    echo "Discovered docker environment. Run script without starting the container."
    return 0
  else
    return 1
  fi
}

#############################################################################################################################################################
# Main Procedure
#############################################################################################################################################################
# Read command line arguments
while [[ $# != 0 ]]; do
  case "$1" in
    "-a" | "--aurix-port")
      if [[ -z "$2" ]]; then
        log_error_msg "Aurix port is not set"
        usage
      fi
      DEFINE_AURIX_PORT="true"
      AURIX_PORT="$2"
      check_aurix_port
      shift
      ;;
    "-c" | "--clean-partitions")
      CLEAN_PARTITIONS="true"
      ;;
    "-d" | "--bsp-dir")
      if [[ -z "$2" ]]; then
        log_error_msg "DDU directory is not set"
        usage
      fi
      DDU_PKG_DIR="$2"
      shift
      ;;
    "-f" | "--force-remove")
      FORCE_REMOVE="true"
      ;;
    "-h" | "--help")
      usage
      ;;
    "-t" | "--tar-path")
      if [[ -z "$2" ]]; then
        log_error_msg "Path of tarball file is not set"
        usage
      fi
      DDU_TARBALL_PATH="$2"
      shift
      ;;
    "-u" | "--update-partition")
      if [[ -z "$2" ]]; then
        log_error_msg "Partition to flash is not set"
        usage
      fi
      PARTITION_TO_UPDATE="$2"
      shift
      ;;
    "-w" | "--write-data")
      WRITE_CUSTOMER_DATA="true"
      ;;
    "-nd" | "--no-docker")
      USE_DOCKER="false"
      version_check
      ;;
    "-fd" | "--docker-in-docker")
      FORCE_DOCKER="true"
      version_check
      ;;
    "-sh" | "--signed-headers")
      SIGNED_HEADERS="true"
      ;;
    "-D" | "--debug")
      DEBUG_LOGGING="true"
      ;;
    *)
      if [[ -z "$1" ]]; then
        break
      fi
      log_error_msg "Wrong command line arguments"
      usage
      ;;
  esac
  shift
done

# For an easier usage of this script inside an already running container,
# a short test runs to detect a container environment.
if [[ "${FORCE_DOCKER}" == "false" ]]; then
  docker_env_detect
  if [[ $? == 0 ]]; then
    USE_DOCKER="false"
    version_check
  fi
fi

if [[ "${PARTITION_TO_UPDATE}" != "default" && "${WRITE_CUSTOMER_DATA}" == "true" ]]; then
  log_error_msg "Writing customer data does not work if updating one partition is configured"
  usage
fi

echo "================================================================================================================"
echo "                                     Flash Direct Drive Update Package                                          "
echo "================================================================================================================"

if [[ -z "${FLASHING_CONTAINER}" && "${USE_DOCKER}" == "true" ]]; then
  FLASHING_CONTAINER="artifacts.swf.i.mercedes-benz.com/adas-docker/ddu_workspace/flashing_container:v6.0.8.0"
  log_info_msg "Flashing Container: ${FLASHING_CONTAINER}"

  if [[ "${FORCE_REMOVE}" == "true" ]]; then
    log_info_msg "Force stop and remove existing flashing container"
    bash -c "docker rm --force flashing-container"
  fi
fi

# By default, flash script and DDU package are expected to be in the same location
if [[ -z "${DDU_TARBALL_PATH}" ]]; then
  if [[ -z "${DDU_PKG_DIR}" ]]; then
    DDU_PKG_DIR=$(dirname "$(realpath -s "$BASH_SOURCE")")
  else
    DDU_PKG_DIR=$(realpath ${DDU_PKG_DIR})
  fi
  DDU_PKG_PATH=$(realpath ${DDU_PKG_DIR}/*.tgz)
  DDU_PKG_CONTAINER_PATH="/img/*.tgz"
else
  DDU_PKG_PATH=$DDU_TARBALL_PATH
  DDU_PKG_DIR=$(dirname "$DDU_TARBALL_PATH")
  DDU_TARBALL_NAME=$(basename "${DDU_TARBALL_PATH}")
  DDU_PKG_CONTAINER_PATH="/img/${DDU_TARBALL_NAME}"
fi

# Check if DDU package is a tarball or a directory
if [[ -f "${DDU_PKG_PATH}" ]]; then
  SKIP_TAR_DDU="false"
  log_info_msg "DDU Package is a tarball file: ${DDU_PKG_PATH}"
else
  if [[ ! -d "${DDU_PKG_DIR}/ta" || ! -d "${DDU_PKG_DIR}/tools" ]]; then
    log_error_msg "DDU package does not exist in ${DDU_PKG_DIR}"
    exit 1
  fi
  SKIP_TAR_DDU="true"
  log_info_msg "DDU package is a directory: ${DDU_PKG_DIR}"
fi

# Build arguments of flash_bsp_images.py
FLASH_BSP_ARG="-b ${HW_TYPE}"

# Enable debug logs
if [[ "${DEBUG_LOGGING}" == "true" ]]; then
  FLASH_BSP_ARG="${FLASH_BSP_ARG} -D"
fi

# Clean all partitions
if [[ "${CLEAN_PARTITIONS}" == "true" ]]; then
  log_info_msg "Erasing all of QSPI and EMMC partitions"
  FLASH_BSP_ARG="${FLASH_BSP_ARG} --clean"
fi

# Update one partition
if [[ "${PARTITION_TO_UPDATE}" != "default" ]]; then
  log_info_msg "Partition to flash: ${PARTITION_TO_UPDATE}"
  case "${PARTITION_TO_UPDATE}" in
    "adaptive") PARTITION_TO_UPDATE="A_gos0-p-sw" ;;
    "ndas") PARTITION_TO_UPDATE="A_gos0-av-rootfs" ;;
    "fsi") PARTITION_TO_UPDATE="A_fsi-fw" ;;
    "rootfs") PARTITION_TO_UPDATE="A_usr-fs" ;;
    "factory") PARTITION_TO_UPDATE="A_gos0-av-factory" ;;
    "factory_safety") PARTITION_TO_UPDATE="A_gos0-ifs2_7" ;;
    "display") PARTITION_TO_UPDATE="A_plat-misc-cfg" ;;
    *)
      log_error_msg "${PARTITION_TO_UPDATE} is not in expected partitions to be flashed"
      exit 1
      ;;
  esac
  FLASH_BSP_ARG="${FLASH_BSP_ARG} -u ${PARTITION_TO_UPDATE}"
fi

if [[ "${USE_DOCKER}" == "true" ]]; then
  WORKSPACE_DIR="/workspace"
else
  WORKSPACE_DIR="${FLASH_DDU_PATH}"
fi

# Write customer data
if [[ "${WRITE_CUSTOMER_DATA}" == "true" ]]; then
  if [[ -f "${FLASH_DDU_PATH}/customer_data.json" ]]; then
    log_info_msg "Writing customer data"
    FLASH_BSP_ARG="${FLASH_BSP_ARG} --customer-data ${WORKSPACE_DIR}/customer_data.json"
  else
    log_error_msg "Missing customer_data.json in ${FLASH_DDU_PATH}"
    exit 1
  fi
fi

# Flash signed headers
if [[ "${SIGNED_HEADERS}" == "true" ]]; then
  if [[ -d "${FLASH_DDU_PATH}/signed_headers" ]]; then
    log_info_msg "Flashing with signed headers"
    FLASH_BSP_ARG="${FLASH_BSP_ARG} --headers ${WORKSPACE_DIR}/signed_headers"
  else
    log_error_msg "Missing signed_headers folder in ${FLASH_DDU_PATH}"
    exit 1
  fi
fi

# Get list of serial USB devices
LIST_TTYUSB=$(ls /dev/ttyUSB*)
# Set Recovery mode
automate_recovery_mode ${STATE_ON}
# Detect USB-C device
check_usb_device

log_info_msg "Flashing IDC6 Orin hardware started"

# Start the flashing
if [[ "${USE_DOCKER}" == "true" ]]; then
  # Prepare docker run command
  # Prepare bash command to be executed in docker container
  if [[ "${SKIP_TAR_DDU}" == "false" ]]; then
    log_info_msg "Unpacking tarball file in flashing container"
    BASH_CMD="bash -c \"tar xvf ${DDU_PKG_CONTAINER_PATH} -C /tmp && \
                        cp -r /tmp/tools/tools /tmp/ta/ && \
                        python3 /tmp/ta/tools/flashtools/bootburn/flash_bsp_images.py -P /tmp/ta ${FLASH_BSP_ARG}\""

  else
    BASH_CMD="bash -c \"cp -r /img/tools/tools /img/ta/ && \
                        python3 /img/ta/tools/flashtools/bootburn/flash_bsp_images.py -P /img/ta ${FLASH_BSP_ARG}\""
  fi

  # Execute the flash command in docker
  FLASH_CMD="docker run --rm \
                        --name flashing-container \
                        --privileged \
                        --net host \
                        -v /dev/bus/usb:/dev/bus/usb \
                        -v ${FLASH_DDU_PATH}:/workspace \
                        -v ${DDU_PKG_DIR}:/img \
                        -v /var/log:/var/log \
                        -v /var/lock:/var/lock \
                        ${FLASHING_CONTAINER} \
                        ${BASH_CMD}"
else
  # Prepare bash command to be executed in a normal OS environment
  if [[ "${SKIP_TAR_DDU}" == "false" ]]; then
    log_info_msg "Unpacking tarball file for flashing in a normal environment"
    FLASH_CMD="bash -c \"sudo tar xvf ${DDU_PKG_PATH} -C /tmp && \
                         sudo cp -r /tmp/tools/tools /tmp/ta/ && \
                         sudo python3 /tmp/ta/tools/flashtools/bootburn/flash_bsp_images.py -P /tmp/ta ${FLASH_BSP_ARG}\""
  else
    FLASH_CMD="bash -c \"cp -r  ${DDU_PKG_DIR}/tools/tools  ${DDU_PKG_DIR}/ta/ && \
                         sudo python3  ${DDU_PKG_DIR}/ta/tools/flashtools/bootburn/flash_bsp_images.py -P  ${DDU_PKG_DIR}/ta ${FLASH_BSP_ARG}\""
  fi
fi

# Run flashing process
if ! /bin/bash -c "${FLASH_CMD}"; then
  log_error_msg "Flashing IDC6 Orin hardware failed"
  # Disable recovery mode
  automate_recovery_mode ${STATE_OFF}
  exit 1
fi

# Disable recovery mode
automate_recovery_mode ${STATE_OFF}

log_info_msg "Flashing IDC6 Orin hardware completed successfully"
