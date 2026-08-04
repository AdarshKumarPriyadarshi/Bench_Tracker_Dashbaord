from __future__ import annotations

import os
from pathlib import Path
from contextlib import closing
import tarfile
import tempfile
from typing import Optional

from flashing.adaptive.remote_adaptive_controller import RemoteAdaptiveController
from flashing.flash_graph import FlashGraph
from log.format import BGColor, FGColor
from log.utils import dump_colored_figlet_txt, dump_failure, dump_success, dump_time
from ssh.ssh_connection_handler import SSHConnectionHandler
from ssh.utils import remove_directory
from upload import UploadOp, UploadOpFactory
from utils.file_system import remove_suffixes
from utils.runtime import RuntimeTimer
from utils.tar import get_tar_leading_dirs, tar_contains


class NDASFlashOp:
    """Class that encapsulates the steps necessary to
       'flash' the NDAS stack towards an IDC.

       'Flash' in this context means a copy of binaries
       to a well-defined place on the IDC.

    To sum up the steps:
    1. Get the driveworks_xxx.tar.
    2. Validate the tar file (expected content is there).
    3. Untar the tar file.
    4. Establish ssh - connection.
      4.1 Remove the files/directories on the IDC (device).
      4.2 Upload the data to the Device.
      4.3 Close the ssh connection.
    5. Clean up and return.

    """

    magicString = "NDASFlashOp"

    def __init__(self, flashGraph: FlashGraph, name: str, tarFilename: str, workspaceDir: str, uploader: UploadOp):
        """Constructor fills member attributes and expects and existing testbench object.
        """
        # Get the testbench environment.
        self._name = name
        self.tarFilename = tarFilename
        self.graph = flashGraph
        self.config = flashGraph.config
        self.magicString = self.magicString

        self.workspaceDir = workspaceDir
        self.uploader = uploader
        # Use the logger from the graph node.
        self.logger = self.graph.logger

        self.idc_adaptive = RemoteAdaptiveController(logger=self.logger)

        # Report on last flash attempt.
        self._report = [""]

    @classmethod
    def create(cls, flash_graph: FlashGraph) -> Optional[NDASFlashOp]:
        """Creator method that retrieves all necessary information
           from an FlashGraph and forwards the
           creation to the default/standard constructor.
        Args:
            flash_graph (_type_): _description_
        """
        # TODO: (vibenzi) create class method that can be called by the FlashOpFactory
        if not flash_graph.config.modules["ndas"].update:
            return None

        logger = flash_graph.logger

        tarFilename = flash_graph.config.modules["ndas"].sources["source"].url
        if tarFilename is not None and os.path.isfile(tarFilename) and tarfile.is_tarfile(tarFilename):
            logger.debug(f"NDASFlashOp uses tarfile at {tarFilename}")
        else:
            logger.error(f"Can't create NDAS flash op! Please check tarfile at '{tarFilename}'!")
            return None

        graphWorkspace = flash_graph.workingDir
        workspaceDir = graphWorkspace / "ndas"
        os.makedirs(workspaceDir)

        # Strip extension/suffices (e.g. tar.gz)
        name = remove_suffixes(str(tarFilename))

        uploader = UploadOpFactory(flash_graph.config, flash_graph.logger).create()

        # Create AdaptiveFlashOp from proper data.
        return cls(flash_graph, name, tarFilename, workspaceDir, uploader)

    @property
    def name(self):
        return self._name

    @property
    def report(self):
        return "\n".join(self._report)

    @property
    def NDAS_TARGET_DIR(self):
        return "/usr/local"

    @property
    def NDAS_RR_DATA_DIR(self):
        return "/usr/local/driveworks/apps/roadrunner-2.0/config"

    @property
    def NDAS_DRIVEWORKS_SYMLINK(self):
        return "/usr/local/driveworks"

    @property
    def NDAS_DRIVEWORKS_REGEX(self):
        return "driveworks-"

    @property
    def NDAS_VERSION_INFO(self):
        return "version_info.txt"

    def is_valid_ndas_tar_file(self, path: Path) -> bool:
        # TODO: Check directory structure!
        if tarfile.is_tarfile(path):
            with tarfile.open(path) as tar_file:
                contains_NDAS = tar_contains(tar_file, self.NDAS_VERSION_INFO)
                valid = contains_NDAS
                if not valid:
                    self.logger.info(f"{path} is not a valid NDAS tar file.")
                return valid
        else:
            self.logger.info(f"{path} is not a valid adaptive tar file.")
        return False

    def get_installed_ndas_files_on_idc(self, ssh):
        # Get NDAS files on IDC:

        cmd_ls_ndas_dirs = f"ls -d {self.NDAS_TARGET_DIR}/* | grep '{self.NDAS_DRIVEWORKS_REGEX}'"
        __, stdout, _ = ssh.exec_command(cmd_ls_ndas_dirs)

        dir_candidates_list = stdout.split("\n")

        dir_list = []

        for dir_candidate in dir_candidates_list:

            true_str = "TRUE"

            cmd_is_directory = f"if [ -d {dir_candidate} ]; then echo {true_str}; fi"
            _, stdout, _ = ssh.exec_command(cmd_is_directory)
            if true_str in stdout.strip():
                dir_list.append(dir_candidate)
            else:
                pass

        return dir_list

    def get_top_level_tarfile(self, path: Path) -> list:
        """
            Returns top level directories and files without the '.' directory.
        """
        top_dirs = set()
        with tarfile.open(path, mode="r") as archive:
            full_content = archive.getnames()
            offset = 1 if os.path.commonprefix(full_content) == "." else 0
            for i in full_content:
                try:
                    dir = i.split("/")[offset]
                    top_dirs.add(dir)
                except IndexError:
                    continue
        return list(top_dirs)

    def rm_old_data_on_target(self, top_level_dir:list, ssh):
        """
            Removes the old directories and files in the target system
        """
        for i in top_level_dir:
            dir = os.path.join(self.NDAS_TARGET_DIR, i)
            cmd = f"rm -r {dir}"
            _, stdout, _ = ssh.exec_command(cmd)

    def flash(self):
        """ """

        self.logger.info(dump_colored_figlet_txt(type(self).__name__, fgcolor=FGColor.BLACK, bgcolor=BGColor.GREEN))

        # I. Make sure files are there.
        if os.path.isfile(self.tarFilename):
            pass
        else:
            raise FileNotFoundError(f"File not available at given path: {self.tarFilename}")

        tarFilePath = Path(self.tarFilename)

        # II. Check a valid ADAPTIVE-type tar-file was given.
        # NOTE: is_valid ... may also be done in FrontLoading!??
        self.logger.info("Check for valid NDAS tar file:")
        valid = self.is_valid_ndas_tar_file(tarFilePath)

        if not valid:
            self.logger.error("Could not use provided NDAS tar file for flashing! Aborting ADAPTIVE flashing.")
            return False

        files = [tarFilePath]
        targets = [self.NDAS_TARGET_DIR]
        # erase_flags = [False]
        # NOW We are good to start peripherie stuff AND ! note, we should have an ssh connection available!

        # (fgritsc) TODO: Check for ssh connection available, e.g. with a ping.

        with SSHConnectionHandler(self.config, logger=self.logger) as ssh:

            if ssh is None:
                self.logger.error(f"{dump_failure()} establishing SSH Connection! ")
                return False

            self.logger.info("Stopping adaptive")

            self.idc_adaptive.stop(ssh)
            self.logger.info("Stopping adaptive DONE:")

            ndas_on_idc_pre_flashing = self.get_installed_ndas_files_on_idc(ssh)

            for source, target in zip(files, targets):

                self.logger.info("-")
                self.logger.info(f"Flashing {source}")

                # Actual 'flashing'.
                # NOTE: The "retries" are handled in a do-while loop which makes exception handling easier.
                maxNrOfRetries = 1
                flash_success = False
                trial = 0

                while True:

                    if trial > maxNrOfRetries:
                        break

                    if trial > 0:
                        dotprogress_str = "." * trial
                        self.logger.info(f"Retrying flashing {dotprogress_str}")

                    try:
                        # Now we copy payload data to device.
                        self.logger.info("Extracting source files to temporary directory")

                        ndas_top_level_tar = self.get_top_level_tarfile(source)
                        self.rm_old_data_on_target(ndas_top_level_tar, ssh)

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

                            symlinks = {}
                            for root, dirs, files in os.walk(tmpdir, followlinks=False):
                                for name in files:
                                    file = Path(root) / name
                                    if file.is_symlink():
                                        symlinks[name] = os.readlink(file)
                                        file.unlink()

                            with RuntimeTimer("UploadingTime") as upload_time:
                                self.logger.info("Copying source files to target directory")
                                self.uploader.upload(tmpdir.glob('*'), target)
                            self.logger.info(f"Uploading {source} to IDC took {dump_time(int(upload_time))}.")

                            for name, symlink in symlinks.items():
                                ssh.exec_command(f"ln -s {symlink} {target + '/' + name}")

                        ssh.exec_command("sync")

                        flash_success = True
                        break

                    except Exception as e:
                        self.logger.error(f"Failed to flash {source} onto {target}.")
                        self.logger.error(str(e))
                        trial += 1
                        flash_success = False
                        continue

                if flash_success:
                    self.logger.info(f"{dump_success()} Flashing: {source}")

            #
            ndas_on_idc_post_flashing = self.get_installed_ndas_files_on_idc(ssh)

            # Cleanup ndas on IDC:
            # There are more than before:
            #
            #  Example 1:
            #  pre/before     post/after
            #    *-5.09-*
            #    *-5.10-*     *-5.10-*       --> [DELETE]
            #
            #  Example 2:
            #  pre/before     post/after
            #    *-5.10-*     *-5.10-*       --> [DELETE]
            #                 *-5.11-*
            new_ndas_version = None
            if len(ndas_on_idc_post_flashing) > len(ndas_on_idc_pre_flashing):

                ndas_versions_to_delete = []
                for ndas_version in ndas_on_idc_post_flashing:
                    if ndas_version in ndas_on_idc_pre_flashing:
                        ndas_versions_to_delete.append(ndas_version)
                    else:
                        new_ndas_version = ndas_version
                self.logger.info("\nCleaning up previous ndas versions")
                for path in ndas_versions_to_delete:
                    remove_directory(ssh, path)

            if new_ndas_version:
                ssh.logger.info("Updating driveworks symlink")
                true_str = "TRUE"
                cmd_exists = f"if [ -e {self.NDAS_DRIVEWORKS_SYMLINK} ]; then echo {true_str}; fi"
                _, stdout, _ = ssh.exec_command(cmd_exists)
                if true_str in stdout.strip():
                    ssh.logger.debug("Unlinking existing driveworks symlink")
                    ssh.exec_command(f"""unlink {self.NDAS_DRIVEWORKS_SYMLINK}""")
                ssh.logger.debug("Creating driveworks symlink")
                ssh.exec_command(
                    f"""cd {self.NDAS_TARGET_DIR} && ln -s {new_ndas_version} {self.NDAS_DRIVEWORKS_SYMLINK}"""
                )

            self.logger.warning("PLEASE REBOOT DEVICE AFTER SUCCESSFUL FLASH!")
            self._report.append(f"PLEASE REBOOT DEVICE AFTER SUCCESSFUL FLASH!")

        return flash_success
