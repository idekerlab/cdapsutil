#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_communitydetection
----------------------------------

Tests for `cdapsutil.cd` module.
"""

import os
import sys
import tempfile
import shutil
import json
import unittest

import requests_mock

import cdapsutil
import ndex2


class TestCommunityDetection(unittest.TestCase):

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

    def get_infomap_res_as_dict(self):
        with open(os.path.join(self.get_data_dir(),
                               'cdinfomap_out.json'), 'r') as f:
            return json.load(f)

    def test_constructor_none_for_runner(self):
        try:
            cdapsutil.CommunityDetection(runner=None)
            self.fail('Expected CommunityDetectionError')
        except cdapsutil.CommunityDetectionError as ce:
            self.assertEqual('runner is None', str(ce))

    def test_service_with_successful_mock_data(self):
        sr = cdapsutil.ServiceRunner(service_endpoint='http://foo',
                                     max_retries=1, poll_interval=0)
        cd = cdapsutil.CommunityDetection(runner=sr)
        net_cx = self.get_human_hiv_as_nice_cx()
        json_res = self.get_infomap_res_as_dict()

        with requests_mock.Mocker() as m:
            m.post('http://foo', json={'id': 'taskid'},
                   status_code=202)
            m.get('http://foo/taskid/status', status_code=200,
                  json={'progress': 100})
            m.get('http://foo/taskid', status_code=200,
                  json=json_res)
            hier_net = cd.run_community_detection(net_cx,
                                                  algorithm='infomap')

            self.assertEqual(68, len(hier_net.get_nodes()))
            self.assertEqual(67, len(hier_net.get_edges()))
            self.assertEqual('infomap_(none)_HIV-human PPI',
                             hier_net.get_name())
            self.assertEqual('0', hier_net.get_network_attribute('__CD_OriginalNetwork')['v'])

    def test_external_with_successful_datafile_from_service(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        datafile = os.path.join(self.get_data_dir(), 'cdinfomap_out.json')
        net_cx = self.get_human_hiv_as_nice_cx()
        hier_net = cd.run_community_detection(net_cx=net_cx,
                                              algorithm=datafile)
        self.assertEqual(68, len(hier_net.get_nodes()))
        self.assertEqual(67, len(hier_net.get_edges()))
        self.assertEqual('cdinfomap_out.json_(none)_HIV-human PPI',
                         hier_net.get_name())
        self.assertEqual('0', hier_net.get_network_attribute('__CD_OriginalNetwork')['v'])

    def test_external_with_successful_hidefdatafile_from_docker(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        datafile = os.path.join(self.get_data_dir(), 'cdhidef:0.2.2.out')
        net_cx = self.get_human_hiv_as_nice_cx()
        hier_net = cd.run_community_detection(net_cx=net_cx,
                                              algorithm=datafile)
        self.assertEqual(105, len(hier_net.get_nodes()))
        self.assertEqual(121, len(hier_net.get_edges()))
        self.assertEqual('cdhidef:0.2.2.out_(none)_HIV-human PPI',
                         hier_net.get_name())
        self.assertEqual('0', hier_net.get_network_attribute('__CD_OriginalNetwork')['v'])

    def test_external_with_successful_louvaindatafile_from_docker(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        datafile = os.path.join(self.get_data_dir(), 'cdlouvain:0.2.0.out')
        net_cx = self.get_human_hiv_as_nice_cx()
        hier_net = cd.run_community_detection(net_cx=net_cx,
                                              algorithm=datafile)
        self.assertEqual(1, len(hier_net.get_nodes()))
        self.assertEqual(0, len(hier_net.get_edges()))
        self.assertEqual('cdlouvain:0.2.0.out_(none)_HIV-human PPI',
                         hier_net.get_name())
        self.assertEqual('0', hier_net.get_network_attribute('__CD_OriginalNetwork')['v'])

    def test_external_with_successful_infomapdatafile_from_docker(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        datafile = os.path.join(self.get_data_dir(), 'cdinfomap:0.1.0.out')
        net_cx = self.get_human_hiv_as_nice_cx()
        hier_net = cd.run_community_detection(net_cx=net_cx,
                                              algorithm=datafile)
        self.assertEqual(52, len(hier_net.get_nodes()))
        self.assertEqual(51, len(hier_net.get_edges()))
        self.assertEqual('cdinfomap:0.1.0.out_(none)_HIV-human PPI',
                         hier_net.get_name())
        self.assertEqual('0', hier_net.get_network_attribute('__CD_OriginalNetwork')['v'])

    def test_external_with_successful_oslomdatafile_from_docker(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        datafile = os.path.join(self.get_data_dir(), 'cdoslom:0.3.0.out')
        net_cx = self.get_human_hiv_as_nice_cx()
        hier_net = cd.run_community_detection(net_cx=net_cx,
                                              algorithm=datafile)
        self.assertEqual(9, len(hier_net.get_nodes()))
        self.assertEqual(8, len(hier_net.get_edges()))
        self.assertEqual('cdoslom:0.3.0.out_(none)_HIV-human PPI',
                         hier_net.get_name())
        self.assertEqual('0', hier_net.get_network_attribute('__CD_OriginalNetwork')['v'])

    def test_apply_style(self):
        temp_dir = tempfile.mkdtemp()
        try:
            net_cx = ndex2.nice_cx_network.NiceCXNetwork()
            cd = cdapsutil.CommunityDetection()
            cd._apply_style(net_cx)
            res = net_cx.get_opaque_aspect('cyVisualProperties')
            self.assertEqual('network', res[0]['properties_of'])
            net_cx = ndex2.nice_cx_network.NiceCXNetwork()
            cd._apply_style(net_cx,
                            style=os.path.join(self.get_data_dir(),
                                               'hiv_human_ppi.cx'))
            altres = net_cx.get_opaque_aspect(('cyVisualProperties'))
            self.assertNotEqual(res, altres)
        finally:
            shutil.rmtree(temp_dir)

    def test_get_node_dictionary(self):
        net_cx = self.get_human_hiv_as_nice_cx()
        cd = cdapsutil.CommunityDetection()
        node_dict = cd._get_node_dictionary(net_cx)
        self.assertEqual(471, len(node_dict))
        self.assertEqual('REV', node_dict[738])


if __name__ == '__main__':
    sys.exit(unittest.main())
