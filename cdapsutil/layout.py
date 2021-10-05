# -*- coding: utf-8 -*-

import logging
import json
from json.decoder import JSONDecodeError
import ndex2
from ndex2 import constants
from cdapsutil.runner import LayoutServiceRunner
from cdapsutil.exceptions import CommunityDetectionError

LOGGER = logging.getLogger(__name__)


class Layout(object):
    """
    Runs Layout packaged as `Docker <https://www.docker.com/>`__
    containers built for `CDAPS service <https://cdaps.readthedocs.io>`__ vi
    :py:class:`~cdapsutil.runner.Runner`
    """

    def __init__(self,
                 runner=LayoutServiceRunner()):
        """
        Constructor. See class description for usage

        """
        if runner is None:
            raise CommunityDetectionError('runner is None')
        self._runner = runner

    def run_layout(self, net_cx, algorithm=None,
                   temp_dir=None, arguments=None):
        """
        Runs layout algorithm specified by **algorithm** parameter
        on **net_cx** network

        :param net_cx: Network to run community detection on
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param algorithm: Name of algorithm to run. Depending on the
                          :py:class:`~cdapsutil.runner.Runner` used this
                          can be an algorithm name, a file, or a Docker image
        :type algorithm: str
        :param temp_dir: Path to temporary directory used by some of the
                         :py:class:`~cdapsutil.runner.Runner` runners
        :type temp_dir: str
        :param arguments: Any custom parameters for algorithm. The
                          parameters should all be of type :py:class:`str`
                          If custom parameter is just a flag set
                          value to ``None``
                          Example: ``{'--flag': None, '--cutoff': '0.2'}``
        :type arguments: dict
        :return: Network with layout added
        :rtype: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        """
        e_code, out, err = self._runner.run(net_cx, algorithm=algorithm,
                                            arguments=arguments,
                                            temp_dir=temp_dir)
        if e_code != 0:
            raise CommunityDetectionError('Non-zero exit code from '
                                          'algorithm: ' +
                                          str(e_code) + ' : ' + str(err) +
                                          ' : ' + str(out))

        layout = self._get_layout_from_result(result=out)

        net_cx.set_opaque_aspect(ndex2.constants.CARTESIAN_LAYOUT_ASPECT,
                                 layout)
        return net_cx

    def _get_layout_from_result(self, result=None):
        """
        Gets layout from algorithm output
        :param result:
        :return: Cartesian Layout Aspect
        :rtype: dict
        """
        if isinstance(result, list):
            return result
        try:
            return json.loads(result)
        except JSONDecodeError as je:
            raise CommunityDetectionError('Error parsing result: ' + str(je))
