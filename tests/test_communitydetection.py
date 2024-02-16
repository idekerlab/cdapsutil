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
from unittest.mock import MagicMock

import requests_mock
from ndex2 import constants
from ndex2.cx2 import CX2Network

import cdapsutil
from cdapsutil.cd import CXHierarchyCreatorHelper, HierarchyCreatorHelper, CX2HierarchyCreatorHelper
from cdapsutil.exceptions import CommunityDetectionError
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

    def test_get_network_name(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        helper = HierarchyCreatorHelper()
        # try passing None
        self.assertEqual('unknown', helper._get_network_name(None))

        # try network with no call to set_name() made
        net_cx = ndex2.nice_cx_network.NiceCXNetwork()
        self.assertEqual('unknown', helper._get_network_name(net_cx=net_cx))

        # try network where name set to None
        net_cx = ndex2.nice_cx_network.NiceCXNetwork()
        net_cx.set_name(None)
        self.assertEqual('unknown', helper._get_network_name(net_cx=net_cx))

        # try network where name set to empty string
        net_cx = ndex2.nice_cx_network.NiceCXNetwork()
        net_cx.set_name('')
        self.assertEqual('', helper._get_network_name(net_cx=net_cx))

    def test_run_community_detection_with_weight_col(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        net_cx = ndex2.nice_cx_network.NiceCXNetwork()
        try:
            cd.run_community_detection(net_cx, algorithm='foo',
                                       weight_col='somecol')
        except CommunityDetectionError as ce:
            self.assertEqual('Weighted graphs are not yet supported',
                             str(ce))

    def test_derive_hierarchy_from_result_with_none_result(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)

        try:
            cd._derive_hierarchy_from_result(None)
        except CommunityDetectionError as ce:
            self.assertEqual('Result is None',
                             str(ce))

    def test_derive_hierarchy_from_result_with_dict_missing_result(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)

        try:
            cd._derive_hierarchy_from_result({'hi': 'there'})
        except CommunityDetectionError as ce:
            self.assertEqual('Expected result key in JSON',
                             str(ce))

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

    def test_external_with_network_name_set_to_none(self):
        er = cdapsutil.ExternalResultsRunner()
        cd = cdapsutil.CommunityDetection(runner=er)
        datafile = os.path.join(self.get_data_dir(), 'cdinfomap_out.json')
        net_cx = self.get_human_hiv_as_nice_cx()
        net_cx.set_name(None)
        hier_net = cd.run_community_detection(net_cx=net_cx,
                                              algorithm=datafile)
        self.assertEqual(68, len(hier_net.get_nodes()))
        self.assertEqual(67, len(hier_net.get_edges()))
        self.assertEqual('cdinfomap_out.json_(none)_unknown',
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
            helper = CXHierarchyCreatorHelper()
            helper.apply_style(net_cx)
            res = net_cx.get_opaque_aspect('cyVisualProperties')
            self.assertEqual('network', res[0]['properties_of'])
            net_cx = ndex2.nice_cx_network.NiceCXNetwork()
            helper.apply_style(net_cx,
                               style=os.path.join(self.get_data_dir(),
                                                  'hiv_human_ppi.cx'))
            altres = net_cx.get_opaque_aspect(('cyVisualProperties'))
            self.assertNotEqual(res, altres)
        finally:
            shutil.rmtree(temp_dir)

    def test_get_node_dictionary(self):
        net_cx = self.get_human_hiv_as_nice_cx()
        helper = CXHierarchyCreatorHelper()
        node_dict = helper._get_node_dictionary(net_cx)
        self.assertEqual(471, len(node_dict))
        self.assertEqual('REV', node_dict[738])

    def test_format_custom_parameters(self):
        helper = HierarchyCreatorHelper()
        self.assertEqual(helper._format_custom_parameters(None), '')
        self.assertEqual(helper._format_custom_parameters({}), '')
        params = {'param1': 'value1', 'param2': 'value2'}
        expected = 'param1 value1 param2 value2'
        self.assertEqual(helper._format_custom_parameters(params), expected)

    def test_get_network_name_cx2(self):
        helper = HierarchyCreatorHelper()
        net_cx = CX2Network()
        net_cx.add_network_attribute('name', 'Test Network')
        self.assertEqual(helper._get_network_name(net_cx), 'Test Network')

    def test_add_custom_annotations_no_nodeAttributesAsCX2(self):
        helper = HierarchyCreatorHelper()
        net_cx = ndex2.nice_cx_network.NiceCXNetwork()
        res_json = {}
        nodes_dict = {}
        self.assertIsNone(helper._add_custom_annotations(net_cx, nodes_dict, res_json))

    def test_add_custom_annotations(self):
        helper = HierarchyCreatorHelper()
        net_cx = CX2Network()
        node_id = net_cx.add_node(attributes={'name': 'Node1'})
        nodes_dict = {1: node_id}
        res_json = {
            'nodeAttributesAsCX2': {
                'attributeDeclarations': [{
                    'nodes': {
                        'attr_name_1': {'a': 'attr1', 'v': 'attr_value_1', 'd': 'string'}
                    }
                }],
                'nodes': [{
                    'id': 1,
                    'v': {'attr1': 'Test Value'}
                }]
            }
        }
        helper._add_custom_annotations(net_cx, nodes_dict, res_json)
        node_attrs = net_cx.get_node(node_id)[constants.ASPECT_VALUES]
        self.assertTrue(any(attr == 'attr_name_1' for attr in node_attrs.keys()))

    def test_get_node_dictionary_cx2(self):
        helper = CX2HierarchyCreatorHelper()
        net_cx2 = CX2Network()
        net_cx2.add_node(attributes={'name': 'Node1'})
        net_cx2.add_node(attributes={'name': 'Node2'})
        net_cx2.get_nodes = MagicMock(return_value={
            1: {constants.ASPECT_VALUES: {constants.NODE_NAME_EXPANDED: "Node1"}},
            2: {constants.ASPECT_VALUES: {constants.NODE_NAME_EXPANDED: "Node2"}}
        })
        node_dict = helper._get_node_dictionary(net_cx2)
        self.assertEqual(node_dict, {1: "Node1", 2: "Node2"})

    def test_create_empty_hierarchy_network_cx2(self):
        helper = CX2HierarchyCreatorHelper()
        net_cx2 = CX2Network()
        net_cx2.add_node(attributes={'name': 'Node1'})
        net_cx2.add_node(attributes={'name': 'Node2'})
        hier_net = helper._create_empty_hierarchy_network(
            docker_image="test_image",
            algo_name="test_algo",
            source_network=net_cx2,
            arguments={"param1": "value1"}
        )
        self.assertIsInstance(hier_net, CX2Network)
        print(hier_net.get_network_attributes())
        self.assertTrue((hier_net.get_network_attributes()['name']).startswith("test_algo"))

    def test_create_network_basic(self):
        helper = CX2HierarchyCreatorHelper()
        net_cx2 = CX2Network()
        net_cx2.add_node(attributes={'name': 'Node1'})
        net_cx2.add_node(attributes={'name': 'Node2'})
        helper._get_node_dictionary = MagicMock(return_value={1: "Node1", 2: "Node2"})
        cluster_members = {1: [1], 2: [2]}
        clusters_dict = {1: [2]}

        res_as_json = {
            "nodeAttributesAsCX2": {
                "attributeDeclarations": [],
                "nodes": []
            }
        }

        hier_net = helper.create_network(
            docker_image="docker_image",
            algo_name="algo_name",
            net_cx=net_cx2,
            cluster_members=cluster_members,
            clusters_dict=clusters_dict,
            res_as_json=res_as_json,
            arguments={}
        )

        self.assertIsInstance(hier_net, CX2Network)
        self.assertTrue(len(hier_net.get_nodes()) > 0)
        self.assertTrue(len(hier_net.get_edges()) > 0)

    def test_apply_style_cx2(self):
        helper = CX2HierarchyCreatorHelper()
        net_cx2 = CX2Network()
        net_cx2.add_node(attributes={'name': 'Node1'})
        net_cx2.add_node(attributes={'name': 'Node2'})
        helper.apply_style(net_cx2, style='default_style.cx2')
        self.assertIsNotNone(net_cx2.get_visual_properties())


if __name__ == '__main__':
    sys.exit(unittest.main())
