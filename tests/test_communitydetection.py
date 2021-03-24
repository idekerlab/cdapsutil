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

    def test_service_with_successful_mock_data(self):
        sr = cdapsutil.ServiceRunner(service_endpoint='http://foo')
        cd = cdapsutil.CommunityDetection(service=sr)
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
                                                  algo_or_docker='infomap',
                                                  via_service=True,
                                                  max_retries=1,
                                                  poll_interval=0)

            self.assertEqual(68, len(hier_net.get_nodes()))
            self.assertEqual(67, len(hier_net.get_edges()))
            self.assertEqual('infomap_(none)_HIV-human PPI',
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

    def get_edge_dict(self, net_cx):
        edge_dict = {}
        for edge_id, edge_obj in net_cx.get_edges():
            if edge_obj['s'] not in edge_dict:
                edge_dict[edge_obj['s']] = set()
            edge_dict[edge_obj['s']].add(edge_obj['t'])
        return edge_dict

    def test_get_edge_list(self):
        net_cx = self.get_human_hiv_as_nice_cx()

        edge_dict = self.get_edge_dict(net_cx)

        cd = cdapsutil.CommunityDetection()
        res = cd._get_edge_list(net_cx)
        for entry in res.split('\n'):
            if len(entry.strip()) == 0:
                continue
            splitentry = entry.split('\t')
            self.assertTrue(int(splitentry[1]) in
                            edge_dict[int(splitentry[0])])

    def test_write_edge_list(self):
        temp_dir = tempfile.mkdtemp()
        try:
            net_cx = self.get_human_hiv_as_nice_cx()

            edge_dict = self.get_edge_dict(net_cx)

            cd = cdapsutil.CommunityDetection()
            input_edgelist = cd._write_edge_list(net_cx, temp_dir)
            with open(input_edgelist, 'r') as f:
                for entry in f:
                    if len(entry.strip()) == 0:
                        continue
                    splitentry = entry.split('\t')
                    self.assertTrue(int(splitentry[1]) in
                                    edge_dict[int(splitentry[0])])
        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    sys.exit(unittest.main())
