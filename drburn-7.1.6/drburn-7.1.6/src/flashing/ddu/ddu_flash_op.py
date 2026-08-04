from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Optional

from config.flash_config import ModuleDDU
from flashing.adaptive.remote_adaptive_controller import RemoteAdaptiveController
from flashing.adaptive.comissioning_handler import ComissioningHandler
from flashing.flash_graph import FlashGraph
from log.format import BGColor, FGColor
from log.utils import dump_colored_figlet_txt, dump_failure, dump_success, dump_time
from system.disk_space_statistics import DiskSpaceStatistics
from system.host_pc import HostPC
from system.utils import bytes_to_gb
from utils.file_system import remove_suffixes
from utils.runtime import RuntimeTimer


class DDUFlashOp:
    """Class that encapsulates the steps necessary to
       flash a given DDU image twoards an IDC.

       Flash in this context uses at some point the
       bootburn tool, but that is just for the fans.

    To sum up the steps:
    1. Get the my-ddu-ota-pkg_***.tgz
    2. Validate the tar file (expected content is there).
    3. Make sure flash-bash script is there.
     3.1 If given -> use this, otherwise use drburn default flash_ddu.sh
     3.2 Make sure *.tgz and *.sh are next to each other.
    4. Establish ssh - connection and do commissioning.
    5. RUN   flash command!
    6. Establish ssh - connection and restore comissioning.

    """

    magicString = "DDUFlashOp"

    def __init__(self, flashGraph: FlashGraph, name: str, tarFilename: str, flashScript: str, workspaceDir: str,
                 clear_persistency: bool, customar_data_path: Optional[str], aurix_port: str):
        self._name = name
        self.tarFilename = tarFilename
        self.flashScript = flashScript
        self.clear_persistency = clear_persistency
        self.customar_data_path = customar_data_path
        self.aurix_port = aurix_port
        self.graph = flashGraph
        self.config = self.graph.config
        self.magicString = self.magicString
        self.workspaceDir = workspaceDir

        # Use the logger from the graph node.
        self.logger = self.graph.logger

        # 'Controllers' which help interacting with the device/IDC.
        self.idc_adaptive = RemoteAdaptiveController(logger=self.logger)
        self.idc_comissioning = ComissioningHandler(logger=self.logger)

        # Report on last flash attempt.
        self._report = []

    @classmethod
    def create(cls, flashGraph: FlashGraph) -> Optional[DDUFlashOp]:
        """Creator method that retrieves all necessary information
           from an FlashGraph and forwards the
           creation to the default/standard constructor.
        Args:
            flashGraph (FlashGraph): FlashGraph object that carries config information.
        """
        # TODO: (vibenzi) create class method that can be called by the FlashOpFactory
        module = flashGraph.config.modules["ddu"]

        if not isinstance(module, ModuleDDU):
            return None

        if not module.update:
            return None

        logger = flashGraph.logger

        tarFilename = Path(module.sources["source"].url)
        if tarFilename is not None and os.path.isfile(tarFilename) and tarfile.is_tarfile(tarFilename):
            logger.debug(f"DDUFlashOp uses tarfile at {tarFilename}")
            pass
        else:
            logger.error(f"Can't create DDU flash op! Please check tarfile at '{tarFilename}'!")
            return None

        flash_script = module.sources["script"].url
        if flash_script is not None and os.path.isfile(flash_script) :
            logger.debug(f"DDUFlashOp uses script file at {flash_script}")
            pass
        else:
            logger.error(f"Can't create DDU flash op! Please check flash script at '{flash_script}'!")
            return None

        # Only ONE my-ddu*.tgz file in directory allowed -> safely have a temporary working directory.
        workspaceDir = flashGraph.workingDir / "ddu_flashing"
        os.makedirs(workspaceDir)

        workspace_stats = DiskSpaceStatistics(workspaceDir)
        ddu_file_size_GB = bytes_to_gb(tarFilename.stat().st_size)
        if workspace_stats.freeGB > ddu_file_size_GB:
            # Copies tar file to workspaceDir
            destfile = shutil.copy(tarFilename, workspaceDir)

            if Path(destfile).is_file():
                # Adjust new tarFilename!
                if not (Path(destfile).name.startswith("my-ddu-ota-pkg")):
                    old_destfile = destfile
                    destfile = str(Path(old_destfile).parent.joinpath(f'my-ddu-ota-pkg_{tarFilename.name}'))
                    os.rename(old_destfile, destfile)
                tarFilename = Path(destfile)
            else:
                logger.error(f"Copying ddu-file to working directory failed! -> No DDU flashing possible!")

        else:
            logger.error(
                f"Could not create DDU flashing op since not enough disk space ({workspace_stats.freeGB} GB < {ddu_file_size_GB} GB) ! -> NO DDU flashing!\n"
                f"Workspace directory: '{workspaceDir}'\n"
            )
            return None

        # Ensure bash script for flashing is available (flash_ddu.sh)
        if flash_script is not None and flash_script.is_file():
            logger.debug(f"Found ddu-bash-script at {flash_script}")

            if tarFilename.parent == flash_script.parent:
                logger.info("ddu-file and ddu-flash script share same directory.")
            else:
                shutil.copyfile(flash_script, tarFilename.parent / "flash_ddu.sh")
                flash_script = tarFilename.parent / "flash_ddu.sh"

        else:
            # Copies the default flash_ddu.sh script to the given targetDir.
            #     a) delete already available flash_ddu.sh in advance
            #     b) copy src/flash_ddu.sh to basedir of my_ddu*.tgz
            #     c) Double-check flash_ddu.sh got copied
            # a)
            # targetDir is dir of tarfile!
            targetDir = tarFilename.parent
            assert isinstance(
                targetDir, Path
            ), f"Expected pathlib.Path type for targetDir while obtaining {type(targetDir)}"

            targetFlashDDUScript = targetDir / "flash_ddu.sh"
            if targetFlashDDUScript.is_file():
                os.remove(targetFlashDDUScript)
                if not targetFlashDDUScript.is_file():
                    logger.error(
                        f"Multiple(?) flash_ddu.sh files next to the provided ddu.tar file! ({tarFilename}) no ddu flashing possible!"
                    )
                    return None
            # b)
            repo_flash_script = Path("flash_ddu.sh")
            thisDir = Path(".")
            repo_flash_script_lst = list(thisDir.glob(f"**/flash_ddu.sh"))
            if len(repo_flash_script_lst) == 1:
                flash_script = repo_flash_script_lst[0]
                logger.info(f"Using repository-flash-ddu script: {repo_flash_script}")
            else:
                if len(repo_flash_script_lst) > 1:
                    logger.error(f"Found more than one of {repo_flash_script_lst}!")
                    logger.error(
                        f"Could not determine unique flash_ddu.sh script from repo directory!-> no ddu flashing!"
                    )
                elif len(repo_flash_script_lst) == 0:
                    logger.error(f"No flash_ddu.sh found in repo-directory!-> no ddu-flashing possible!")
                else:
                    logger.critical(
                        "Undefined case detected in finding flash_ddu script! --> no ddu flashing possible!"
                    )
                return None
            shutil.copy(repo_flash_script, targetFlashDDUScript)
            # c)
            if not targetFlashDDUScript.is_file():
                raise FileNotFoundError(f"Could not find flash_ddu.sh at target dest! {targetDir}")
            flash_script = targetFlashDDUScript

        customer_data_json_path: Optional[str] = None
        if HostPC.is_MTTF():
            # Copies the default customer_data.json to the given targetDir.
            #     a) delete already available customer_data.json in advance
            #     b) copy src/customer_data.json to basedir of my_ddu*.tgz
            #     c) Double-check customer_data.json got copied
            # a)
            # targetDir is dir of tarfile!
            targetDir = tarFilename.parent
            assert isinstance(
                targetDir, Path
            ), f"Expected pathlib.Path type for targetDir while obtaining {type(targetDir)}"

            target_customer_data_json = targetDir / "customer_data.json"
            if target_customer_data_json.is_file():
                os.remove(target_customer_data_json)
                if not target_customer_data_json.is_file():
                    logger.error(
                        f"Multiple(?) customer_data.json files next to the provided ddu.tar file! ({tarFilename}) no ddu flashing possible!"
                    )
                    return None
            # b)
            thisDir = Path(".")
            repo_customer_data_lst = list(thisDir.glob(f"**/customer_data.json"))
            if len(repo_customer_data_lst) == 1:
                repo_customer_data_script = Path(".") / repo_customer_data_lst[0]
                logger.info(f"Using repository-customer_data.json: {repo_customer_data_script}")
            else:
                if len(repo_customer_data_lst) > 1:
                    logger.error(f"Found more than one of {repo_customer_data_lst}!")
                    logger.error(
                        f"Could not determine unique customer_data.json script from repo directory!-> no ddu flashing!"
                    )
                elif len(repo_customer_data_lst) == 0:
                    logger.error(f"No customer_data.json found in repo-directory!-> no ddu-flashing possible!")
                else:
                    logger.critical(
                        "Undefined case detected in finding customer_data.json! --> no ddu flashing possible!"
                    )
                return None
            shutil.copy(repo_customer_data_script, target_customer_data_json)
            # c)
            if not target_customer_data_json.is_file():
                raise FileNotFoundError(f"Could not find customer_data.json at target dest! {targetDir}")
            customer_data_json_path = str(target_customer_data_json)

        # Use the flash-data as name provider (trimmed by extension).
        name = remove_suffixes(str(tarFilename))

        if HostPC.is_MTTF():
            return DDUFlashOpMTTF(flashGraph, name, str(tarFilename), flash_script, flashGraph.workingDir, module.clear_persistency, customer_data_json_path, module.aurix_port)
        elif HostPC.is_ds_pc():
            return DDUFlashOpDSPC(flashGraph, name, str(tarFilename), flash_script, flashGraph.workingDir, module.clear_persistency, customer_data_json_path, module.aurix_port)
        else:
            return cls(flashGraph, name, str(tarFilename), flash_script, flashGraph.workingDir, module.clear_persistency, customer_data_json_path, module.aurix_port)

    @property
    def report(self):
        return "\n".join(self._report)

    @property
    def name(self):
        return self._name

    @property
    def report(self):
        return "\n".join(self._report)

    def extract_flashware(self) -> bool:
        """
        Extract flashware image from tarball and updates the tarFilename to be flashed.

        On error, prints the error message and return False.
        """

        self.logger.info(f"Running flashware extracting")

        if not os.path.isfile(self.tarFilename):
            self.logger.error(f"File not available at given path: {self.tarFilename}")
            return False

        if not tarfile.is_tarfile(self.tarFilename):
            self.logger.error("Provided ddu_file is NOT a tar-file!")
            return False

        # Read archived flashware tarball filename
        list_cmd = [
            "tar",
            "tf",
            f"{self.tarFilename}"
        ]
        result = subprocess.run(list_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.error(result.stderr)

        flashware_filename = ""
        for line in result.stdout.splitlines():
            if not line:
                continue

            self.logger.debug(line)
            if str(line).strip().startswith("./mbu_images_") and str(line).strip().endswith(".tgz"):
                flashware_filename = str(line).strip()
                break
            if str(line).strip().startswith("./slim_qnx_") and str(line).strip().endswith(".tgz"):
                flashware_filename = str(line).strip()
                break

        if result.returncode == 0 and len(flashware_filename) > 0:
            self.logger.info(f"Found flashware image: {flashware_filename}")
            self._report.append(f"Found flashware image in tarball.")
        else:
            self.logger.error(f"{dump_failure()} flashware image not found in {self.tarFilename}")
            self._report.append(f"Extracting flashware image failed!")
            return False

        # Extract archived flashware tarball
        target_directory = Path(self.tarFilename).parent
        target_directory.mkdir(parents=True, exist_ok=True)
        extract_flashware_image_cmd = [
            "tar",
            "xfv",
            f"{self.tarFilename}",
            "-C",
            str(target_directory),
            "--strip-components=1",
            f"{flashware_filename}",
        ]
        result = subprocess.run(extract_flashware_image_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.error(result.stderr)

        for line in result.stdout.splitlines():
            self.logger.debug(line)

        for path in target_directory.iterdir():
            self.logger.debug(path.name)

        target_filename = target_directory.joinpath(Path(flashware_filename).name).resolve()
        if result.returncode == 0 and target_filename.exists():
            self.logger.info(f"Extracted flashware image to: {str(target_filename)}")
            self._report.append(f"Extracted flashware image {flashware_filename}")
        else:
            self.logger.error(f"{dump_failure()} Could not extract flashware image of {self.tarFilename}")
            self._report.append(f"Extracting flashware image failed!")
            return False

        self.tarFilename = str(target_filename)
        return True

    def check_for_valid_setup(self):
        """
        Ensures that tar file and flash script exists. Inspects tar file to be valid ddu file.
        """

        # I. Make sure files are there.
        if not os.path.isfile(self.tarFilename):
            self.logger.error(f"File not available at given path: {self.tarFilename}")
            return False

        ddu_file = self.tarFilename
        flashDDUScript = self.flashScript

        # Check ddu-file is available:
        if os.path.isfile(ddu_file):
            self.logger.info(f"Found ddu file: {ddu_file}")
        else:
            self.logger.error(f"ddu file ({ddu_file}) not found.")
            return False

        # Check flash-script is available:
        if os.path.isfile(flashDDUScript):
            self.logger.info(f"Found ddu-flash-script: {flashDDUScript}")
        else:
            self.logger.error(f"ddu-flash-script ({flashDDUScript}) not found.")
            return False

        # Check customer-data-json is available:
        if self.customar_data_path is not None:
            if os.path.isfile(self.customar_data_path):
                self.logger.info(f"Found customer_data.json: {self.customar_data_path}")
            else:
                self.logger.error(f"customer_data.json ({self.customar_data_path}) not found.")
                return False

        # Tarfile? (.tar.gz or .tgz?)
        if not tarfile.is_tarfile(ddu_file):
            self.logger.error("Provided ddu_file is NOT a tar-file!")
            return False

        return True

    def log_flash_headline(self):
        self.logger.info(dump_colored_figlet_txt(type(self).__name__, fgcolor=FGColor.BLACK, bgcolor=BGColor.RED))

    def flash(self):
        self.log_flash_headline()

        if "mbu_orin_flashware" in self.tarFilename or "slim_qnx_orin_flashware" in self.tarFilename:
            if not self.extract_flashware():
                return False

        # Make sure attributes are filled appropriately,
        # - ddu-file and
        # - flash_ddu.sh are at proper places.
        # Easy out.
        if not self.check_for_valid_setup():
            return False

        # ========================
        # F L A S H I N G
        # ========================

        cmd = ["bash", str(self.flashScript)]
        if self.clear_persistency:
            cmd.append("-c")

        if self.customar_data_path is not None:
            # use customer data to flash DDU
            cmd.append("-w")

        if self.aurix_port:
            cmd.append("-a")
            cmd.append(self.aurix_port)

        cmd.append("-t")
        cmd.append(self.tarFilename)

        self.logger.info(f"Running DDU Flashing: {' '.join(cmd)}")
        proc_res = subprocess.run(cmd)
        if proc_res.returncode == 0:
            self.logger.info(f"{dump_success()} DDU Flashing terminated gracefully with returncode 0.")
            self._report.append("Running flash_ddu.sh script.")
        else:
            self.logger.error(f"{dump_failure()} DDU Flashing terminated with returncode {proc_res.returncode}.")
            self._report.append("Running flash_ddu.sh script failed!")
            return False

        shutil.rmtree(self.workspaceDir / "ddu_flashing", ignore_errors=True)
        self._report.append("Ran ddu flashing.")

        return True


class DDUFlashOpDSPC(DDUFlashOp):
    def flash(self):
        self.log_flash_headline()

        if "mbu_orin_flashware" in self.tarFilename or "slim_qnx_orin_flashware" in self.tarFilename:
            if not self.extract_flashware():
                return False

        # Make sure attributes are filled appropriately,
        # - ddu-file and
        # - flash_ddu.sh are at proper places.
        # Easy out.
        if not self.check_for_valid_setup():
            return False

        # Make sure we are on the DSPC (double-check).
        if not HostPC.is_ds_pc():
            self.logger.error("Host is NOT DSPC as epxected. Misconfiguration!")
            self.logger.error("    DDU flashing not started.")
            return False

        # ========================
        # F L A S H I N G
        # ========================
        # NOTE: DDU flashing does *NOT* require an ssh connection.
        # (fgritsc) TODO: Check if idc is powered? (minicom, serial ...)

        # Safely copy environment.
        flash_env = os.environ.copy()
        flash_env[
            "FLASHING_CONTAINER"
        ] = "dockerproxy.prod.carpc.adas.corpinter.net:80/adas-docker/ddu_workspace/flashing_container:v6.0.8.0"
        cmd = ["bash", str(self.flashScript)]
        if self.clear_persistency:
            cmd.append("-c")

        if self.aurix_port:
            cmd.append("-a")
            cmd.append(self.aurix_port)

        cmd.append("-t")
        cmd.append(self.tarFilename)

        self.logger.info(f"Using docker: {flash_env['FLASHING_CONTAINER']}")
        self.logger.info(f"Run ddu-flashing: {cmd}")
        # Run.
        proc_res = subprocess.run(cmd, env=flash_env, stderr=subprocess.PIPE)
        if proc_res.returncode == 0:
            self.logger.info(f"{dump_success()} DDU flashing from DSPC terminated gracefully with returncode 0.")
        else:
            self.logger.error(
                f"{dump_failure()} DDU flashing from DSPC terminated with returncode {proc_res.returncode}."
            )
            self.logger.error(f"{proc_res.stderr}")
            return False

        self._report.append("Ran ddu flashing.")

        return True


class DDUFlashOpMTTF(DDUFlashOp):
    def flash(self):
        self.log_flash_headline()

        if "mbu_orin_flashware" in self.tarFilename or "slim_qnx_orin_flashware" in self.tarFilename:
            if not self.extract_flashware():
                return False

        # Make sure attributes are filled appropriately,
        # - ddu-file and
        # - flash_ddu.sh are at proper places.
        # Easy out.
        if not self.check_for_valid_setup():
            return False

        # Make sure we are on the MTTF (double-check).
        if not HostPC.is_MTTF():
            self.logger.error("Expecting username >gatewayuser< on MTTF. Misconfiguration!")
            self.logger.error("    DDU flashing not started.")
            return False

        ddu_file = Path(self.tarFilename)
        flash_ddu_script = Path(self.flashScript)

        # Working directory on MTTF (this is a physical disk space)
        basedir = Path("/builds/idc/")

        # Temporary dirname from which flashing is started, holding my-ddu*.tar.gz and flash_ddu.sh
        tmp_dirname = "tmp_ddu_flashing"

        # As long as the docker is run on the MTTF how it is, the sudo for copying etc is necessary.
        def run_cmd_as_sudo(cmd):
            cmd = f"echo passw0rd | sudo -S {cmd}"
            self.logger.info(f"Running: {cmd}")
            os.system(cmd)

        # Create temporary directory.
        abs_dirname = basedir.joinpath(tmp_dirname)
        if abs_dirname.is_dir():
            pass
            # Directory already exists.
        else:
            self.logger.info(f"Creating working directory for ddu-flashing: {str(abs_dirname)}")
            run_cmd_as_sudo(f"mkdir {str(abs_dirname)}")

        # Make sure directory is available.
        if abs_dirname.is_dir():
            self.logger.info(f"Using {str(abs_dirname)} for flashing (putting my-ddu*.tar.gz and flash_ddu.sh there)")

            # I. Cleanup: Make sure old/previous ddu-files are removed!
            for fname in os.listdir(abs_dirname):
                if ("mbu" in fname or "ddu" in fname) and ".tgz" in fname or "flash_ddu.sh" in fname:
                    run_cmd_as_sudo(f"rm -v {str(abs_dirname)}/{fname}")

            # II: Placing my-ddu*.tar.gz  and flash_ddu.sh in temporary directory.
            run_cmd_as_sudo(f"cp -v {str(flash_ddu_script)} {str(abs_dirname)}")
            run_cmd_as_sudo(f"cp -v {str(ddu_file)} {str(abs_dirname)}")
            if self.customar_data_path is not None:
                customer_data_json = Path(self.customar_data_path)
                run_cmd_as_sudo(f"cp -v {str(customer_data_json)} {str(abs_dirname)}")

            # III: FLASH command
            bash_cmd = f"cd {str(abs_dirname)} && bash {flash_ddu_script.name} -fd"
            if self.clear_persistency:
                bash_cmd += " -c"

            if self.customar_data_path is not None:
                bash_cmd += " -w"

            if self.aurix_port:
                bash_cmd += f" -a {self.aurix_port}"

            bash_cmd += f" -t {str(abs_dirname.joinpath(ddu_file.name))}"

            self.logger.info(f"bashCmd: {bash_cmd}")
            proc_res = subprocess.run(bash_cmd, shell=True)
            if proc_res.returncode == 0:
                self.logger.info(f"{dump_success()} DDU Flashing terminated gracefully with return code 0.")
                self._report.append("Running flash_ddu.sh script.")
            else:
                self.logger.error(f"{dump_failure()} DDU Flashing terminated with return code {proc_res.returncode}.")
                self._report.append("Running flash_ddu.sh script failed!")
                return False

            shutil.rmtree(abs_dirname, ignore_errors=True)
            self._report.append("Ran ddu flashing.")

        return True
