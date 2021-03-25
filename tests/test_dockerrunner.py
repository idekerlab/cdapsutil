#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_dockerrunner
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
from cdapsutil.runner import DockerRunner
from cdapsutil.exceptions import CommunityDetectionError


class TestDockerRunner(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def write_mock_docker(self, outfile=None,
                          exit_code=0):
        with open(outfile, 'w') as f:
            f.write('#!/usr/bin/env python\n')
            f.write('import sys\n\n')
            f.write('sys.stdout.write(str(" ".join(sys.argv[1:])))\n')
            f.write('sys.stderr.write("stderroutput")\n')
            f.write('sys.exit(' + str(exit_code) + ')\n')

        os.chmod(outfile, stat.S_IRWXU)

    def test_run_all_parameters_none(self):
        dr = DockerRunner()
        try:
            dr.run(None)
            self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Algorithm is None', str(ce))

    def test_run_with_mock_docker(self):
        temp_dir = tempfile.mkdtemp()
        try:
            docker = os.path.join(temp_dir, 'docker')
            self.write_mock_docker(outfile=docker, exit_code=0)
            dr = DockerRunner(binary_path=docker)
            net_cx = ndex2.nice_cx_network.NiceCXNetwork()
            e_code, out, err = dr.run(net_cx, algorithm='myalgo',
                                      temp_dir=temp_dir)
            self.assertEqual(0, e_code)
            self.assertEqual(b'stderroutput', err)
            res_str = 'run --rm -v ' + temp_dir + ':' + temp_dir + ' myalgo ' +\
                os.path.join(temp_dir, 'input.edgelist')
            print('result: ' + str(out))
            print('res_str: ' + res_str)
            self.assertEqual(res_str.encode(), out)

        finally:
            shutil.rmtree(temp_dir)

    def test_run_with_mock_docker_with_args(self):
        temp_dir = tempfile.mkdtemp()
        try:
            docker = os.path.join(temp_dir, 'docker')
            self.write_mock_docker(outfile=docker, exit_code=0)
            dr = DockerRunner(binary_path=docker)
            myargs = {'--blah': None,
                      '--val': 2,
                      '--foo': 'hi'}
            net_cx = ndex2.nice_cx_network.NiceCXNetwork()
            e_code, out, err = dr.run(net_cx, algorithm='myalgo',
                                      temp_dir=temp_dir,
                                      arguments=myargs)
            self.assertEqual(0, e_code)
            self.assertEqual(b'stderroutput', err)
            out_str = out.decode()
            self.assertTrue('run --rm -v ' + temp_dir + ':' +
                            temp_dir + ' myalgo' in out_str)
            self.assertTrue('--blah' in out_str)
            self.assertTrue('--val 2' in out_str)
            self.assertTrue('--foo hi' in out_str)
        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    sys.exit(unittest.main())
