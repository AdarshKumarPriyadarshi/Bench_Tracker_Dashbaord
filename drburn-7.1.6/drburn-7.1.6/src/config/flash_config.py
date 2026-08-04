from __future__ import annotations

import argparse
import shlex
import sys
from argparse import ArgumentParser, Namespace
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Union, Dict, Sequence, Any, Optional, List, Tuple

from pydantic import BaseModel, Field

from config.commandline_args import setup_argument_parser
from config.utils import update_dict
from log.logger import Logger
from log.utils import dump_dict_as_table
from utils.url import is_url


class Output(BaseModel):
    logdir: Optional[Path] = Field()
    localstorage: Optional[Path] = Field()
    workspace: Optional[Path] = Field()


class Artifactory(BaseModel):
    uri: Optional[str] = Field()
    user: Optional[str] = Field()
    password: Optional[str] = Field()


class Idc(BaseModel):
    ip: Optional[str] = Field()
    port: int = Field(default=22)


class Source(BaseModel):
    error: bool = Field(default=False)
    url: Optional[Union[str, Path]] = Field(description="Local path or url of tar file")


class Module(BaseModel):
    id: str = Field(description="The lowercase flashing module name, e.g. adaptive")
    update: bool = Field(default=False, description="Whether to update idc via flashing")
    sources: Dict[str, Source] = Field(default={"source": Source()})

    def has_errors(self) -> bool:
        return any([source.error for _, source in self.sources.items()])

    def has_sources(self) -> bool:
        return any([source.url if key == "source" else None for key, source in self.sources.items()])

    def has_downloads(self) -> bool:
        return any([str(source.url).startswith("http") for _, source in self.sources.items()])

    def table(self) -> Dict[str, str]:
        return {source_id: source.url for source_id, source in self.sources.items() if
                source_id != "delete_persistency"}


class ModuleAdaptive(Module):
    clear_persistency: bool = Field(default=False)


class ModuleDDU(Module):
    clear_persistency: bool = Field(default=False)
    aurix_port: Optional[str] = Field()


class AvailableModules(Enum):
    ADAPTIVE = "adaptive"
    NDAS = "ndas"
    RRDATA = "rrdata"
    DDU = "ddu"
    BUNDLE = "bundle"

    @classmethod
    def values(cls) -> List[str]:
        return list(map(lambda c: str(c.value), cls))

    def __str__(self):
        return str(self.value)


class ModuleConfig(BaseModel):
    adaptive: ModuleAdaptive = Field(default=ModuleAdaptive(id="adaptive"))
    ndas: Module = Field(default=Module(id="ndas"))
    rrdata: Module = Field(default=Module(id="rrdata"))
    ddu: ModuleDDU = Field(default=ModuleDDU(id="ddu"))
    bundle: Module = Field(default=Module(id="bundle"))

    def __getitem__(self, item) -> Module:
        return self.__dict__[item]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def items(self) -> List[Tuple[str, Module]]:
        return [
            ("adaptive", self.adaptive),
            ("ndas", self.ndas),
            ("rrdata", self.rrdata),
            ("ddu", self.ddu),
            ("bundle", self.bundle)
        ]


class StoreModuleSources(argparse.Action):
    def __call__(self, parser: ArgumentParser, namespace: Namespace, values: str | Sequence[Any] | None,
                 option_string: str | None = ...) -> None:
        module_id, source_id = option_string.lstrip("-").split('-')
        module_dict = namespace.modules.get(module_id, Module(id=module_id).dict())
        module = Module(**module_dict)

        if self.nargs and self.nargs in ["+", "*"]:
            values = ' '.join(values)

        lexer = shlex.shlex(values, posix=True)
        lexer.whitespace_split = True
        lexer.whitespace = ","

        sources = module.sources
        for word in lexer:
            key_and_value = word.split("=", maxsplit=1)
            if len(key_and_value) == 1:
                key_and_value = [source_id, *key_and_value]
            key, value = key_and_value
            sources[key] = Source(url=value)

        namespace.modules[module_id] = module.dict()


class FlashConfig(BaseModel):
    config: Optional[Path] = Field(description="JSON config file")
    debug: Optional[bool] = Field(description="debug mode without modifying flashed software")
    download: Optional[bool] = Field(description="download only")
    interactive: Optional[bool] = Field(description="mode that guides the user step by step")
    verbose: Optional[bool] = Field(description="increase output verbosity")
    output: Optional[Output] = Field(default=Output())
    artifactory: Optional[Artifactory] = Field(default=Artifactory())
    idc: Optional[Idc] = Field(default=Idc())
    modules: ModuleConfig = Field(default=ModuleConfig())

    def has_updates(self) -> bool:
        return any([module.update for _, module in self.modules.items()])

    def has_source_for_module(self, module_id: str) -> bool:
        module = self.modules[module_id]

        return module is not None and module.has_sources()

    def has_sources(self) -> bool:
        return any([module.has_sources() for _, module in self.modules.items()])

    def has_downloads(self) -> bool:
        return any([module.has_downloads() for _, module in self.modules.items()])

    def set_update(self, module_id: str, update: bool):
        module = self.modules[module_id]
        module.update = update
        self.modules[module_id] = module

    def has_errors(self) -> bool:
        return any([module.has_errors() for _, module in self.modules.items()])

    def get_modules_to_configure(self) -> List[Module]:
        return [module for _, module in self.modules.items() if module.update or module.has_errors()]

    def get_modules_with_sources(self) -> List[Module]:
        return [module for _, module in self.modules.items() if module.has_sources()]

    @staticmethod
    def from_default() -> FlashConfig:
        return FlashConfig.construct(
            debug=False,
            download=False,
            interactive=True,
            verbose=False,
            output=Output(logdir="", localstorage="", workspace=""),
            artifactory=Artifactory(uri="", user="", password=""),
            idc=Idc(ip=""),
        )

    @staticmethod
    def from_args(namespace: Namespace) -> FlashConfig:
        """ Merges cli arguments with flash config defaults"""
        default = FlashConfig.from_default()

        # Forcefully disable interactive mode, if non_interactive is set
        interactive = not namespace.non_interactive and namespace.interactive

        output = Output(
            logdir=namespace.output_logdir,
            localstorage=namespace.output_localstorage,
            workspace=namespace.output_workspace,
        )

        artifactory = Artifactory(
            uri=namespace.artifactory_uri,
            user=namespace.artifactory_user,
            password=namespace.artifactory_password,
        )

        idc = Idc(
            ip=namespace.idc_ip,
            port=namespace.idc_port,
        )

        modules: ModuleConfig = default.modules
        for key, value in namespace.__dict__.items():
            if key == "clear_adaptive_persistency":
                module: ModuleAdaptive = modules.adaptive
                module.clear_persistency = True if value else False
            if key == "clear_ddu_persistency":
                module: ModuleDDU = modules.ddu
                module.clear_persistency = True if value else False
            if key == "ddu_aurix_port" and value:
                module: ModuleDDU = modules.ddu
                module.aurix_port = value
                continue
            if value is None:
                continue
            if key.split("_")[0] in AvailableModules.values():
                module_id = key.split("_")[0]
                source_id = "_".join(key.split("_")[1:])

                module: Module = modules[module_id]

                module.update = namespace.__dict__.get(f"update_{module_id}", False)

                source = module.sources.get(source_id, Source())
                source.url = value if is_url(value) else Path(value)
                module.sources[source_id] = source

                modules[module_id] = module

        return FlashConfig.construct(
            config=namespace.config,
            debug=namespace.debug,
            download=namespace.download,
            interactive=interactive,
            verbose=namespace.verbose,
            output=output,
            artifactory=artifactory,
            idc=idc,
            modules=modules
        )

    @staticmethod
    def from_config(cli_args: FlashConfig, logger: Logger) -> Optional[FlashConfig]:
        """Updates command line arguments with parameters provided in config file.

        1. Command line arguments

        2. Reading parameters from *.json file -> overwrite cli arguments.

        Args:
            cli_args (FlashConfig): Holds the result from a argparse
            logger (Logger):

        Returns:
            FlashConfig: consolidated config
        """

        logger.debug(f"Received following cli arguments:\n{dump_dict_as_table(cli_args.dict())}")

        if not cli_args.config:
            return cli_args

        if not cli_args.config.exists() or not cli_args.config.is_file():
            logger.error(f"Config file {cli_args.config} not found")
            return None

        with open(cli_args.config, "r") as json_file:
            try:
                json_config = FlashConfig.parse_raw(json_file.read())
            except Exception as e:
                logger.error(f"Failed to load config file {cli_args.config}.\n{str(e)}")
                return None
            logger.debug(f"Received following json configuration:\n{dump_dict_as_table(json_config.dict())}")
            try:
                consolidated_config_dict = update_dict(cli_args.dict(), json_config.dict())
            except Exception as e:
                logger.error(f"Failed to match cli arguments and parameters from {cli_args.config}.\n{str(e)}")
                return None

        logger.debug(f"Configuration:\n{dump_dict_as_table(consolidated_config_dict)}")
        return FlashConfig(**consolidated_config_dict)


if __name__ == "__main__":
    """Updates default flashConfig.json and flashConfig.schema.json"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", "-o",
                        type=PathLike,
                        required=False,
                        default=Path(__file__).parent.parent.parent.absolute())

    args = parser.parse_args(sys.argv[1:])

    with open(args.outdir / "flashConfig.json", "w") as file:
        parser = setup_argument_parser("example-session-id")
        flash_config = FlashConfig.from_args(parser.parse_args(["--idc-ip", "192.168.5.10"]))
        flash_config.interactive = False
        file.write(flash_config.json(by_alias=True, indent=4))

    with open(args.outdir / "flashConfig.schema.json", "w") as file:
        file.write(FlashConfig().schema_json(indent=4))
