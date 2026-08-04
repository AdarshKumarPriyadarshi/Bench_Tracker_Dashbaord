from __future__ import annotations

import os
from pathlib import Path
import tarfile
import tempfile
from contextlib import closing
from typing import List, Optional

from flashing.adaptive.remote_adaptive_controller import RemoteAdaptiveController
from flashing.flash_graph import FlashGraph
from log.format import BGColor, FGColor
from log.utils import dump_colored_figlet_txt, dump_failure, dump_success, dump_time
from ssh.ssh_connection_handler import SSHConnectionHandler
from upload import UploadOp, UploadOpFactory
from utils.file_system import remove_suffixes
from utils.runtime import RuntimeTimer
from utils.tar import get_tar_leading_dirs


class RRDATAFlashOp:
    """Class that encapsulates the steps necessary to
       'flash' the RRDATA stack towards an IDC.

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

    magicString = "RRDATAFlashOp"

    def __init__(self, flash_graph: FlashGraph, name: str, tar_filename: str, workspace_dir: str, uploader: UploadOp):
        """Constructor fills member attributes and expects and existing testbench object.
        """
        # Get the testbench environment.
        self._name = name
        self.tarFilename = tar_filename
        self.graph = flash_graph
        self.config = flash_graph.config
        self.magicString = self.magicString

        self.workspaceDir = workspace_dir
        self.uploader = uploader
        # Use the logger from the graph node.
        self.logger = self.graph.logger

        self.idc_adaptive = RemoteAdaptiveController(logger=self.logger)

        # Report on last flash attempt.
        self._report = [""]

    @classmethod
    def create(cls, flash_graph: FlashGraph) -> Optional[RRDATAFlashOp]:
        """Creator method that retrieves all necessary information
           from an FlashGraph and forwards the
           creation to the default/standard constructor.
        Args:
            flash_graph (_type_): _description_
        """
        # TODO: (vibenzi) create class method that can be called by the FlashOpFactory
        if not flash_graph.config.modules["rrdata"].update:
            return None

        logger = flash_graph.logger

        tar_filename = flash_graph.config.modules["rrdata"].sources["source"].url
        if tar_filename is not None and os.path.isfile(tar_filename) and tarfile.is_tarfile(tar_filename):
            logger.debug(f"RRDATAFlashOp uses tarfile at {tar_filename}")
        else:
            return None

        graph_workspace = flash_graph.workingDir
        workspace_dir = graph_workspace / "rrdata"
        os.makedirs(workspace_dir)

        # Strip extension/suffices (e.g. tar.gz)
        name = remove_suffixes(str(tar_filename))

        uploader = UploadOpFactory(flash_graph.config, flash_graph.logger).create()

        # Create AdaptiveFlashOp from proper data.
        return cls(flash_graph, name, tar_filename, workspace_dir, uploader)

    @property
    def name(self):
        return self._name

    @property
    def report(self):
        return "\n".join(self._report)

    @property
    def RRDATA_RR_DATA_DIR(self):
        return "/usr/local/driveworks/data"
        # Currently, the mount seems not be flashable. Throwing directory not exists errors. Therefor using the versioned directory
        # return "/usr/local/driveworks/data"

    def is_valid_rrdata_tar_file(self, path: Path) -> bool:
        # TODO: Check directory structure!
        if tarfile.is_tarfile(path):
            return True

        self.logger.info(f"{path} is not a valid RRDATA tar file.")

        return False

    def get_top_level_tarfile(self, path: Path) -> List[str]:
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

    def rm_old_data_on_target(self, top_level_dir: list, ssh: SSHConnectionHandler) -> None:
        """
            Removes the old directories and files in the target system
        """
        for i in top_level_dir:
            dir = os.path.join(self.RRDATA_RR_DATA_DIR, i)
            cmd = f"rm -r {dir}"
            _, stdout, _ = ssh.exec_command(cmd)

    def flash(self) -> bool:
        """ """

        self.logger.info(dump_colored_figlet_txt(type(self).__name__, fgcolor=FGColor.BLACK, bgcolor=BGColor.GREEN))

        # I. Make sure files are there.
        if os.path.isfile(self.tarFilename):
            pass
        else:
            raise FileNotFoundError(f"File not available at given path: {self.tarFilename}")

        tar_file_path = Path(self.tarFilename)

        # II. Check a valid ADAPTIVE-type tar-file was given.
        # NOTE: is_valid ... may also be done in FrontLoading!??
        self.logger.info("Check for valid RRDATA tar file:")
        valid = self.is_valid_rrdata_tar_file(tar_file_path)

        if not valid:
            self.logger.error("Could not use provided RRDATA tar file for flashing! Aborting RRDATA flashing.")
            return False

        files = [tar_file_path]
        targets = [self.RRDATA_RR_DATA_DIR]

        with SSHConnectionHandler(self.config, logger=self.logger) as ssh:
            if ssh is None:
                self.logger.error(f"{dump_failure()} establishing SSH Connection! ")
                return False

            self.logger.info("Stopping adaptive")
            self.idc_adaptive.stop(ssh)
            self.logger.info("Stopping adaptive DONE:")

            for source, target in zip(files, targets):
                self.logger.info("-")
                self.logger.info(f"Flashing {source}")

                # Actual 'flashing'.
                # NOTE: The "retries" are handled in a do-while loop which makes exception handling easier.
                max_nr_of_retries = 1
                flash_success = False
                trial = 0

                while True:

                    if trial > max_nr_of_retries:
                        break

                    if trial > 0:
                        dotprogress_str = "." * trial
                        self.logger.info(f"Retrying flashing {dotprogress_str}")

                    try:
                        # Now we copy payload data to device.
                        self.logger.info("Extracting source files to temporary directory")

                        rrdata_top_level_tar = self.get_top_level_tarfile(source)
                        self.rm_old_data_on_target(rrdata_top_level_tar, ssh)

                        # Create local tmp extract dir
                        with tempfile.TemporaryDirectory(dir=self.workspaceDir) as tmpdir_name:
                            tmpdir = Path(tmpdir_name)

                            # extract source tarball
                            with closing(tarfile.open(source)) as archive:
                                leading_dirs = get_tar_leading_dirs(archive)
                                self.logger.debug(f"leading_dirs: {Path(*leading_dirs)}")

                                members = []
                                for member in archive.getmembers():
                                    # rewrite member if leading_dirs >= 2
                                    # ./rrdata/trafficlightturning-hyperion8 -> ./trafficlightturning-hyperion8
                                    strip_components = len(leading_dirs) - 1 if len(leading_dirs) > 1 else 0
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

            self.logger.warning("PLEASE REBOOT DEVICE AFTER SUCCESSFUL FLASH!")
            self._report.append(f"PLEASE REBOOT DEVICE AFTER SUCCESSFUL FLASH!")

        return flash_success
