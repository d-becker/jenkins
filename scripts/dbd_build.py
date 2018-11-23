#!/usr/bin/env python3

"""
This module provides functionality that builds dbd `BuildConfiguration`s.
"""

from typing import List, Optional

from pathlib import Path

import logging
import subprocess

def build_configs_with_dbd(configurations_dir: Path,
                           configuration_files: Optional[List[str]],
                           output_dir: Path,
                           dbd_path: Path,
                           cache: Path) -> None:
    """
    Builds the dbd `BuildConfiguration`s found in the `configurations` directory.

    Args:
        configurations_dir: The path to the directory in which `BuildConfiguration` files are located.
        configuration_files: A list of filenames in the `configurations_dir` directory.
            If provided, only the given `BuildConfiguration` files will be built.
        output_dir: The path to the directory in which the resulting docker-compose
            directories will be generated. This directory must already exist.
        dbd_path: The path to the dbd.py file that will be called to build the `BuildConfiguration`s.
        cache: The path to the directory that will be used as the dbd cache.
            This directory does not have to already exist.
    """

    logging.info("Building the configurations with dbd.")
    files_in_configurations_dir = configurations_dir.expanduser().resolve().iterdir()
    filter_function = lambda file_path: _filter_paths(file_path, configuration_files)
    build_config_files = filter(filter_function, files_in_configurations_dir)

    for configuration in build_config_files:
        logging.info("Building configuration with filename %s.", str(configuration))
        command = ["python3", str(dbd_path), str(configuration), str(output_dir), "-c", str(cache)]
        subprocess.run(command, check=True)

def _filter_paths(file_path: Path, configuration_files: Optional[List[str]]) -> bool:
    if file_path.is_dir():
        return False

    if configuration_files is not None:
        return file_path.name in configuration_files

    return True
