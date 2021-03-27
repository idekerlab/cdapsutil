#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_runner
----------------------------------

Tests for `cdapsutil.runner` module.
"""

import os
import stat
import sys
import tempfile
import shutil
import unittest

import ndex2
import cdapsutil
from cdapsutil.runner import Runner


class TestRunner(unittest.TestCase):

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

        res = Runner._get_edge_list(net_cx)
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

            input_edgelist = Runner._write_edge_list(net_cx, temp_dir)
            with open(input_edgelist, 'r') as f:
                for entry in f:
                    if len(entry.strip()) == 0:
                        continue
                    splitentry = entry.split('\t')
                    self.assertTrue(int(splitentry[1]) in
                                    edge_dict[int(splitentry[0])])
        finally:
            shutil.rmtree(temp_dir)

    def test_get_algorithms(self):
        runner = Runner()
        try:
            runner.get_algorithms()
            self.fail('Expected CommunityDetectionError')
        except cdapsutil.CommunityDetectionError as ce:
            self.assertEqual('Not implemented for this Runner', str(ce))

    def test_run(self):
        runner = Runner()
        try:
            runner.run()
            self.fail('Expected CommunityDetectionError')
        except cdapsutil.CommunityDetectionError as ce:
            self.assertEqual('Not implemented for this Runner', str(ce))


if __name__ == '__main__':
    sys.exit(unittest.main())
