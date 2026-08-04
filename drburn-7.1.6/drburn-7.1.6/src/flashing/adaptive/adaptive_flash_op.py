from __future__ import annotations

import asyncio
import os
import subprocess
import shutil
import tarfile
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Optional, Dict, List

from config.flash_config import Source, ModuleAdaptive
from flashing.adaptive.remote_adaptive_controller import RemoteAdaptiveController
from flashing.flash_graph import FlashGraph
from log.format import BGColor, FGColor, Style
from log.utils import dump_bold, dump_colored_figlet_txt, dump_failure, dump_success, dump_time, dump_dict_as_table
from ssh.ssh_connection_handler import SSHConnectionHandler
from ssh.utils import erase_directory
from upload import UploadOpFactory, UploadOp
from utils.file_system import remove_suffixes
from utils.tar import get_tar_leading_dirs, tar_contains
from utils.runtime import RuntimeTimer


class AdaptiveFlashOp:
    """Class that encapsulates the steps necessary to
       'flash' the adaptive stack twoards an IDC.

       'Flash' in this context means a copy of binaries
       to a well-defined place on the IDC.

    To sum up the steps:
    1. Get the adaptive.tar.
    2. Validate the tar file (expected content is there).
    3. Untar the tar file.
    4. Establish ssh - connection.
      4.1 Stop adaptive runnables/executables on IDC (device).
      4.2 Remove the files/directories on the IDC (device).
      4.3 Upload the data to the Device.
      4.4 Start the adaptive runnables/executables.
      4.5 Close the ssh connection.
    5. Clean up and return.

    """

    DELETE_PERSISTENCY = "delete_persistency"

    magicString = "AdaptiveFlashOp"

    def __init__(self, flashGraph: FlashGraph, name: str, sources: Dict[str, Source], workspaceDir: str, uploader: UploadOp, clear_persistency: bool):
        """Constructor fills member attributes and expects and existing testbench object.
        """
        # Get the testbench environment.
        self._name = name
        self.sources = sources
        self.clear_persistency = clear_persistency
        self.graph = flashGraph
        self.magicString = self.magicString

        self.workspaceDir = workspaceDir
        self.uploader = uploader
        # Path for temporary untared data.
        self.untarDir = Path(workspaceDir) / "adaptive_untared"

        # SSH config
        self.config = self.graph.config
        # Use the logger from the graph (owner).
        self.logger = self.graph.logger

        # Create AdaptiveController
        self.idc_adaptive = RemoteAdaptiveController(logger=self.logger)

        # Report on last flash attempt.
        self._report = []

    @classmethod
    def create(cls, flash_graph: FlashGraph) -> Optional[AdaptiveFlashOp]:
        """Creator method that retrieves all necessary information
           from an FlashGraph and forwards the
           creation to the default/standard constructor.
        Args:
            flash_graph (_type_): _description_
        """
        # TODO: (vibenzi) create class method that can be called by the FlashOpFactory
        module = flash_graph.config.modules["adaptive"]

        if not isinstance(module, ModuleAdaptive):
            return None

        if not module.update:
            return None

        logger = flash_graph.logger

        sources = module.sources
        sources = {source_id: source for source_id, source in sources.items() if source.url}
        if not len(sources.items()):
            logger.error("You have to provide at least one source tarfile!")
            return None

        tar_filename: str = ""
        for source_id, source in sources.items():
            tar_filename = source.url
            error_message = f"Can't create Adaptive flash op! Please check tarfile for {source_id} at '{tar_filename}'."
            if tar_filename is None:
                logger.error(f"{error_message} No file given!")
                return None
            if not os.path.isfile(tar_filename):
                logger.error(f"{error_message} Is not a file!")
                return None
            if not tarfile.is_tarfile(tar_filename):
                logger.error(f"{error_message} Is not a valid tarfile!")
                return None

            logger.debug(f"AdaptiveFlashOp uses tarfile for {source_id} at {tar_filename}")

        # Remove suffixes for name creation.
        name = remove_suffixes(str("__".join(["adaptive", *str(tar_filename).split("__")[1:]])))

        graphWorkspace = flash_graph.workingDir
        workspaceDir = graphWorkspace / "adaptive/"
        os.makedirs(workspaceDir)

        uploader = UploadOpFactory(flash_graph.config, flash_graph.logger).create()

        # Create AdaptiveFlashOp from proper data.
        return cls(flash_graph, name, sources, workspaceDir, uploader, module.clear_persistency)

    @property
    def name(self):
        return self._name

    @property
    def report(self):
        return "\n".join(self._report)

    @property
    def ADAPTIVE_SOURCE(self):
        return "adaptive_partition_tar.tar"

    @property
    def ADAPTIVE_PERSISTENCY_SOURCE(self):
        return "persistency_partition_tar.tar"

    @property
    def STUB_LIBS_SOURCE(self):
        return "stub_libs_partition_tar.tar"

    @property
    def ADAPTIVE_TARGET(self):
        return "/usr/adaptive"

    @property
    def ADAPTIVE_PERSISTENCY_TARGET(self):
        """ Do not delete /var/lib/adaptive """
        return "/usr/adaptive/var"

    @property
    def ADAPTIVE_PERSISTENCY_TARGET_LEGACY(self):
        """ R6 persistency target """
        return "/var/lib/adaptive"

    @property
    def STUB_LIBS_TARGET(self):
        return "/usr/local/driveworks/libs"

    def is_valid_tar_file(self, path: Path) -> bool:
        # TODO: (vibenzi) Consider using exception for error handling
        if tarfile.is_tarfile(path):
            with tarfile.open(path) as tar_file:
                contains_ADAPTIVE_SOURCE = tar_contains(tar_file, self.ADAPTIVE_SOURCE)
                contains_ADAPTIVE_PERSISTENCY_SOURCE = tar_contains(tar_file, self.ADAPTIVE_PERSISTENCY_SOURCE)
                valid = contains_ADAPTIVE_SOURCE and contains_ADAPTIVE_PERSISTENCY_SOURCE
                if not valid:
                    self.logger.info(f"{path} is not a valid ADAPTIVE tar file.")
                return valid
        else:
            self.logger.info(f"{path} is not a valid adaptive tar file.")
        return False

    def flash(self) -> bool:
        """
        Flashing ADAPTIVE:

        base_..idc...tar.gz file contains ->  adaptive.tar
                                          ->  adaptive_persistency.tar

        These are copied to the device using SSH/SCP.

        Sequential step-by-step flow of flashing adaptive onto IDC device.
        NOTE: The flashing strategy is organized such that fast checks
              are queried first to make problems obvious as early as possible.

        I.   Untar tar file to a temporary working directory and configure flash targets.
             and check for adaptive.tar and adaptive_persistency.tar in untar result.
        II.  Check ssh connection is available.
             a) We make a ping (coarse test; convenient feedback to user).
             b) We try establishing an ssh connection.
        IV.  Prepare IDC:
             a) Stop adaptive on device
             b) Mount adaptive partitions
        V.   Flash/Put new adaptive* to device/IDC. [adaptive.tar, adaptive_persistency.tar]
             a) Remove existing adaptive on device.
             b) Copy adaptive*.tar to device.
             c) Extract file on device.
        VI.  Restart adaptive on device
        """
        self.logger.info(dump_colored_figlet_txt(type(self).__name__, fgcolor=FGColor.WHITE, bgcolor=BGColor.BLUE))
        self.logger.info(f"{dump_bold(type(self).__name__)} sources: \n"
                         f"{dump_dict_as_table({source_id: source.url for source_id, source in self.sources.items()})}")

        if self._report:
            self.logger.warning("Overriding flash report (from a previous flash run?)")

        files: List[Path] = []
        targets: List[str] = []

        # I.   Configure flash targets
        is_r6_source = self.sources.get("source")
        is_r10_source = 0 # TODO: should adapt it properly here
        if is_r6_source:
            # Untar legacy packed tar file <= R6
            adaptive_source = self.untar_source(is_r6_source.url)
            files = [adaptive_source]
            targets = [self.ADAPTIVE_TARGET]

        elif is_r10_source:
            # Configure flash targets dynamically >= R7
            partition_to_target = {
                "adaptive": self.ADAPTIVE_TARGET,
                "persistency": self.ADAPTIVE_PERSISTENCY_TARGET,
                "stub_libs": self.STUB_LIBS_TARGET,
                self.DELETE_PERSISTENCY: self.ADAPTIVE_PERSISTENCY_TARGET_LEGACY
            }
            sources = self.sources.copy()
            if self.clear_persistency:
                sources[self.DELETE_PERSISTENCY] = Source(url=Path(""))
            files, targets = zip(
                *[(source.url, partition_to_target.get(source_id)) for source_id, source in sources.items()])

        else:
            # Configure flash targets dynamically >= R7
            partition_to_target = {
                "adaptive": self.ADAPTIVE_TARGET,
                "stub_libs": self.STUB_LIBS_TARGET
            }
            sources = self.sources.copy()
            files, targets = zip(
                *[(source.url, partition_to_target.get(source_id)) for source_id, source in sources.items()])

        # II.  Check ssh connection is available.
        idc_ip = self.config.idc.ip
        idc_port = self.config.idc.port
        #      We try establishing an ssh connection.
        self.logger.info(f"Testing ethernet connection")
        with SSHConnectionHandler(self.config, logger=self.logger) as ssh:
            if ssh is None:
                self.logger.critical(f"{dump_failure()} establishing SSH Connection! ")
                self.logger.critical("Aborting Adaptive flashing!")
                self._report.append(f"Could not create SSH connection! (Ip: {idc_ip}, Port: {idc_port}")
                self._report.append(f"Flashing not possible!")
                return False

        # ====================================
        # Flashing IDC through SSH
        # ====================================
        with SSHConnectionHandler(self.config, logger=self.logger) as ssh:
            if ssh is None:
                self.logger.error(f"{dump_failure()} establishing SSH Connection! ")
                return False

            # IV. Prepare IDC:
            # a) Sync fs.
            ssh.exec_command("sync")

            # b) Stop adaptive.
            self.logger.info("Stopping adaptive")
            self.idc_adaptive.stop(ssh, self.config.verbose)
            self._report.append(f"Stopped adaptive on device.")

            # c) Mount partitions.
            self.logger.info("Mounting adaptive partitions")
            if is_r10_source:
                self.idc_adaptive.mount_partitions(ssh, [
                    self.ADAPTIVE_TARGET,
                    self.ADAPTIVE_PERSISTENCY_TARGET_LEGACY
                ])
            else:
                self.idc_adaptive.mount_partitions(ssh, [
                    self.ADAPTIVE_TARGET
                ])
            self._report.append(f"Mounted adaptive partitions on device.")

            # d) Clear SelfDiagnosticAgent_Executable.
            if is_r6_source:
                adaptive_self_diagnostic_target = f"{self.ADAPTIVE_PERSISTENCY_TARGET_LEGACY}/SelfDiagnosticAgent_Executable/*"
                self.logger.info(f"Clearing {adaptive_self_diagnostic_target}")
                # rm -rf /var/lib/adaptive/SelfDiagnosticAgent_Executable/*
                _, _, stderr = ssh.exec_command(f"rm -rf {adaptive_self_diagnostic_target}")
                if stderr:
                    self.logger.error(f"Error while clearing {adaptive_self_diagnostic_target}\n{stderr}")
                self._report.append(f"Cleared {adaptive_self_diagnostic_target}")

            # V. Put new adaptive* to device/IDC.
            flash_success = True
            for source, target in zip(files, targets):
                if isinstance(source, str):
                    source = Path(source)
                self.logger.info("-")
                self.logger.info(f"Flashing {source}")

                # Skip persistency_partition_tar files
                if "persistency_partition_tar" in str(source) and not is_r10_source and not is_r6_source:
                    self.logger.info(f"Skipping {source} as it matches persistency_partition_tar pattern.")
                    continue

                # Actual 'flashing'.
                # NOTE: The "retries" are handled in a do-while loop which makes exception handling easier.
                max_nr_of_retries = 1
                attempt = 0
                retry_flash_success = False

                # [DO-WHILE]
                while True:
                    if attempt > max_nr_of_retries:
                        break

                    if attempt > 0:
                        dotprogress_str = "." * attempt
                        self.logger.info(f"Retrying flashing {dotprogress_str}")

                    try:
                        # Whenever we start the 'flash' procedure, we do not care about
                        # previously copied that -> we start from the beginning:

                        device_literal = f"{FGColor.YELLOW}{BGColor.WHITE}IDC{FGColor.RESET}:"
                        erase_literal = f"{Style.ITALIC}Erasing{FGColor.RESET}"
                        self.logger.info(f"{device_literal} {erase_literal} {target} directory.")

                        # V a) Remove existing.
                        erased_directory = erase_directory(ssh=ssh, dir=target, logger=self.logger)
                        ssh.exec_command("sync")

                        if not erased_directory:
                            attempt += 1
                            continue

                        # If R7 and target '/var/lib/adaptive', then only delete
                        if is_r10_source and target == self.ADAPTIVE_PERSISTENCY_TARGET_LEGACY:
                            retry_flash_success = True
                            break

                        # V b) Create persistency dir if not legacy
                        if target == self.ADAPTIVE_PERSISTENCY_TARGET and is_r10_source:
                            self.logger.info(f"Creating directory {self.ADAPTIVE_PERSISTENCY_TARGET}")
                            ssh.exec_command(f"mkdir -p {self.ADAPTIVE_PERSISTENCY_TARGET}")
                            ssh.exec_command("sync")
                            self._report.append(f"Created directory {self.ADAPTIVE_PERSISTENCY_TARGET}")

                        # V c) Copy to device.
                        # Now we copy payload data to device.
                        self.logger.info("Extracting source files to temporary directory")

                        # V d) Extract file (locally).
                        # Create local tmp extract dir
                        with tempfile.TemporaryDirectory(dir=self.workspaceDir) as tmpdir_name:
                            tmpdir = Path(tmpdir_name)

                            # extract source tarball
                            with closing(tarfile.open(source)) as archive:
                                leading_dirs = get_tar_leading_dirs(archive)
                                self.logger.debug(f"leading_dirs: {Path(*leading_dirs)}")

                                members = []
                                for member in archive.getmembers():
                                    # rewrite member if leading_dirs < 0
                                    strip_components = len(leading_dirs)
                                    parts = Path(member.path).parts[strip_components:]
                                    if len(parts):
                                        member.path = Path(*parts)
                                        members.append(member)
                                self.logger.info("Extracting source file")
                                # refactored 'tar -xvf {source} --strip-components={leading_dirs}'
                                archive.extractall(path=tmpdir, members=members)

                            with RuntimeTimer("UploadingTime") as upload_time:
                                self.logger.info("Copying source files to target directory")
                                self.uploader.upload(tmpdir.glob('*'), target)
                            self.logger.info(f"Uploading {source} to IDC took {dump_time(int(upload_time))}.")
                            self._report.append(f"Uploaded {source.name} in {dump_time(int(upload_time))}.")

                        # V e) Workaround for persistency files.
                        if target == self.ADAPTIVE_PERSISTENCY_TARGET and is_r10_source:
                            self.logger.info("Workaround for persistency files")
                            ssh.exec_command(
                                "sed -i '2s/^\\s*$/# workaround for first boot\\n/' /usr/adaptive/startup.sh")
                            self._report.append(f"Added workaround for first boot")

                        # V f) Sync fs
                        self.logger.info("Syncing filesystem")
                        ssh.exec_command("sync")
                        self._report.append(f"Synced filesystem")

                        retry_flash_success = True
                        break

                    except Exception as e:
                        self.logger.error(f"Failed to flash {source} onto {target}.")
                        self.logger.error(str(e))
                        attempt += 1
                        retry_flash_success = False
                        continue

                flash_success &= retry_flash_success
                if retry_flash_success and is_r10_source and target == self.ADAPTIVE_PERSISTENCY_TARGET_LEGACY:
                    self.logger.info(f"{dump_success()} Erasing: {target}")
                    self._report.append(f"Erased {target} on device.")
                    continue

                if retry_flash_success:
                    self.logger.info(f"{dump_success()} Flashing: {source}")
                    self._report.append(f"Flashed {source.name} to device.")

            self.logger.warning(dump_bold("PLEASE REBOOT DEVICE AFTER SUCCESSFUL FLASH!"))
            self._report.append(f"PLEASE REBOOT IDC ({idc_ip}) AFTER SUCCESSFUL FLASH!")

        # Cleanup legacy tar files dir
        if self.untarDir.is_dir():
            self.logger.info(f"Cleaning up temporary directory: {self.untarDir}...")
            # Freeing  1.3 GB of memory
            shutil.rmtree(self.untarDir)
            self.logger.info(f"Cleaning up temporary directory: {self.untarDir} Done.")

        return flash_success

    def untar_source(self, tarFilename: str):
        # Using pathlib.Path for convenience.
        tarFilePath = Path(tarFilename)

        # I.   Check tar file is there.
        if not tarFilePath.is_file():
            self.logger.error("Adaptive tar file not found at: {self.tarFilename}")
            self.logger.error("Aborting Adaptive flashing!")
            self._report.append(f"adaptive - tarfile (at {tarFilename}) not found. Flashing not possible!")
            return False
        else:
            self.logger.info(f"Found adaptive-tarfile: {dump_bold(tarFilename)}")
            self._report.append(f"Found adaptive-tarfile (at {tarFilename}).")

        self.logger.info(f"Untar tarfile: {tarFilePath}")

        # III. Untar tarfile.
        if not self.untarDir.is_dir():
            self.logger.info(f"Creating directory: {self.untarDir}")
            os.makedirs(self.untarDir)

        if not self.untarDir.is_dir():
            self.logger.error("Creating directory for un-tar-ed data failed!")
            return False

        # Untar.
        untar_cmd = ["tar", "xfv", tarFilePath, "-C", str(self.untarDir)]
        self.logger.info(f"Extracting tar-file {tarFilePath}:")

        timeout_secs = 480
        try:
            with RuntimeTimer("AdaptiveUntarDuration") as untar_duration:
                subprocess.run(untar_cmd, timeout=timeout_secs)

        except subprocess.TimeoutExpired as te:
            # Catch timeout.
            self.logger.info("Untar took unexpected long (maybe out of disk space?)")
            return False

        # Make sure tar contains adaptive sources after untaring.
        def find_file(fname) -> Optional[Path]:
            found_lst = list(self.untarDir.glob(f"**/{fname}"))
            if len(found_lst) > 1:
                self.logger.debug(f"Warning: Found more than one of {fname}!")
                return None
            elif len(found_lst) == 0:
                self.logger.debug(f"No {fname} found in untar-directory!")
                return None

            return found_lst[0]

        adaptive_source = find_file(self.ADAPTIVE_SOURCE)

        self.logger.info("Check for valid adaptive tar-file.")
        if adaptive_source is None:
            self.logger.error(f"Could not find {self.ADAPTIVE_SOURCE}. Aborting Adaptive flashing.")
        else:
            self.logger.info(f"Found valid {dump_bold(self.ADAPTIVE_SOURCE)} file.")

        if adaptive_source is None:
            return False

        self.logger.info(
            f"{dump_success()} Extracting {self.ADAPTIVE_SOURCE} and {self.ADAPTIVE_PERSISTENCY_SOURCE} took {dump_time(float(untar_duration))}"
        )

        self._report.append("Adaptive tar-file valid and extracted.")

        return adaptive_source
