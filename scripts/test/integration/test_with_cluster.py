#!/usr/bin/env python3

from pathlib import Path
from typing import Iterable, List

import unittest

import docker

import oozie_testing.inside_container.example_runner
import oozie_testing.inside_container.report
import test_env



class TestWithCluster(unittest.TestCase):
    reports_dir = Path("testing/reports")
    timeout = 180
    build_config_dir = Path("docker_compose_resources")
    oozieserver: docker.models.containers.Container = None

    @classmethod
    def setUpClass(cls) -> None:
        import within_cluster_testing

        test_env.docker_compose_up(TestWithCluster.build_config_dir)

        # Assert that Hadoop and Oozie are running.
        TestWithCluster._check_cluster_running()

        TestWithCluster.oozieserver = test_env.get_oozieserver()
        inside_container = Path(oozie_testing.inside_container.__file__).parent.expanduser().resolve()
        test_env.setup_testing_env_in_container(TestWithCluster.oozieserver, inside_container)

        # Assert examples are extracted and uploaded
        TestWithCluster._check_examples_extracted()
        TestWithCluster._check_examples_uploaded_to_hdfs()

        # Copy the testing file to the containerx
        test_env.docker_cp_to_container(TestWithCluster.oozieserver.name,
                                        str(Path(within_cluster_testing.__file__).expanduser().resolve()),
                                        "/opt/oozie/inside_container")

    @classmethod
    def tearDownClass(cls) -> None:
        test_env.docker_compose_down(TestWithCluster.build_config_dir)

    def test_launching_normal_example_ok(self) -> None:
        example_name = "java-main"
        cmd = "python3 /opt/oozie/inside_container/within_cluster_testing.py --run-normal {}".format(example_name)

        (return_code, output) = TestWithCluster.oozieserver.exec_run(cmd, workdir="/opt/oozie")

        self.assertEqual(0, return_code)

    def test_launching_normal_example_wrong_name(self) -> None:
        example_name = "java-main-wrong-name"
        cmd = "python3 /opt/oozie/inside_container/within_cluster_testing.py --run-normal {}".format(example_name)

        (return_code, output) = TestWithCluster.oozieserver.exec_run(cmd, workdir="/opt/oozie")
        self.assertNotEqual(0, return_code)

    def test_building_fluent_example_ok(self) -> None:
        example_class_name = "JavaMain"
        build_dir = "build_dir"
        cmd = "python3 /opt/oozie/inside_container/within_cluster_testing.py --build-fluent {} {}".format(
            example_class_name,
            build_dir)

        (return_code, output) = TestWithCluster.oozieserver.exec_run(cmd, workdir="/opt/oozie")
        self.assertEqual(0, return_code)

        # Check if the example was really built on the filesystem.
        (return_code_ls, output_ls) = TestWithCluster.oozieserver.exec_run("ls {}".format(build_dir), workdir="/opt/oozie")
        self.assertEqual(0, return_code_ls)

        build_dir_contents = output_ls.decode().split()
        self.assertTrue("org" in build_dir_contents)
        self.assertTrue(any(map(lambda name: name.endswith(".jar"), build_dir_contents)))

    def test_building_fluent_example_wrong_name(self) -> None:
        example_class_name = "JavaMain_Wrong_Name"
        build_dir = "build_dir"
        cmd = "python3 /opt/oozie/inside_container/within_cluster_testing.py --build-fluent {} {}".format(
            example_class_name,
            build_dir)

        (return_code, output) = TestWithCluster.oozieserver.exec_run(cmd, workdir="/opt/oozie")
        self.assertNotEqual(0, return_code)

    def test_launching_fluent_example_ok(self) -> None:
        # TODO: Fix this test.
        example_class_name = "JavaMain"
        cmd = "python3 /opt/oozie/inside_container/within_cluster_testing.py --run-fluent {}".format(example_class_name)

        (return_code, output) = TestWithCluster.oozieserver.exec_run(cmd, workdir="/opt/oozie")
        self.assertEqual(0, return_code)

    @staticmethod
    def _check_cluster_running() -> None:
        docker_client = docker.from_env()

        containers: Iterable[docker.models.containers.Container] = docker_client.containers.list()
        container_names: List[str] = list(map(lambda container: container.name, containers))

        service_names = ["oozieserver", "historyserver", "namenode", "resourcemanager", "nodemanager", "datanode"]

        among_services = lambda service_name: any(map(lambda container_name: service_name in container_name, container_names))

        not_running = list(filter(lambda service_name: not among_services(service_name), service_names))
        if not_running:
            raise ValueError("The following docker services are running: {}.".format(not_running))

    @staticmethod
    def _check_examples_extracted() -> None:
        (return_code, _) = TestWithCluster.oozieserver.exec_run("ls examples")

        if return_code != 0:
            raise ValueError("The Oozie examples are not extracted.")

        
    @staticmethod
    def _check_examples_uploaded_to_hdfs() -> None:
        (return_code, _) = TestWithCluster.oozieserver.exec_run("hdfs dfs -ls examples")

        if return_code != 0:
            raise ValueError("The Oozie examples are not uploaded to HDFS.")

        
