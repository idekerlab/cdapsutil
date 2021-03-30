# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import json
import time
import requests
import cdapsutil

from cdapsutil.exceptions import CommunityDetectionError

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
    e_code, out, err = drunner.submit(algorithm=docker_dict['image'],
                                      temp_dir=docker_dict['temp_dir'],
                                      arguments=docker_dict['arguments'])
    res = dict()
    res['e_code'] = e_code
    res['out'] = out.decode('utf-8')
    res['err'] = err.decode('utf-8')
    res['elapsed_time'] = _cur_time_in_seconds() - start_time
    with open(docker_dict['outfile'], 'w') as f:
        json.dump(res, f)


class ProcessWrapper(object):
    """
    Runs command line process
    """
    def __init__(self):
        """
        Constructor
        """
        pass

    def run(self, cmd):
        """
        Runs external process

        :param cmd: Command to run. Should be a list of arguments
                    that include invoking command. For example to
                    run ``ls -la`` pass in ['ls','-la']
        :type cmd: list
        :return: (return code, stdout from subprocess, stderr from subprocess)
        :rtype: tuple
        """
        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        out, err = p.communicate()

        return p.returncode, out, err


class Runner(object):
    """
    Base class for objects that run Community Detection Algorithms packaged as
    `Docker <https://www.docker.com/>`__ containers built for
    `CDAPS service <https://cdaps.readthedocs.io/>`__ via various means.

    Currently built Runners:

    :py:class:`ExternalResultsRunner` - Parses already run output file/stream

    :py:class:`DockerRunner` - Runs locally via Docker

    :py:class:`ServiceRunner` - Runs remotely via CDAPS Service

    """

    def __init__(self):
        """
        Constructor
        """
        self._docker_image_name = ''
        self._algorithm_name = ''
        LOGGER.warning('DISCLAIMIER: cdapsutil is experimental '
                       'and may contain errors and interfaces '
                       'may change')

    def get_docker_image(self):
        """
        Gets the name of the Docker image

        :return: Name of Docker image or empty string if
                 unknown
        :rtype: str
        """
        return self._docker_image_name

    def set_docker_image(self, docker_image):
        """
        Sets Docker image
        :return:
        """
        self._docker_image_name = docker_image

    def get_algorithm_name(self):
        """
        Gets the algorithm name

        :return: Name of algorithm or empty string if unknown
        :rtype: str
        """
        return self._algorithm_name

    def set_algorithm_name(self, algoname):
        """
        Sets algorithm name

        :param algoname: Name of algorithm
        :type algoname: str
        :return:
        """
        self._algorithm_name = algoname

    def get_algorithms(self):
        """
        Will always raise since subclasses should implement this
        :py:class:`~cdapsutil.exceptions.CommunityDetectionError`

        :raises CommunityDetectionError: Will always raise this
        """
        raise CommunityDetectionError('Not implemented for this Runner')

    def run(self, net_cx=None, algorithm=None, arguments=None, temp_dir=None):
        """
        Must be implemented by subclasses. Will always raise
        :py:class:`cdapsutil.exceptions.CommunityDetectionError`

        :param net_cx: Network to use as input
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param algorithm:
        :param arguments: Any custom parameters for algorithm. The
                          parameters should all be of type :py:class:`str`
                          If custom parameter is just a flag set
                          value to ``None``
                          Example: ``{'--flag': None, '--cutoff': '0.2'}``
        :param temp_dir:
        :raises CommunityDetectionError: Will always raise this
        :return: None
        """
        raise CommunityDetectionError('Not implemented for this Runner')

    @staticmethod
    def _write_edge_list(net_cx, tempdir=None, weight_col=None):
        """
        Writes edges from `net_cx` network to file named ``input.edgelist``
        in `tempdir` as a tab delimited file of source target

        **WARNING** `weight_col` parameter is currently ignored

        :param net_cx: Network to extract edges from
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param tempdir: Directory to write edge list to
        :type tempdir: str
        :return: Path to edgelist file
        :rtype: str
        """
        edgelist = os.path.join(tempdir, 'input.edgelist')
        with open(edgelist, 'w') as f:
            for edge_id, edge_obj in net_cx.get_edges():
                f.write(str(edge_obj['s']) + '\t' + str(edge_obj['t']) + '\n')
        return edgelist

    @staticmethod
    def _get_edge_list(net_cx, weight_col=None):
        """
        Gets edges from 'net_cx' network.

        **WARNING** 'weight_col' parameter is currently ignored

        :param net_cx: Network to extract edges from
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param weight_col: Name of column to extract weights from
        :type weight_col: str
        :return: Edges in tab delimited format
        :rtype: str
        """
        edgelist = []

        for edge_id, edge_obj in net_cx.get_edges():
            edgelist.append(str(edge_obj['s']) + '\t' + str(edge_obj['t']) + '\n')
        return ''.join(edgelist)


class ServiceRunner(Runner):
    """
    :py:class:`Runner` that runs `CDAPS Service containers`
    remotely via `CDAPS Service <https://cdaps.readthedocs.io>`__

    :param service_endpoint: URL for CDAPS REST Service
    :type service_endpoint: str
    :param requests_timeout: Timeout in seconds to pass to
                             :py:mod:`requests` module for all web requests
    :type requests_timeout: int or float
    :param max_retries: Number of times to check for task completion
    :type max_retries: int
    :param poll_interval: Time to wait in seconds between checks for task
                          completion
    :type poll_interval: int
    """

    USER_AGENT_KEY = 'UserAgent'
    """
    User Agent Header label
    """

    REST_ENDPOINT = 'http://cdservice.cytoscape.org/cd/' \
                    'communitydetection/v1'
    """
    Default Rest endpoint
    """

    def __init__(self, service_endpoint=REST_ENDPOINT, requests_timeout=30,
                 max_retries=600, poll_interval=1):
        """
        Constructor. See class docs for usage

        """
        super().__init__()

        self._service_endpoint = service_endpoint
        self._requests_timeout=requests_timeout
        self._useragent = 'cdapsutil/' +\
                          str(cdapsutil.__version__)
        self._max_retries = max_retries
        self._poll_interval = poll_interval

    def _get_user_agent_header(self):
        """
        Gets a :py:class:`dict` with User Agent for this
        client that can be passed to `headers=` of :py:mod:`requests`
        package

        :return: ``{'UserAgent': 'cdapsutil/<VERSION>'}``
        :rtype: dict
        """
        return {ServiceRunner.USER_AGENT_KEY: self._useragent}

    def _extract_exit_out_and_error_from_json(self, resp_as_json):
        """

        :param resp_as_json:
        :return:
        """
        e_code = 0
        if resp_as_json['status'] != 'complete':
            e_code = 1
        return e_code, resp_as_json['result'], resp_as_json['message']

    def run(self, net_cx=None, algorithm=None, arguments=None,
            temp_dir=None):
        """
        Runs 'algorithm' via `CDAPS service <https://cdaps.readthedocs.io/>`__
        with error code, standard out and standard error derived
        from the service call

        :param net_cx: Network to use as input
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param algorithm: Algorithm to run
        :type algorithm: str
        :param arguments: Any custom parameters for algorithm. The
                          parameters should all be of type :py:class:`str`
                          If custom parameter is just a flag set
                          value to ``None``
                          Example: ``{'--flag': None, '--cutoff': '0.2'}``
        :type arguments: dict
        :param temp_dir: Ignored
        :type temp_dir: str
        :raises CommunityDetectionError: If there is an error in running job
                                         outside of non-zero exit code from
                                         command
        :return: (return code, stdout from subprocess, stderr from subprocess)
        :rtype: tuple
        """
        edgelist = self._get_edge_list(net_cx)
        task_id = self.submit(algorithm=algorithm, data=edgelist,
                              arguments=arguments)['id']
        LOGGER.debug('Waiting for task ' + str(task_id) + ' to complete')
        self.set_algorithm_name(algorithm)
        self.wait_for_task_to_complete(task_id,
                                                max_retries=self._max_retries,
                                                poll_interval=self._poll_interval)
        resp_as_json = self.get_result(task_id)
        if resp_as_json['status'] != 'complete':
            CommunityDetectionError('Error running algorithm. '
                                    'Raw JSON: ' +
                                    str(resp_as_json))

        return self._extract_exit_out_and_error_from_json(resp_as_json)

    def submit(self, algorithm=None, data=None,
               arguments=None):
        """
        Submits algorithm to `CDAPS service <https://cdaps.readthedocs.io/>`__
        with endpoint set in constructor

        :param algorithm: Name of algorithm to call
        :type algorithm: str
        :param data: The data to pass to the algorithm
        :type object: Could be str, dict, list or anything that can be
                      converted to JSON
        :param arguments: Any custom parameters for algorithm. The
                          parameters should all be of type :py:class:`str`
                          If custom parameter is just a flag set
                          value to ``None``
                          Example: ``{'--flag': None, '--cutoff': '0.2'}``
        :type arguments: dict
        :return: Task id in this format ``{'id': '<TASK ID'}``
        :rtype: dict
        """
        if algorithm is None or len(str(algorithm).strip()) == 0:
            raise CommunityDetectionError('Algorithm is empty string or None')

        thedata = {'algorithm': algorithm,
                   'data': data}

        if arguments is not None:
            thedata['customParameters'] = arguments
        req = None
        try:
            LOGGER.debug('Submitting algorithm ' + str(algorithm) + ' to ' +
                         str(self._service_endpoint))
            req = requests.post(self._service_endpoint, json=thedata,
                                headers=self._get_user_agent_header(),
                                timeout=self._requests_timeout)
            if req.status_code != 202:
                raise CommunityDetectionError('Received unexpected HTTP response '
                                              'status code: ' +
                                              str(req.status_code) +
                                              ' from request: ' +
                                              str(req.text))
            return req.json()
        except requests.exceptions.HTTPError as he:
            raise CommunityDetectionError('Received HTTPError submitting ' +
                                          str(algorithm) + ' with parameters ' +
                                          str(arguments) + ' : ' +
                                          str(he))
        except json.decoder.JSONDecodeError as je:
            raise CommunityDetectionError('Unable to parse result from submit: ' +
                                          str(je))
        finally:
            if req is not None:
                try:
                    req.close()
                except requests.exceptions.HTTPError as he:
                    LOGGER.debug('Caught HTTPError closing response : ' +
                                 str(he))
                    pass

    def wait_for_task_to_complete(self, task_id, poll_interval=1,
                                  consecutive_fail_retry=5,
                                  max_retries=None):
        """
        Waits for task with `task_id` id to complete.

        :param task_id: Id of task
        :type task_id: str
        :param poll_interval: How long to wait in seconds before checking
                              again if task is complete
        :type poll_interval: int
        :param consecutive_fail_retry: If the number of consecutive failure calls to get
                               status exceeds this value an exception is raised
        :type consecutive_fail_retry: int
        :param max_retries: Total number of checks to perform before raising an
                            exception. For example, if `max_retries` is set to
                            ``600`` and `poll_interval` is ``1`` then this
                            method will wait 10 minutes for task to complete
                            checking 600 times, or once per second.
                            **NOTE:** If set to``None`` this method will
                            poll indefinitely
        :type max_retries: int
        :raises CommunityDetectionError: If `task_id` is ``None``, if
                                         `max_fail_retry` is exceeded,
                                         if `max_retries` is exceeded
        :return: status response of completed task
        :rtype: dict

        """
        if task_id is None or len(str(task_id).strip()) == 0:
            raise CommunityDetectionError('Task id is empty string or None')

        # polling loop to wait for task to complete
        progress = 0
        consecutive_err_cnt = 0
        retry_count = 0
        LOGGER.debug('Task id: ' + str(task_id) +
                     ' Poll interval: ' + str(poll_interval) +
                     ' consecutive fail retry: ' +
                     str(consecutive_fail_retry) +
                     ' max retries: ' + str(max_retries))
        while progress != 100 and consecutive_err_cnt <= consecutive_fail_retry:

            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug('Try # ' + str(retry_count) + ' progress: ' +
                             str(progress) + ' consecutive error count: ' +
                             str(consecutive_err_cnt))
            retry_count += 1
            if max_retries is not None:
                if retry_count > max_retries:
                    raise CommunityDetectionError('Max retry count ' +
                                                  str(max_retries) +
                                                  ' exceeded')
            time.sleep(poll_interval)
            resp = None
            try:
                resp = requests.get(self._service_endpoint + '/' +
                                    str(task_id) + '/status',
                                    headers=self._get_user_agent_header(),
                                    timeout=self._requests_timeout)

                if resp.status_code != 200:
                    consecutive_err_cnt += 1
                    LOGGER.debug('Ran into some error: ' + str(resp.text))
                    continue

                resp_json = resp.json()
                if resp_json is None or 'progress' not in resp_json:
                    LOGGER.debug('progress not in JSON: ' + str(resp_json))
                    consecutive_err_cnt += 1
                    continue
                consecutive_err_cnt = 0
                progress = resp_json['progress']
                LOGGER.debug('Progress is ' + str(progress))
            except requests.exceptions.HTTPError as he:
                LOGGER.debug('Received error from requests: ' + str(he))
                consecutive_err_cnt += 1
                continue
            finally:
                if resp is not None:
                    try:
                        resp.close()
                    except requests.exceptions.HTTPError as he:
                        LOGGER.debug('Caught HTTPError closing response : ' +
                                     str(he))
                        pass

        if consecutive_err_cnt > 0:
            raise CommunityDetectionError('Received ' +
                                          str(consecutive_err_cnt) +
                                          ' consecutive errors')
        return resp_json

    def get_result(self, task_id):
        """
        Gets result from `CDAPS service <https://cdaps.readthedocs.io/>`__

        :param task_id: Id of task
        :type task_id: str
        :return: Result from service
        :rtype: dict
        """
        if task_id is None or len(str(task_id).strip()) == 0:
            raise CommunityDetectionError('Task id is empty string or None')
        resp = None
        try:
            resp = requests.get(self._service_endpoint + '/' +
                                str(task_id),
                                headers=self._get_user_agent_header(),
                                timeout=self._requests_timeout)
            if resp.status_code != 200:

                raise CommunityDetectionError('Received ' + str(resp.status_code) +
                                              ' HTTP response status code : ' +
                                              str(resp.text))
            return resp.json()
        except requests.exceptions.HTTPError as he:
            raise CommunityDetectionError('Received HTTPError getting result'
                                          ' for task: ' + task_id + ' : ' +
                                          str(he))
        finally:
            if resp is not None:
                try:
                    resp.close()
                except requests.exceptions.HTTPError as he:
                    LOGGER.debug('Caught HTTPError closing response : ' +
                                 str(he))
                    pass

    def get_algorithms(self):
        """
        Queries `CDAPS service <https://cdaps.readthedocs.io/>`__ for list
        of available algorithms

        Example result (only showing one algorithm):

        .. code-block:: python

            { "algorithms":
                {
                  "name": "hidef",
                  "displayName": "HiDeF",
                  "description": "...",
                  "version": "0.2.2",
                  "dockerImage": "coleslawndex/cdhidef:0.2.2",
                  "inputDataFormat": "EDGELISTV2",
                  "outputDataFormat": "COMMUNITYDETECTRESULTV2",
                  "customParameters": [
                    {
                      "name": "--maxres",
                      "displayName": "Maximum resolution parameter",
                      "description": "Maximum resolution parameter. Increase to get more smaller communities",
                      "type": "value",
                      "defaultValue": "50.0",
                      "validationType": "number",
                      "validationHelp": "Should be a number",
                      "validationRegex": null,
                      "minValue": null,
                      "maxValue": null
                    },
                    {
                      "name": "--alg",
                      "displayName": "Algorithm",
                      "description": "Choose to use Louvain or newer Leiden algorithm",
                      "type": "value",
                      "defaultValue": "louvain",
                      "validationType": "string",
                      "validationHelp": "Must be set to louvain or leiden",
                      "validationRegex": "louvain|leiden",
                      "minValue": null,
                      "maxValue": null
                    }
                  ]
                }
            }

        :raises CommunityDetectionError: If there is an error
        :return: Algorithms available from service in example format shown above
        :rtype: dict
        """
        resp = None
        try:
            resp = requests.get(self._service_endpoint + '/algorithms',
                                headers=self._get_user_agent_header(),
                                timeout=self._requests_timeout)
            if resp.status_code != 200:
                raise CommunityDetectionError('Received ' +
                                              str(resp.status_code) +
                                              ' HTTP response status code : ' +
                                              str(resp.text))
            return resp.json()
        except json.JSONDecodeError as je:
            raise CommunityDetectionError('Error result not in JSON '
                                          'format : ' + str(je))
        except requests.exceptions.HTTPError as he:
            raise CommunityDetectionError('Received HTTPError getting '
                                          'algorithms : ' +
                                          str(he))
        finally:
            if resp is not None:
                try:
                    resp.close()
                except requests.exceptions.HTTPError as he:
                    LOGGER.debug('Caught HTTPError closing response : ' +
                                 str(he))
                    pass


class DockerRunner(Runner):
    """
    :py:class:`Runner` that runs CDAPS Service Docker containers
    locally via `Docker <https://docker.com>`__

    :param binary_path: Full path to Docker command
    :type binary_path: str
    :param processwrapper: Object to run external process
    :type processwrapper: :py:class:`ProcessWrapper`
    """
    def __init__(self, binary_path='docker',
                 processwrapper=ProcessWrapper()):
        """
        Constructor
        """
        super().__init__()
        self._dockerpath = binary_path
        self._procwrapper = processwrapper

    def run(self, net_cx=None, algorithm=None, arguments=None,
            temp_dir=None):
        """
        Runs `Docker <https://docker.com>`__ command returning a tuple
        with error code, standard out and standard error

        :param net_cx: Network to use as input
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param algorithm: docker image to run
        :type algorithm: str
        :param arguments: Any custom parameters for algorithm. The
                          parameters should all be of type :py:class:`str`
                          If custom parameter is just a flag set
                          value to ``None``
                          Example: ``{'--flag': None, '--cutoff': '0.2'}``
        :type arguments: dict
        :param temp_dir: temporary directory where docker can be run
                         this should be a directory that docker can
                         access when `-v X:X` flag is added to docker
                         command
        :type temp_dir: str
        :raises CommunityDetectionError: If there is an error in running job
                                         outside of non-zero exit code from
                                         command
        :return: (return code, stdout from subprocess, stderr from subprocess)
        :rtype: tuple
        """
        if algorithm is None:
            raise CommunityDetectionError('Algorithm is None')

        edgelist = self._write_edge_list(net_cx, tempdir=temp_dir)
        full_args = [self._dockerpath, 'run',
                     '--rm', '-v',
                     temp_dir + ':' +
                     temp_dir,
                     algorithm,
                     edgelist]
        self.set_docker_image(algorithm)
        self.set_algorithm_name(algorithm)
        if arguments is not None:
            for key in arguments:
                full_args.append(key)
                if arguments[key] is not None:
                    full_args.append(str(arguments[key]))

        start_time = _cur_time_in_seconds()
        try:
            return self._procwrapper.run(full_args)
        finally:
            LOGGER.debug('Running ' +
                         ' '.join(full_args) +
                         ' took ' +
                         str(_cur_time_in_seconds() - start_time) +
                         ' seconds')


class ExternalResultsRunner(Runner):
    """
    :py:class:`Runner` returns an already generated result set
    via `algorithm` parameter in :py:func:`~ExternalResultsRunner.run` method.
    This allows results generated externally to be processed.

    """
    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def run(self, net_cx=None, algorithm=None, arguments=None,
            temp_dir=None):
        """
        Assumes `algorithm` contains path to file with result of invocation
        of algorithm. This allows for externally run algorithms to be
        loaded into this library.

        A tuple is returned with return code,result and standard error
        of result.

        In this implementation the return code is always ``0`` unless the
        contents of the file is in format matching result from
        CDAPS REST Service in which case a ``1`` returncode may be sent if
        the status was **NOT** ``complete``. Any data in ``message`` field
        will be set in the standard error of result.

        :param net_cx: Ignored
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param algorithm: Path to file with results
        :type algorithm: str
        :param arguments: Ignored
        :type arguments: dict
        :param temp_dir: Ignored
        :type temp_dir: str
        :raises CommunityDetectionError: If there is an error in running job
                                         outside of non-zero exit code from
                                         command
        :return: (return code, result, error message)
        :rtype: tuple
        """
        if algorithm is None:
            raise CommunityDetectionError('Algorithm is None')

        if not os.path.isfile(algorithm):
            raise CommunityDetectionError(str(algorithm) + ' is not a file')
        e_code = 0
        err = None
        try:
            with open(algorithm, 'r') as f:
                result = f.read()
                try:
                    if result.lstrip().startswith('{'):
                        json_res = json.loads(result)
                        if 'status' in result:
                            if str(json_res['status']) != 'complete':
                                e_code = 1
                        if 'message' in result:
                            err = json_res['message']
                except json.JSONDecodeError:
                    pass
            self.set_docker_image('Loaded from file: ' + algorithm)
            self.set_algorithm_name(os.path.basename(algorithm))
            return e_code, result, err
        except OSError as oe:
            raise CommunityDetectionError('Caught OSError : ' + str(oe))
