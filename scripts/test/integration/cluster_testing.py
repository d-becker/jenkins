#!/usr/bin/env python3

import unittest

import test_env

class TestWithCluster(unittest.TestCase):
    reports_dir = Path("testing/reports")
    timeout = args.timeout if args.timeout is not None else 180
    build_config_dir = Path("docker_compose_resources")

    @classmethod
    def setUpClass(cls) -> None:
        test_env.docker_compose_up(TestWithCluster.build_config_dir)

        # TODO: Assert that Hadoop and Oozie are running.

        oozieserver = test_env.get_oozieserver()
        test_env.setup_testing_env_in_container(oozieserver)

        # TODO: Assert examples are extracted and uploaded

    @classmethod
    def tearDownClass() -> None:
        test_env.docker_compose_down(TestWithCluster.build_config_dir)

        
