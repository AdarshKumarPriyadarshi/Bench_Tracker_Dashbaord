from __future__ import annotations

import os
import pathlib
import subprocess
import time
from typing import Optional

import yaml

from config.config_front_loader import ConfigFrontLoader
from flashing.adaptive.comissioning_handler import ComissioningHandler
from flashing.flash_graph import FlashGraph
from log.format import FGColor, BGColor
from log.utils import dump_colored_figlet_txt, dump_failure, dump_time, dump_success
from ssh.ssh_connection_handler import SSHConnectionHandler
from system.host_pc import HostPC
from utils.file_system import remove_suffixes
from utils.url import adapt_url_domain


class BundleFlashOp:
    magicString = "BundleFlashOp"

    @classmethod
    def create(cls, flashGraph: FlashGraph) -> Optional[BundleFlashOp]:
        if not flashGraph.config.modules["bundle"].update:
            return None

        logger = flashGraph.logger

        bundleFilename = flashGraph.config.modules["bundle"].sources["source"].url
        if bundleFilename is not None and bundleFilename.is_file():
            logger.debug(f"BundleFlashOp uses bundle at  {bundleFilename}")
        else:
            logger.error(f"Can't create Bundle flash op! Please check bundle at '{bundleFilename}'!")
            return None

        name = remove_suffixes(str(bundleFilename))
        return cls(flashGraph, name, pathlib.Path(bundleFilename), pathlib.Path(flashGraph.workingDir))

    def __init__(self, flashGraph: FlashGraph, name: str, bundleFilename: pathlib.Path, workspaceDir: pathlib.Path):
        self._name = name
        self.bundle_filename = bundleFilename
        self.graph = flashGraph
        self.workspace_dir = workspaceDir
        self.logger = self.graph.logger
        self.config = self.graph.config

        self.idc_comissioning = ComissioningHandler(logger=self.logger)

        self._report = []

    @property
    def report(self):
        return "\n".join(self._report)

    @property
    def name(self):
        return self._name

    def comissioning_backup(self):
        # (fgritsc) TODO: Check if idc is powered? (minicom, serial ...)
        with SSHConnectionHandler(self.config, retry_timeout=30, logger=self.logger) as ssh:

            if ssh is None:
                self.logger.error(f"{dump_failure()} establishing SSH Connection! ")
                self.logger.error(f"{dump_failure()} Comissioning backup not possible!")
                return False

            # Create backup of 'comissioning' and store on host.
            self.idc_comissioning.backup_files(ssh, self.workspace_dir)

        self._report.append("Created comissioning backup.")
        return True

    def comissioning_restore(self):
        ssh_start_time = time.time()
        with SSHConnectionHandler(self.config, retry_timeout=600, logger=self.logger) as ssh:

            if ssh is None:
                self.logger.error(f"{dump_failure()} establishing SSH Connection! ")
                extract_cmd = self.idc_comissioning.EXTRACT_TAR_CMD
                self.logger.error(
                    (
                        "Failed to establish ssh connection.\n",
                        f"Please restore comissioning files manually with '{extract_cmd}'.",
                    )
                )
                return False

            ssh_connect_time = time.time()
            up_time = ssh_connect_time - ssh_start_time
            self.logger.info(f"IDC SSH port became active after {dump_time(up_time)}.")
            # Finally, restore comissioning files.
            # TODO: Success?
            self.idc_comissioning.restore_comissioning_files(ssh)

        self._report.append("Restored comissioning backup.")
        return True

    def adapt_docker_url(self, label: str, url: str):
        # NV bundled urls are not accessible by MB and not via DSCP
        # -> manually (!) mirror FC drops from NV to MB artifactory
        # -> remap URL from NV to MB or DSPC equivalent

        name = url.split("/")[-1]
        mb_base_url = "artifact.swf.i.mercedes-benz.com/adasndas-docker/drburn"
        new_url = f"{mb_base_url}/{name}"

        if HostPC.is_ds_pc():
            new_url = new_url.replace("artifact.swf.i.mercedes-benz.com", "dockerproxy.prod.carpc.adas.corpinter.net:80")

        self.logger.debug(f"Adapting {label} URL from {url} to {new_url}")
        self._report.append(f"Docker {label} remapped")

        return new_url

    def download_ddu(self, label, url: str):
        name = url.split("/")[-1]

        # don't change if not remotely downloaded
        # -> we cannot guess where the DDU would be located then
        if "source_original" not in self.config["bundle"]:
            self.logger.debug(f"Keeping {label} URL {url} due to local config")

            # try to find image locally
            local_path = self.bundle_filename.parent / name
            if not local_path.is_file():
                self.logger.error(f"Local bundle missing needed {label} DDU image at {local_path}")
                self._report.append(f"{label} DDU missing")
                return None
            else:
                self.logger.debug(f"Using local {label} DDU at {local_path}")
                self._report.append(f"{label} DDU local")

            return local_path

        source_path = "/".join(self.config["bundle"]["source_original"].split("/")[0:-1])

        new_url = f"{source_path}/{name}"
        new_url = adapt_url_domain(new_url)
        self.logger.debug(f"Adapting {label} URL from {url} to {new_url}")

        # download utility expects existing file -> create it
        download_path = self.workspace_dir / name
        download_path.touch()

        self.logger.info(f"Downloading {label} DDU, this may take a while...")
        self.logger.debug(f"Downloading {label} DDU from {new_url} to {download_path}")
        error = ConfigFrontLoader.download_url_using_wget(self.logger, new_url, download_path)
        if error:
            self.logger.error(f"Failed to download {label} DDU from: {new_url}")
            self._report.append(f"{label} DDU download failed")
            return None
        else:
            self._report.append(f"{label} DDU download")

        return download_path

    def log_flash_headline(self):
        self.logger.info(dump_colored_figlet_txt(type(self).__name__, fgcolor=FGColor.BLACK, bgcolor=BGColor.RED))

    def flash(self):
        self.log_flash_headline()

        fc_url = None
        ddu_paths = []
        docker_remaps = []

        # read bundle
        with open(self.bundle_filename) as file:
            bundle = yaml.load(file, Loader=yaml.CLoader)

        # convert/download sources
        for source in bundle["Info"]["Source"]:
            source_url = bundle["Info"]["Source"][source]["URL"]

            # URL type: DDU
            if source_url.endswith(".tgz"):
                mapped_path = self.download_ddu(source, source_url)
                if not mapped_path:
                    return False

                ddu_paths.append(mapped_path)

            # URL type: Docker
            elif source_url.startswith("nvcr.io") and ":" in source_url:
                mapped_name = self.adapt_docker_url(source, source_url)
                if not mapped_name:
                    return False

                docker_remaps.append((source_url, mapped_name))

                if source == "Flashing Container":
                    fc_url = mapped_name

            # URL type: unsupported
            else:
                self.logger.error(f"Unsupported Bundle URL {source_url} for {source}")
                return False

        # FC needs to be specified to continue
        if not fc_url:
            self.logger.error("Bundle has no Flashing Container entry")
            return False

        # save bundle with modifications
        with open(self.bundle_filename) as file_in:
            # use read, replace, write since input yaml uses references that are resolved on import
            content = file_in.read()

            # remap docker URLs
            for old, new in docker_remaps:
                content = content.replace(old, new)

            with open(self.workspace_dir / self.bundle_filename.name, "w") as file_out:
                file_out.write(content)

        # backup comissioning, bundle might flash adaptive persistency
        comissioning_successful = self.comissioning_backup()
        if not comissioning_successful:
            self.logger.warning("Could not execute comissioning. DDU-flashing continues anyway!")

        # setup flashing
        env = os.environ.copy()
        env["FC_URL"] = fc_url
        env["BUNDLE"] = str(self.bundle_filename.name)

        mounts = []
        # if DDU is not downloaded, map it into container
        for ddu_path in ddu_paths:
            if ddu_path.parent != self.workspace_dir:
                mounts += ["-v", f"{ddu_path}:/rfs/cache/img/{ddu_path.name}"]

        # adapted from handbook
        # see: https://docs.google.com/document/d/1Ekl9396A17_4IWMpZdZmbH2HDSQj94-B0zt_ZIHIJwc/edit?pli=1#heading=h.cziubcbsj4ws
        # title: ATG-B QNX Vehicle Dev Handbook [TOT]
        cmd = [
            'docker', 'run',
            '--net', 'host',
            '-it',
            '--name', 'flashing_container',
            '--privileged',
            '-v', '/dev/bus/usb:/dev/bus/usb',
            '-v', '/run/udev:/run/udev',
            '-w', '/rfs/update_tools',
            '-v', f'{self.workspace_dir}/log:/rfs/cache/log',
            '-v', f'{self.workspace_dir}:/rfs/cache/img',
            *mounts,
            '--mount', 'type=bind,source=/etc/device_config/device_config.yaml,target=/rfs/cache/device_config.yaml',
            '--rm',
            f'{fc_url}',
            'python3', 'fc-cli.py',
            '--bundle-url', f'/rfs/cache/img/{self.bundle_filename.name}',
            '--token', 'NA'
        ]

        self.logger.info(f"Running Bundle Flashing: {' '.join(cmd)}")
        res = subprocess.run(cmd, cwd=self.workspace_dir, env=env)
        if res.returncode == 0:
            self.logger.info(f"{dump_success()} Bundle Flashing terminated gracefully with returncode 0.")
            self._report.append("Running bundle flash.")
        else:
            self.logger.error(f"{dump_failure()} Bundle Flashing terminated with returncode {res.returncode}.")
            self._report.append("Running bundle flash failed!")
            return False

        self._report.append("Ran ddu flashing.")

        # restore commissioning
        comissioning_restored = self.comissioning_restore()
        if not comissioning_restored:
            self.logger.warning("Could not restore comissioning! (DDU flashing was successful)")
            self._report.append("Restoring comissionig backup failed. Advice to user: -> Restore manually!")
            return False

        return True





