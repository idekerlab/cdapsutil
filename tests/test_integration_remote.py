#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_remoteservice
----------------------------------

This is an acceptance test only enabled
if correct environment variables are set
"""

import os
import sys
import tempfile
import shutil
import json
import unittest

import cdapsutil
import ndex2

SKIP_REASON = 'CDAPSUTIL_TEST_SERVER not set cannot run'\
              ' remote integration tests'
DOCKER_SKIP_REASON = 'CDAPSUTIL_TEST_DOCKER not set cannot run'\
              ' Docker integration tests on remote algorithms'

@unittest.skipUnless(os.getenv('CDAPSUTIL_TEST_SERVER') is not None,
                     SKIP_REASON)
class TestRemoteService(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def get_data_dir(self):
        return os.path.join(os.path.dirname(__file__), 'data')

    def get_human_hiv_as_nice_cx(self):
        """

        :return:
        """
        return ndex2.create_nice_cx_from_file(os.path.join(self.get_data_dir(),
                                                           'hiv_human_ppi.cx'))

    def get_service_runner(self):
        """
        Gets service runner
        :return:
        """
        service_host = os.getenv('CDAPSUTIL_TEST_SERVER')
        if len(service_host.strip()) == 0:
            return cdapsutil.ServiceRunner()
        return cdapsutil.ServiceRunner(service_endpoint=service_host)

    def get_algorithms(self):
        sr = self.get_service_runner()
        algos_dict = sr.get_algorithms()['algorithms']
        cd_dict = {}
        for entry in algos_dict:
            if 'EDGELIST' not in algos_dict[entry]['inputDataFormat']:
                continue
            if 'COMMUNITY' not in algos_dict[entry]['outputDataFormat']:
                continue
            cd_dict[entry] = algos_dict[entry]
        return cd_dict

    def test_get_algorithms(self):

        sr = self.get_service_runner()
        res = sr.get_algorithms()
        self.assertTrue('algorithms' in res)
        self.assertTrue(len(res['algorithms']) > 0)
        for key in res['algorithms'].keys():
            self.assertTrue(res['algorithms'][key]['dockerImage'] is not None)

    def test_run_community_detection_with_all_algorithms(self):
        sr = self.get_service_runner()
        cd_dict = self.get_algorithms()
        algos = []
        for algo in cd_dict.keys():
            algos.append(algo)
        self.assertTrue(len(algos) > 0)
        net_cx = self.get_human_hiv_as_nice_cx()
        cd = cdapsutil.CommunityDetection(runner=sr)
        failures = []
        for algo in algos:
            try:
                hier_net = cd.run_community_detection(net_cx=net_cx,
                                                      algorithm=algo)
                self.assertTrue(hier_net is not None)
                self.assertTrue(len(hier_net.get_nodes()) > 0)
                self.assertTrue(algo in hier_net.get_name())
            except cdapsutil.CommunityDetectionError as ce:
                failures.append(algo + ' failed : ' + str(ce))

        self.assertEqual('', ' '.join(failures))

    @unittest.skipUnless(os.getenv('CDAPSUTIL_TEST_DOCKER') is not None,
                         DOCKER_SKIP_REASON)
    def test_run_community_detection_with_all_algorithms_via_docker(self):
        cd_dict = self.get_algorithms()
        algos = []
        for algo in cd_dict.keys():
            algos.append(cd_dict[algo]['dockerImage'])
        self.assertTrue(len(algos) > 0)
        net_cx = self.get_human_hiv_as_nice_cx()
        cd = cdapsutil.CommunityDetection(runner=cdapsutil.DockerRunner())
        failures = []
        for algo in algos:
            temp_dir = tempfile.mkdtemp(dir=os.getcwd())
            try:
                hier_net = cd.run_community_detection(net_cx=net_cx,
                                                      algorithm=algo,
                                                      temp_dir=temp_dir)
                self.assertTrue(hier_net is not None)
                self.assertTrue(len(hier_net.get_nodes()) > 0)
                self.assertTrue(algo in hier_net.get_name())
            except cdapsutil.CommunityDetectionError as ce:
                failures.append(algo + ' failed : ' + str(ce))
            finally:
                shutil.rmtree(temp_dir)

        self.assertEqual('', ' '.join(failures))


if __name__ == '__main__':
    sys.exit(unittest.main())
