#!/usr/bin/env python3

import getpass
import urllib.parse
import urllib.request
from os import PathLike
from typing import Union, Tuple

from system.host_pc import HostPC

HTTP_ERROR_UNAUTHORIZED = 401
HTTP_ERROR_FILE_NOT_FOUND = 404

DEFAULT_ARTIFACTORY_URL = "https://artifact.swf.i.mercedes-benz.com/"

PASSWORD_MANAGER = urllib.request.HTTPPasswordMgrWithDefaultRealm()

# TODO: (vibenzi) create class that can only instanciate single password manager


def is_url(url: Union[str, PathLike]) -> bool:
    return url and (str(url).startswith("http"))


def adapt_url_domain(url: str):
    if HostPC.is_ds_pc():
        url = url.replace(
            "https://artifact.swf.i.mercedes-benz.com/artifactory",
            "http://artifacts.prod.carpc.adas.corpinter.net",
        )
    return url


def authenticate(user: str, password: str, uri: str = DEFAULT_ARTIFACTORY_URL):
    parsed_uri = urllib.parse.urlparse(uri)
    reduced_uri = parsed_uri[0] + "://" + parsed_uri[1] + "/"
    PASSWORD_MANAGER.add_password(None, reduced_uri, user, password)
    auth_handler = urllib.request.HTTPBasicAuthHandler(PASSWORD_MANAGER)
    opener = urllib.request.build_opener(auth_handler)
    urllib.request.install_opener(opener)


def url_requires_authentication(url: str) -> bool:
    try:
        urllib.request.urlopen(url).getcode()
    except urllib.error.HTTPError as e:
        if e.code == HTTP_ERROR_UNAUTHORIZED:
            return True
        raise e
    return False


def get_authentication_from_user() -> Tuple[str, str]:
    user = "SSIKKAN"
    password = "cmVmdGtuOjAxOjE4MDQzMTU2MDQ6a2hCZzVqU0hSN1pLb0JnZHppYVc3a3JVc1Qw"
    return user, password


def get_url_content_length(url: str) -> int:
    return int(urllib.request.urlopen(url).info()["Content-Length"])
