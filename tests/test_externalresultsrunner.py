#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_externalresultsrunner
----------------------------------

Tests for `cdapsutil.runner` module.
"""

import os
import sys
import tempfile
import json
import shutil
import unittest

from cdapsutil.runner import ExternalResultsRunner
from cdapsutil.exceptions import CommunityDetectionError


class TestExternalResultsRunner(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def get_test_file(self, file_name):
        return os.path.join(os.path.dirname(__file__), 'data', file_name)

    def test_run_all_parameters_none(self):
        er = ExternalResultsRunner()
        try:
            er.run(None)
            self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Algorithm is None', str(ce))

    def test_algorithm_file_does_not_exist(self):
        er = ExternalResultsRunner()
        temp_dir = tempfile.mkdtemp()
        nonexist_file = os.path.join(temp_dir, 'doesnotexist')
        try:
            er.run(algorithm=nonexist_file)
            self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual(nonexist_file + ' is not a file',
                             str(ce))
        finally:
            shutil.rmtree(temp_dir)

    def test_algorithm_file_is_not_readable(self):
        er = ExternalResultsRunner()
        temp_dir = tempfile.mkdtemp()
        try:
            data_file = os.path.join(temp_dir, 'afile')
            with open(data_file, 'w') as f:
                f.write('hello\n')
                f.flush()
            os.chmod(data_file, 0)
            er.run(algorithm=data_file)
            self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertTrue('Permission denied' in str(ce))
        finally:
            shutil.rmtree(temp_dir)

    def test_algorithm_file_has_invalid_json(self):
        er = ExternalResultsRunner()
        temp_dir = tempfile.mkdtemp()
        try:
            data_file = os.path.join(temp_dir, 'afile')
            with open(data_file, 'w') as f:
                f.write('{hello\n')
                f.flush()
            e_code,\
            result,\
            err = er.run(algorithm=data_file)
            self.assertEqual(0, e_code)
            self.assertEqual('{hello\n', result)
            self.assertEqual(None, err)
        except CommunityDetectionError as ce:
            self.assertTrue('Permission denied' in str(ce))
        finally:
            shutil.rmtree(temp_dir)

    def test_cdhideforiginal(self):
        er = ExternalResultsRunner()
        e_code,\
        result,\
        err = er.run(algorithm=self.get_test_file('cdhidef:0.2.2.out'))

        self.assertEqual(0, e_code)
        jres = json.loads(result)
        self.assertTrue('communityDetectionResult' in jres.keys())
        self.assertTrue('nodeAttributesAsCX2' in jres.keys())
        self.assertEqual(None, err)

    def test_cdhidefbeta(self):
        er = ExternalResultsRunner()
        e_code,\
        result,\
        err = er.run(algorithm=self.get_test_file('cdhidef:1.1.1b1.out'))

        self.assertEqual(0, e_code)
        jres = json.loads(result)
        self.assertTrue('communityDetectionResult' in jres.keys())
        self.assertTrue('nodeAttributesAsCX2' in jres.keys())
        self.assertEqual(None, err)

    def test_cdinfomap(self):
        er = ExternalResultsRunner()
        e_code,\
        result,\
        err = er.run(algorithm=self.get_test_file('cdinfomap:0.1.0.out'))

        self.assertEqual(0, e_code)
        self.assertEqual('790,770,c-c;752,721', result[0:19])
        self.assertEqual(6264, len(result))
        self.assertEqual(None, err)

    def test_cdlouvain(self):
        er = ExternalResultsRunner()
        e_code,\
        result,\
        err = er.run(algorithm=self.get_test_file('cdlouvain:0.2.0.out'))

        self.assertEqual(0, e_code)
        self.assertEqual('740,269,c-m;740,270', result[0:19])
        self.assertEqual(5652, len(result))
        self.assertEqual(None, err)

    def test_cdlouvain(self):
        er = ExternalResultsRunner()
        e_code,\
        result,\
        err = er.run(algorithm=self.get_test_file('cdoslom:0.3.0.out'))

        self.assertEqual(0, e_code)
        self.assertEqual('748,740,c-c;740,296', result[0:19])
        self.assertEqual(6012, len(result))
        self.assertEqual(None, err)

    def test_cdinfomap_json_out_from_service(self):
        er = ExternalResultsRunner()
        e_code, \
        result, \
        err = er.run(algorithm=self.get_test_file('cdinfomap_out.json'))

        self.assertEqual(0, e_code)
        jres = json.loads(result)
        self.assertTrue('id' in jres.keys())
        self.assertTrue('message' in jres.keys())
        self.assertEqual(None, jres['message'])
        self.assertTrue('status' in jres.keys())
        self.assertEqual('complete',jres['status'])
        self.assertEqual(6643, len(result))
        self.assertEqual(None, err)

    def test_cdinfomap_json_out_from_service_with_error(self):

        temp_dir = tempfile.mkdtemp()
        try:
            with open(self.get_test_file('cdinfomap_out.json'), 'r') as f:
                jdata = json.load(f)
            jdata['message'] = 'some error'
            jdata['status'] = 'failed'

            out_file = os.path.join(temp_dir, 'out.json')
            with open(out_file, 'w') as f:
                json.dump(jdata, f)

            er = ExternalResultsRunner()
            e_code, \
            result, \
            err = er.run(algorithm=out_file)

            self.assertEqual(1, e_code)
            jres = json.loads(result)
            self.assertTrue('id' in jres.keys())
            self.assertTrue('message' in jres.keys())
            self.assertEqual('some error', jres['message'])
            self.assertTrue('status' in jres.keys())
            self.assertEqual('failed', jres['status'])
            self.assertEqual(6625, len(result))
            self.assertEqual('some error', err)
        finally:
            shutil.rmtree(temp_dir)




if __name__ == '__main__':
    sys.exit(unittest.main())
