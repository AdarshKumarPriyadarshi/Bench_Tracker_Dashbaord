from abc import ABC, abstractmethod


class Logger(ABC):
    @abstractmethod
    def info(self, *args, **kwargs):
        raise NotImplementedError("Method to be defined in Logger implementation")

    @abstractmethod
    def debug(self, *args, **kwargs):
        raise NotImplementedError("Method to be defined in Logger implementation")

    @abstractmethod
    def warning(self, *args, **kwargs):
        raise NotImplementedError("Method to be defined in Logger implementation")

    @abstractmethod
    def error(self, *args, **kwargs):
        raise NotImplementedError("Method to be defined in Logger implementation")

    @abstractmethod
    def critical(self, *args, **kwargs):
        raise NotImplementedError("Method to be defined in Logger implementation")
