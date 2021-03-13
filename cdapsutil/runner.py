# -*- coding: utf-8 -*-

import subprocess
import logging
import json
import time


LOGGER = logging.getLogger(__name__)


def _cur_time_in_seconds():
    return int(round(time.time()))


def _run_functional_enrichment_docker(docker_dict):
    """
    Function that runs docker dumping results to
    file path specified by docker_dict['outfile']

    {'index': counter,
     'node_id': node_id,
     'outfile': <output file, must be in temp_dir>,
     'image': <docker_image>,
     'arguments': <list of arguments>,
     'temp_dir': <temp directory where input data resides and output will be written>,
     'docker_runner': <instance of DockerRunner class>}

    :param docker_dict: {'outfile': <PATH WHERE OUTPUT RESULT SHOULD BE WRITTEN>}
    :type docker_dict: dict
    :return: None

    """
    start_time = _cur_time_in_seconds()
    drunner = docker_dict['docker_runner']
    e_code, out, err = drunner.run_docker(docker_image=docker_dict['image'],
                                          temp_dir=docker_dict['temp_dir'],
                                          arguments=docker_dict['arguments'])
    res = dict()
    res['e_code'] = e_code
    res['out'] = out.decode('utf-8')
    res['err'] = err.decode('utf-8')
    res['elapsed_time'] = _cur_time_in_seconds() - start_time
    with open(docker_dict['outfile'], 'w') as f:
        json.dump(res, f)


class DockerRunner(object):
    """
    Wrapper to run Docker containers
    """
    def __init__(self, path_to_docker='docker'):
        """
        Constructor
        """
        self._dockerpath = path_to_docker

    def run_docker(self, docker_image=None, arguments=None,
                   temp_dir=None):
        """
        Runs docker command returning a tuple
        with error code, standard out and standard error

        :param docker_image: docker image to run
        :type docker_image: str
        :param arguments: list of arguments
        :type arguments: list
        :param temp_dir: temporary directory where docker can be run
                         this should be a directory that docker can
                         access when `-v X:X` flag is added to docker
                         command
        :type temp_dir: str
        :return:
        """
        full_args = [self._dockerpath, 'run',
                     '--rm', '-v',
                     temp_dir + ':' +
                     temp_dir,
                     docker_image]
        full_args.extend(arguments)
        start_time = _cur_time_in_seconds()
        try:
            return self._run_docker_cmd(full_args)
        finally:
            LOGGER.debug('Running ' +
                         ' '.join(full_args) +
                         ' took ' +
                         str(_cur_time_in_seconds() - start_time) +
                         ' seconds')

    def _run_docker_cmd(self, cmd):
        """
        Runs docker

        :param cmd_to_run: command to run as list
        :type cmd_to_run: list
        :return: (return code, stdout from subprocess, stderr from subprocess)
        :rtype: tuple
        """

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        out, err = p.communicate()

        return p.returncode, out, err
