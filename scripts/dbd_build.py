#!/usr/bin/env python3

"""
This module provides functionality that builds dbd `BuildConfiguration`s.
"""

from pathlib import Path

import logging
import subprocess

def build_configs_with_dbd(configurations: Path,
                           output_dir: Path,
                           dbd_path: Path,
                           cache: Path) -> None:
    """
    Builds the dbd `BuildConfiguration`s found in the `configurations` directory.

    Args:
        configurations: The path to the directory in which `BuildConfiguration` files are located.
        output_dir: The path to the directory in which the resulting docker-compose
            directories will be generated. This directory must already exist.
        dbd_path: The path to the dbd.py file that will be called to build the `BuildConfiguration`s.
        cache: The path to the directory that will be used as the dbd cache.
            This directory does not have to already exist.
    """

    logging.info("Building the configurations with dbd.")
    for configuration in configurations.expanduser().resolve().iterdir():
        if not configuration.is_dir():
            logging.info("Building configuration with filename %s.", str(configuration))
            command = [str(dbd_path), str(configuration), str(output_dir), "-c", str(cache)]
            subprocess.run(command, check=True)
