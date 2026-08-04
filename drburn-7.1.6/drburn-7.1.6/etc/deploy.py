#!/usr/bin/env python3

"""Script to create drburn_*.*.*.tar.xz which can be deployed through saltstack and complies with the archive structure required from 
   https://git.i.mercedes-benz.com/adas-carpc/saltstack-carpc-minerva-aws/blob/quidco-test/saltstates/sit/quidco/init.sls
"""

import argparse
import pathlib
import sys
import tarfile


def main(args):
    parent_dir = args.output_file.parents[0]
    assert pathlib.Path.exists(args.output_file.parents[0]), f"No such directory {parent_dir}"

    assert not pathlib.Path.exists(args.output_file), f"File {args.output_file} already exists."

    drburn_path = pathlib.Path(__file__).absolute()
    print(f"current Path: {drburn_path}")
    while drburn_path.name != "drburn":
        drburn_path = drburn_path.parent

    print(f"Saving contents of {drburn_path} to {args.output_file}")

    with tarfile.open(args.output_file, mode="w:xz") as tar_file:
        tar_file.add(
            drburn_path,
            recursive=True,
            arcname="app",
            filter=(
                lambda tarinfo: None
                if (pathlib.Path(tarinfo.name).name.startswith(".git") or pathlib.Path(tarinfo.name).name.startswith("__pycache__")) or pathlib.Path(tarinfo.name).name.startswith("pyproject.toml") or pathlib.Path(tarinfo.name).name.startswith("test")
                else tarinfo
            ),
        )
    tar_file.close()

    print(f"Tar file created successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        "-o",
        "--output-file",
        help="/path/to/output/file/drburn_*.*.*.tar.xz",
        required=True,
        type=pathlib.Path,
    )

    args = parser.parse_args()

    sys.exit(main(args))
