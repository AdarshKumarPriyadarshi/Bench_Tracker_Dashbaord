import logging
from shutil import which

from config.flash_config import FlashConfig
from .scp import ScpUploadOp
from .scp_py import ScpPyUploadOp
from .upload_op import UploadOp

use_scp_binary_if_available = True


class UploadOpFactory:
    def __init__(self, config: FlashConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger

    def create(self) -> UploadOp:
        if use_scp_binary_if_available and which("scp") and which("sshpass"):
            self.logger.debug(f"UploadOp {ScpUploadOp.__name__:<20} used.")
            return ScpUploadOp(self.config, self.logger)

        self.logger.debug(f"UploadOp {ScpPyUploadOp.__name__:<20} used.")
        return ScpPyUploadOp(self.config, self.logger)
