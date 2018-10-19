#!/usr/bin/env python3

import errno
import subprocess

import docker

def check_command_available(command: str) -> bool:
    try:
        subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False

        raise

    return True

def check_docker_command_available() -> bool:
    return check_command_available("docker")

def check_docker_compose_command_available() -> bool:
    return check_command_available("docker-compose")
    
def check_docker_running() -> bool:
    command = ["docker", "version"]
    process_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return process_result.returncode == 0

