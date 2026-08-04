import pathlib


def dir_empty(path: pathlib.Path):
    assert isinstance(path, pathlib.Path) and path.is_dir()
    has_next = next(path.iterdir(), None)
    if has_next is None:
        return True
    return False


def remove_suffixes(filename: str) -> str:
    filename_path = pathlib.Path(filename)
    clean_filename = pathlib.Path(filename.rstrip("".join(filename_path.suffixes)))
    return pathlib.Path(clean_filename).name
