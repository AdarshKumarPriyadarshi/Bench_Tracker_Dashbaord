#!/usr/bin/env python3

import glob
import pathlib
import readline


def complete(text: str, state):
    if text.startswith("/"):
        if pathlib.Path(text).is_dir() and not text.endswith("/"):
            text += "/"
        return (glob.glob(text + "*") + [None])[state]
    else:
        return None


def input_with_path_completion(message: str = ""):
    readline.redisplay()
    readline.set_completer_delims(" \t\n;")
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
    return input(message)
