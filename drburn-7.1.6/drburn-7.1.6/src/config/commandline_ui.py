import os
import pathlib
from typing import Dict

from config.flash_config import FlashConfig, AvailableModules, Source, ModuleAdaptive, ModuleDDU
from log.format import FGColor, Style
from log.logger import Logger
from log.print_logger import PrintLogger
from log.utils import dump_dict_as_table
from utils.input import input_with_path_completion
from utils.url import is_url


class CommandlineUI:
    def __init__(self, logger: Logger = PrintLogger()):

        self.logger = logger

    def __get_user_input_option(
        self, prompt: str, options: list, options_abbreviated: list, allow_multiple: bool = False,
        return_options: bool = True
    ):
        option_prompt = ""
        if allow_multiple:
            option_prompt = (
                " Please enter one or more of the following options and use commas to separate your choices."
            )

        use_short_options = (
            bool(options_abbreviated)
            and isinstance(options_abbreviated, list)
            and (len(options_abbreviated) == len(options))
        )
        options_str = ""
        if use_short_options:
            options_str = " ".join(
                [f"\n\t({short_option}): '{option}'" for short_option, option in zip(options_abbreviated, options)]
            )
        else:
            options_str = " ".join([f"\n\t'{option}'" for short_option, option in zip(options_abbreviated, options)])

        self.logger.info(f"{prompt + option_prompt}\n{options_str}")

        valid_inputs = (options + options_abbreviated) if use_short_options else options
        user_input = input()
        if allow_multiple:
            user_input = user_input.split(",")
            user_input = [option.strip() for option in user_input]
        else:
            user_input = [user_input]

        while not all([input in valid_inputs for input in user_input]):
            self.logger.info(f"Invalid input. Valid options are\n{options_str}")
            user_input = input()
            if allow_multiple:
                user_input = user_input.split(",")
                user_input = [option.strip() for option in user_input]
            else:
                user_input = [user_input]

        self.logger.info("\n")

        if not return_options:
            if allow_multiple:
                return user_input
            else:
                return user_input[0]

        indices = [
            options.index(input) if input in options else options_abbreviated.index(input) for input in user_input
        ]
        selected_options = [options[index] for index in indices]

        if allow_multiple:
            return selected_options
        else:
            return selected_options[0]

    def __get_user_input_option_yes_no(self, prompt):
        return (
            self.__get_user_input_option(prompt=prompt, options=["yes", "no"], options_abbreviated=["y", "n"]) == "yes"
        )

    def run(self, config: FlashConfig) -> FlashConfig:
        """Encapsulates logic for user interaction update of config.

        Major use-case: If  NOTHING is given from command line -> user is asked what/how to flash.

        NOTE: In case user-interaction should be avoided in any case, e.g. in CI-/CD - pipeline
               -> bypass this functor


        NOTE: If one wants to have autocompletion in user-interaction, this is the place to put it in.

        Further: If one wants to re-use something already downloaded -> derive from this 'function'

        """

        if not config.interactive:
            self.logger.debug(f"CommandlineUI: Nothing to do")
            return config

        config_with_user_input: FlashConfig = config.copy(deep=True)

        # DOWNLOAD-ONLY
        download = config_with_user_input.download

        # ASK USER - UPDATE
        if not config.has_updates() and not config.has_sources():
            selected_modules = self.__get_user_input_option(
                prompt="\nWhat do you want to update?",
                options=AvailableModules.values(),
                options_abbreviated=[module[0] for module in AvailableModules.values()],
                allow_multiple=True,
            )
            for module_id in selected_modules:
                config_with_user_input.set_update(module_id, True)
        elif not config.has_updates() and config.has_sources():
            if download:
                pass
            elif not config_with_user_input.has_downloads() or not download:
                update_candidates = config_with_user_input.get_modules_with_sources()
                self.logger.info(
                    f"Found source(s) for {', '.join([module.id.upper() for module in update_candidates])}, but no module was selected for update."
                )
                update_yes = self.__get_user_input_option_yes_no(prompt="\nDo you want to update the modules?")
                if update_yes:
                    for update_candidate in update_candidates:
                        update_candidate.update = True
            else:
                self.logger.info(
                    f"Found source(s) for {', '.join([module.id.upper() for module in config_with_user_input.get_modules_with_sources()])}, but no module was selected for update. URLs will be downloaded and made available for later use in {config_with_user_input.output.localstorage}."
                )
                config_with_user_input.download = True

            if not config_with_user_input.has_errors():
                return config_with_user_input

        # LOCAL STORAGE
        files_in_local_storage = [
            path
            for path in sorted(config_with_user_input.output.localstorage.iterdir(), key=os.path.getmtime)
            if path.is_file()
        ]

        # ASK USER - SOURCES
        prompt = (
            "Please enter a local path or artifactory URL."
            if not config_with_user_input.has_errors()
            else "Please enter an alternative local path or artifactory URL."
        )
        if files_in_local_storage:
            prompt += f" Enter {config_with_user_input.output.localstorage}/ and press 'tab' twice to search in previously downloaded files."

        modules_to_configure = config_with_user_input.get_modules_to_configure()
        for module in modules_to_configure:
            self.logger.info(f"{module.id.upper()} configuration\n{dump_dict_as_table(module.table())}")

            if isinstance(module, ModuleAdaptive):
                module = self.ask_user_for_adaptive(prompt, module)
                self.logger.info(
                    f"Updated {module.id.upper()} configuration\n{dump_dict_as_table(module.table())}"
                )
                continue

            if isinstance(module, ModuleDDU):
                module = self.ask_user_for_ddu(prompt, module)
                self.logger.info(
                    f"Updated {module.id.upper()} configuration\n{dump_dict_as_table(module.table())}"
                )
                continue

            for _, source in module.sources.items():
                source.url = self.ask_user_for_source(prompt, source)
                self.logger.info(
                    f"Updated {module.id.upper()} configuration\n{dump_dict_as_table(module.table())}"
                )

        return config_with_user_input

    def ask_user_for_ddu(self, prompt: str, module: ModuleDDU) -> ModuleDDU:
        sources = module.sources

        # Ask for source *.tar.gz
        source = sources.get("source", Source())
        source.url = self.ask_user_for_source(prompt, source)
        sources["source"] = source

        # Ask to clear persistency
        warning = (f"{FGColor.YELLOW}{Style.ITALIC}"
                   f"WARNING: Will erase persistency (QSPI and EMMC)!\n"
                   f"Passes options -c to flash_ddu.sh script.\n"
                   f"{FGColor.RESET}")
        module.clear_persistency = self.__get_user_input_option_yes_no(
            f"\n{warning}\n\nDo you want to erase persistency also?")

        # Ask for custom flash script
        custom_flash_script = self.__get_user_input_option_yes_no(
            "Do you want to replace the default flash_ddu.sh script [local path or artifactory URL]?\n\n"
            f"{Style.ITALIC}(otherwise the default flash script will be used){FGColor.RESET}"
        )
        if custom_flash_script:
            source = sources.get("script", Source())
            source.url = None  # reset any given flash script
            source.url = self.ask_user_for_source(prompt, sources["script"])
            sources["script"] = source

        return module

    def ask_user_for_adaptive(self, prompt: str, module: ModuleAdaptive) -> ModuleAdaptive:
        sources = module.sources

        DIRECTORY_MODE = "1"
        INDIVIDUAL_MODE = "2"
        LEGACY_MODE = "3"

        mode = self.__get_user_input_option(
            prompt="Do you want to flash from a directory containing the partitions tar files [R7]?",
            options=[
                "Directory containing the partitions tar files [R7]",
                "Individual partitions tar files [R7]",
                "Legacy tar file containing the partitions tar files [R6]",
            ],
            options_abbreviated=[DIRECTORY_MODE, INDIVIDUAL_MODE, LEGACY_MODE],
            return_options=False
        )

        if mode == LEGACY_MODE:
            self.logger.info("Provide the legacy tar file [R6] containing the partitions tar files.")

            module.sources = {"source": Source(url=self.ask_user_for_source(prompt, sources["source"]))}
            return module

        # Ask to force flash legacy persistency
        warning = (f"{FGColor.RED}{Style.ITALIC}"
                   f"WARNING: Only for trouble shooting in case of having issues with SecOC.\n"
                   f"In case you erase the persistency, you have to performe re-code afterwards."
                   f"{FGColor.RESET}")
        module.clear_persistency = self.__get_user_input_option_yes_no(
            f"\n{warning}\n\nDo you want to erase persistency at '/var/lib/adaptive' also?")
        # Ask to flash stub libs
        flash_stub_libs = self.__get_user_input_option_yes_no(
            "\nDo you want to flash adaptive stub_libs_partition_tar also?")

        if mode == DIRECTORY_MODE:
            self.logger.info("Provide the directory [R7] containing the partitions tar files")
            directory = self.ask_user_for_source(prompt, sources["source"], accept_file=False, accept_dir=True)
            directory_sources = {
                "adaptive": Source(url=f"{directory.rstrip('/')}/adaptive_partition_tar.tar"),
                "persistency": Source(url=f"{directory.rstrip('/')}/persistency_partition_tar.tar"),
                "stub_libs": Source(url=f"{directory.rstrip('/')}/stub_libs_partition_tar.tar"),
            }
            if not flash_stub_libs:
                directory_sources.pop("stub_libs")

            module.sources = directory_sources
            return module

        if mode == INDIVIDUAL_MODE:
            individual_sources: Dict[str, Source] = {}
            partitions = ["adaptive", "persistency", "stub_libs"]

            if not flash_stub_libs:
                partitions.remove("stub_libs")

            for partition in partitions:
                self.logger.info(f"Provide {partition}_partition_tar tar files")
                source = sources.get(partition, Source())
                source.url = self.ask_user_for_source(prompt, source)
                individual_sources[partition] = source

            module.sources = individual_sources
            return module

        raise RuntimeError(f"Adaptive flash mode {mode} is not supported!")

    def ask_user_for_source(self, prompt: str, source: Source, accept_file: bool = True, accept_dir: bool = False,
                            accept_url: bool = True) -> str:
        local_path_or_url = source.url

        if not local_path_or_url or source.error:
            self.logger.info(prompt)
            local_path_or_url = input_with_path_completion()

        # Ask until url is either a local file or an url
        while \
            not (accept_url and is_url(local_path_or_url)) \
                and not (accept_file and pathlib.Path(local_path_or_url).is_file()) \
                and not (accept_dir and pathlib.Path(local_path_or_url).is_dir()):
            if not is_url(local_path_or_url):
                self.logger.error(f"No such file {local_path_or_url}.")
            else:
                self.logger.error(f"{local_path_or_url} is neither a file nor an url.")
            self.logger.info(prompt)
            local_path_or_url = input_with_path_completion()

        source.error = False
        return local_path_or_url
