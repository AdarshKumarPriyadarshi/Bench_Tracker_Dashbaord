import argparse
import json
import pathlib
from unittest.mock import patch

import pytest
import sys

from pytest_mock import MockFixture

import config.commandline_args
import drburn
import utils.url
from config.flash_config import FlashConfig
from flashing.flash_graph_creator import FlashGraphCreator

package_dir = pathlib.Path(__file__).parent.parent

sys.path.append(str(package_dir / "src"))


@pytest.fixture
def user():
    return ""


@pytest.fixture
def password():
    return ""


@pytest.fixture
def default_config_dict():
    with open(package_dir / "flashConfig.json", "r") as json_file:
        return json.load(json_file)


@pytest.fixture
def dummy_ndas_url():
    return "https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas-delivery-dev/ATGB_tests/R5-DBGBuilds/driveworks_32601482_v2_usrlocal_20230222.tar.gz"


@pytest.fixture
def dummy_ndas_url_ds_pc(dummy_ndas_url):
    return utils.url.adapt_url_domain(dummy_ndas_url)


@pytest.fixture
def dummy_ndas_file_size():
    return 4088052556


@pytest.fixture
def dummy_small_file_url():
    return "https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas-delivery-dev/ATGB_tests/CANoe_Config.txt"


@pytest.fixture
def dummy_small_file_url_ds_pc(dummy_small_file_url):
    return utils.url.adapt_url_domain(dummy_small_file_url)


@pytest.fixture
def dummy_small_file_size():
    return 193


@pytest.fixture
def dummy_invalid_url():
    return "https://artifact.swf.i.mercedes-benz.com/artifactory/adasndas-delivery-dev/ATGB_tests/INVALID_URL/CANoe_Config.txt"


@pytest.fixture
def dummy_invalid_url_ds_pc(dummy_invalid_url):
    return utils.url.adapt_url_domain(dummy_invalid_url)


@pytest.fixture
def default_cli_args_namespace() -> argparse.Namespace:
    return config.commandline_args.setup_argument_parser("DUMMY_SESSION_ID").parse_args([])


def test_read_config(default_cli_args_namespace):
    # Given
    default_cli_args_namespace.config = package_dir / "flashConfig.json"
    logger = drburn.FileAndStreamLogger(pathlib.Path("/tmp"))

    # When
    flash_config = FlashConfig.from_config(FlashConfig.from_args(default_cli_args_namespace), logger)

    # Then
    assert flash_config is not None
    assert flash_config.config == default_cli_args_namespace.config


def test_config_front_loader_url_hash_in_file_prefix(dummy_ndas_url):
    file = drburn.ConfigFrontLoader.retrieve_file_for_url(dummy_ndas_url)
    path = pathlib.Path("/tmp") / f"{file.prefix}_{file.suffix}"
    assert drburn.ConfigFrontLoader.get_url_hash(
        dummy_ndas_url
    ) == drburn.ConfigFrontLoader.retrieve_url_hash_from_path(path)


###################### Local / MTTF ######################
@patch('urllib.request.urlopen')
def test_get_url_content_length_small_file(mock_urlopen, dummy_small_file_url, dummy_small_file_size,
                                           mocker: MockFixture):
    # Given
    mock_urlinfo = mocker.MagicMock()
    mock_urlinfo.info.return_value = {"Content-Length": dummy_small_file_size}

    mock_urlopen.return_value = mock_urlinfo

    # When
    content_length = utils.url.get_url_content_length(dummy_small_file_url)

    # Then
    assert content_length == dummy_small_file_size


@patch('urllib.request.urlopen')
def test_get_url_content_length_large_file(mock_urlopen, dummy_ndas_url, dummy_ndas_file_size, mocker: MockFixture):
    # Given
    mock_urlinfo = mocker.MagicMock()
    mock_urlinfo.info.return_value = {"Content-Length": dummy_ndas_file_size}

    mock_urlopen.return_value = mock_urlinfo

    # When
    content_length = utils.url.get_url_content_length(dummy_ndas_url)

    # Then
    assert content_length == dummy_ndas_file_size


###################### Generic ######################
@patch.object(FlashGraphCreator, 'createFlashGraph')
def test_main(test_createFlashGraph, user, password, default_cli_args_namespace):
    # Given
    session_id = drburn.get_current_datetime_string_literal()
    default_cli_args_namespace.config = package_dir / "flashConfig.json"
    default_cli_args_namespace.output_workspace = pathlib.Path(f"/tmp/drburn/{session_id}")
    default_cli_args_namespace.interactive = False
    # With AUTHENTICATION - enter password to execute this part
    # if not HostPC.is_ds_pc() and (not user or not password):
    # user, password = utils.url.get_authentication_from_user()
    default_cli_args_namespace.artifactory_user = user
    default_cli_args_namespace.artifactory_password = password

    test_createFlashGraph.return_value = type('', (object,), {"run": lambda _: True, "print_summary": lambda _: ""})()

    # When
    flash_config = FlashConfig.from_args(default_cli_args_namespace)
    exit_code = drburn.main(flash_config, session_id)

    # Then
    assert exit_code != 1
