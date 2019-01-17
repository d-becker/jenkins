#!/usr/bin/env python3

"""
This script is used to find and remove the docker images generated by the Jenkins job.
"""

import logging

from pathlib import Path

import sys
import traceback

from typing import Iterable

import yaml

import test_env

def images_to_remove(build_output_dir: Path) -> Iterable[str]:
    """
    Returns an iterable with the names of the docker images that were generated by the Jenkins job.

    Args:
        build_output_dir: The directory in which the `dbd` output directories were generated.

    Returns:
        An iterable with the names of the docker images that were generated by the Jenkins job.
    """

    build_config_dirs = build_output_dir.expanduser().resolve().iterdir()

    for build_config_dir in build_config_dirs:
        filename = "output_configuration.yaml"
        output_config_file = build_config_dir / filename

        if not output_config_file.is_file():
            logging.warning("No %s file found in directory %s, cannot remove docker images.",
                            filename,
                            str(build_config_dir))
        else:
            try:
                text: str
                with output_config_file.open() as output_file:
                    text = output_file.read()

                yaml_dict = yaml.load(text)

                components_in_order = yaml_dict["component-order"]
                for component_name in reversed(components_in_order):
                    component_dict = yaml_dict["components"][component_name]
                    if not component_dict["reused"]:
                        image_name = component_dict["image_name"]
                        yield image_name
            # pylint: disable=broad-except
            except Exception as exception:
            # pylint: enable=broad-except
                exception_msg = traceback.format_exception_only(type(exception), exception)[0].strip()
                logging.warning("The following exception occured while checking the yaml file \"%s\" looking "
                                "for images to be removed: \"%s\". Couldn't remove images of that BuildConfiguration.",
                                str(output_config_file),
                                exception_msg)


def main() -> None:
    """
    The entry point of the script.
    """

    build_output_dir = Path(sys.argv[1])

    for image_name in images_to_remove(build_output_dir.expanduser().resolve()):
        test_env.docker_remove_image(image_name)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
