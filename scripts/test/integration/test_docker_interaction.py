#!/usr/bin/env python3

import errno
import logging

from pathlib import Path

import subprocess
import sys
import tempfile
import time

from typing import List

import unittest

import docker

# We add the project root to the path to be able to access the project modules.
sys.path.append(str(Path("../..").resolve()))

import docker_setup

import test_env

IMAGE = "frolvlad/alpine-oraclejdk8"

def _write_to_file(file_path: Path, text: str) -> None:
    with file_path.open("w") as file:
        file.write(text)

class TestDockerCopying(unittest.TestCase):
    def setUp(self) -> None:
        self.container = docker.from_env().containers.run(IMAGE, detach=True, auto_remove=True, tty=True);

    def tearDown(self) -> None:
        self.container.remove(force=True)
        
    def test_docker_copy_to_container_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name).expanduser().resolve()
            file1 = tempdir / "file1.txt"
            file2 = tempdir / "file2.txt"

            _write_to_file(file1, "File 1.")
            _write_to_file(file2, "File 2.")

            dir_in_container = "temp_dir"
            test_env.docker_cp_to_container(self.container.name, tempdir_name, dir_in_container)

            output = list(sorted(self.container.exec_run("ls {}".format(dir_in_container))
                                            .output.decode().strip().split("\n")))
            expected = list(sorted([file1.name, file2.name]))
            self.assertEqual(expected, output)

    def test_docker_copy_to_container_fails_nonexistent_source(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name).expanduser().resolve()

            with self.assertRaises(test_env.DockerSubprocessException):
                nonexistent_directory = tempdir / "nonexistent_directory"
                self.assertFalse(nonexistent_directory.exists())
                test_env.docker_cp_to_container(self.container.name, str(nonexistent_directory), "")

    def test_docker_copy_to_container_fails_nonexistent_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name).expanduser().resolve()

            with self.assertRaises(test_env.DockerSubprocessException):
                dummy_file = tempdir / "file.txt"
                dummy_file.touch()
                self.assertTrue(dummy_file.exists())

                nonexistent_destination = "nonexistent_destination_within_the_container/some_file.txt"
                test_env.docker_cp_to_container(self.container.name, str(dummy_file), nonexistent_destination)

    def test_docker_copy_from_container_ok(self) -> None:
        command_in_container = "mkdir temp_dir && touch temp_dir/file1.txt && touch temp_dir/file2.txt"
        file_creation_result = self.container.exec_run('sh -c "{}"'.format(command_in_container))        
        self.assertEqual(0, file_creation_result.exit_code)
 
        with tempfile.TemporaryDirectory() as local_tempdir_name:
            test_env.docker_cp_from_container(self.container.name, "temp_dir", local_tempdir_name)

            local_tempdir = Path(local_tempdir_name).expanduser().resolve()
            self.assertTrue((local_tempdir / "temp_dir").exists())
            self.assertTrue((local_tempdir / "temp_dir" / "file1.txt").exists())
            self.assertTrue((local_tempdir / "temp_dir" / "file2.txt").exists())

    def test_docker_copy_from_container_fails_nonexistent_source(self) -> None:
        with self.assertRaises(test_env.DockerSubprocessException):
            nonexistent_source = "nonexistent_destination_within_the_container/some_file.txt"
            test_env.docker_cp_from_container(self.container.name, nonexistent_source, ".")

    def test_docker_copy_from_container_fails_nonexistent_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name).expanduser().resolve()

            nonexistent_destination = tempdir / "nonexistent_directory/dummy_file.txt"
            self.assertFalse(nonexistent_destination.exists())

            self.container.exec_run('sh -c "touch dummy_file.txt"')
            

            with self.assertRaises(test_env.DockerSubprocessException):
                test_env.docker_cp_from_container(self.container.name, "dummy_file.txt", nonexistent_destination)

class TestDockerFindingContainers(unittest.TestCase):
    def test_find_oozie_and_nodemanager(self) -> None:
        try:
            oozieserver = docker.from_env().containers.run(IMAGE, detach=True, auto_remove=True,
                                                           tty=True, name="oozieserver");
            nodemanager = docker.from_env().containers.run(IMAGE, detach=True, auto_remove=True,
                                                           tty=True, name="nodemanager");

            found_oozieserver = test_env.get_oozieserver()
            found_nodemanager = test_env.get_nodemanager()

            self.assertEqual(oozieserver, found_oozieserver)
            self.assertEqual(nodemanager, found_nodemanager)
        finally:
            oozieserver.remove(force=True)
            nodemanager.remove(force=True)

class TestDockerCompose(unittest.TestCase):
    docker_compose_text = """
version: '3'
services:
  first_service:
    command: [sh]
    image: {0}
  second_service:
    command: [sh]
    image: {0}""".format(IMAGE)

    def test_docker_compose_up_and_down_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name).expanduser().resolve()
            first_service_name = tempdir.name + "_first_service_1"
            second_service_name = tempdir.name + "_second_service_1"

            try:
                docker_compose_file = tempdir / "docker-compose.yaml"
                _write_to_file(docker_compose_file, TestDockerCompose.docker_compose_text)

                test_env.docker_compose_up(tempdir)

                container_names = list(map(lambda container: container.name, docker.from_env().containers.list()))
                
                self.assertTrue(first_service_name in container_names)
                self.assertTrue(second_service_name in container_names)
            finally:
                test_env.docker_compose_down(tempdir)
                new_container_names = list(map(lambda container: container.name, docker.from_env().containers.list()))
                self.assertFalse(first_service_name in new_container_names)
                self.assertFalse(second_service_name in new_container_names)

    def test_docker_compose_up_fails_no_compose_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name).expanduser().resolve()

            with self.assertRaises(test_env.DockerSubprocessException):
                test_env.docker_compose_up(tempdir)

    def test_docker_compose_down_fails_no_compose_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            tempdir = Path(tempdir_name).expanduser().resolve()

            with self.assertRaises(test_env.DockerSubprocessException):
                test_env.docker_compose_down(tempdir) 

                
