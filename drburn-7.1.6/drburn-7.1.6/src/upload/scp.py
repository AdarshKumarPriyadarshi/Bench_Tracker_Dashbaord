import os
import subprocess
from pathlib import Path
from typing import Union, Iterable

from log.utils import dump_failure
from ssh.ssh_connection_handler import SSHConnectionHandler
from .upload_op import UploadOp


class ScpUploadOp(UploadOp):
    def upload(self, copy_from: Union[Path, Iterable[Path]], copy_to: Path) -> None:
        if not isinstance(copy_from, Iterable):
            copy_from = [copy_from]

        def to_source(p: Path):
            if p.is_dir():
                return f'{p}/'
            return f"{p}"

        sources = list(map(to_source, copy_from))
        target = f"root@{self.config.idc.ip}:{copy_to}"

        self.logger.info(f"{self.__class__.__name__}: from HOST:")
        [self.logger.info(f"{'':<20}{source}") for source in sources]
        self.logger.info(f"{'     to   Device':<20}{copy_to}")

        args = ['sshpass',
                "-p", "root",
                "scp",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-P", f"{self.config.idc.port}",
                "-r",
                "-p"
                ]
        if self.config.debug:
            args.append("-v")

        exit_code = subprocess.call([*args, *sources, target])
        if exit_code != 0:
            raise Exception("SCP: Files copy failed!")

        # call sync
        with SSHConnectionHandler(self.config, logger=self.logger) as ssh:
            if ssh is None:
                self.logger.error(f"{dump_failure()} establishing SSH Connection! ")
                raise Exception("Could not establishing SSH Connection!")

            ssh.exec_command("sync")

        self.logger.info(f"SCP: Files copied successfully.")
