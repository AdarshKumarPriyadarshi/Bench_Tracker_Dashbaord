import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Iterable

from config.flash_config import FlashConfig


class UploadOp(ABC):

    def __init__(self, config: FlashConfig, logger : logging.Logger) -> None:
        self.config = config
        self.logger = logger

    @abstractmethod
    def upload(self, copy_from: Union[Path, Iterable[Path]], copy_to: Path) -> None:
        pass
