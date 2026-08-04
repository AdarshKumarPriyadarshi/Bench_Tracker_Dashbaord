import pathlib

from flashing.adaptive.adaptive_paths import AdaptivePaths
from flashing.adaptive.remote_adaptive_controller import RemoteAdaptiveController
from log.logger import Logger
from ssh.ssh_connection_handler import SSHConnectionHandler


class ComissioningHandler:
    def __init__(self, logger: Logger):
        self.logger = logger

    @property
    def IDC_STORAGE_PATH(self):
        return "/storage"

    @property
    def COMISSIONING_TARFILENAME(self):
        return "sec_comissioning.tgz"

    @property
    def BACKUP_COMISSIONING_TARFILEPATH(self):
        return self.IDC_STORAGE_PATH + "/" + self.COMISSIONING_TARFILENAME

    @property
    def EXTRACT_TAR_CMD(self):
        return f"tar -zxvf {self.BACKUP_COMISSIONING_TARFILEPATH} -C /"

    def backup_files(self, ssh: SSHConnectionHandler, host_dir: pathlib.Path):

        try:
            idc_tar_filepath = self.IDC_STORAGE_PATH + "/" + self.COMISSIONING_TARFILENAME
            adaptive_specs = AdaptivePaths()
            COMISSIONING_FILES = [
                adaptive_specs.ADAPTIVE_PERSISTENCY_TARGET + "/amsr_ssasecd/amsr_ssasec_key_value_storage",
                adaptive_specs.ADAPTIVE_PERSISTENCY_TARGET + "/amsr_vector_fs_sec_cryptostack_daemon/slots/",
            ]

            tar_sources = " ".join(COMISSIONING_FILES)
            ssh.exec_command(f"tar -czvf {idc_tar_filepath} {tar_sources}")

            self.logger.info(f"Saved comissioning backup to {idc_tar_filepath}.")
            ssh.downloadFromDevice(idc_tar_filepath, host_dir)
            self.logger.info(f"Copied comissioning backup to host into {host_dir}.")

        except Exception as e:
            self.logger.error(f"Failed to create comissioning backup.")
            raise e

    def restore_comissioning_files(self, ssh: SSHConnectionHandler):

        adaptive_specs = AdaptivePaths()
        RemoteAdaptiveController(logger=self.logger).mount_partitions(
            ssh, [adaptive_specs.ADAPTIVE_TARGET, adaptive_specs.ADAPTIVE_PERSISTENCY_TARGET]
        )
        try:
            ssh.exec_command(self.EXTRACT_TAR_CMD)
            return True

        except Exception as e:
            self.logger.error(f"Failed to restore comissioning backup.")
            self.logger.error(f"{e}")
            return False
