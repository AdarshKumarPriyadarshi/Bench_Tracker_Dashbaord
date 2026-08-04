import asyncio
from pathlib import Path
from typing import Union, Iterable, Optional

from log.utils import dump_failure
from ssh.ssh_connection_handler import SSHConnectionHandler
from .upload_op import UploadOp


class ScpPyUploadOp(UploadOp):
    def upload(self, copy_from: Union[Path, Iterable[Path]], copy_to: Path) -> None:
        if not isinstance(copy_from, Iterable):
            copy_from = [copy_from]

        def to_source(p: Path):
            if not p.exists():
                raise Exception(f'file not exists {p}')
            return f"{p}"

        sources = list(map(to_source, copy_from))

        self.logger.info(f"{self.__class__.__name__}: from HOST:")
        [self.logger.info(f"{'':<20}{source}") for source in sources]
        self.logger.info(f"{'     to   Device':<20}{copy_to}")

        upload_error: Optional[Exception] = None
        with SSHConnectionHandler(self.config, logger=self.logger) as ssh:
            try:
                if ssh is None:
                    self.logger.error(f"{dump_failure()} establishing SSH Connection! ")
                    raise Exception("Could not establishing SSH Connection!")

                ssh.scp.put(sources, str(copy_to), recursive=True, preserve_times=True)

                # call sync
                ssh.exec_command("sync")
            except Exception as e:
                upload_error = e

        if upload_error is not None:
            raise upload_error

        self.logger.info(f"{self.__class__.__name__}: File copied successfully.")
