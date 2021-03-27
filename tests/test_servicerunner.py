#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_servicerunner
----------------------------------

Tests for `cdapsutil.runner` module.
"""

import os
import stat
import sys
import tempfile
import shutil
import uuid
import unittest

import requests
import requests_mock

import cdapsutil
from cdapsutil.runner import ServiceRunner
from cdapsutil.exceptions import CommunityDetectionError


class TestServiceRunner(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_user_agent_header(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        self.assertEqual({'UserAgent': 'cdapsutil/' +
                                       str(cdapsutil.__version__)},
                          sr._get_user_agent_header())

    def test_get_algorithm_name(self):
        sr = ServiceRunner()
        self.assertEqual('', sr.get_algorithm_name())

    def test_get_docker_image(self):
        sr = ServiceRunner()
        self.assertEqual('', sr.get_docker_image())

    def test_get_algorithms_server_error(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            with requests_mock.Mocker() as m:
                m.get('http://foo/algorithms', status_code=500,
                      text='error')
                sr.get_algorithms()
                self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Received 500 HTTP response status code : error',
                             str(ce))

    def test_get_algorithms_http_error(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            with requests_mock.Mocker() as m:
                m.get('http://foo/algorithms',
                      exc=requests.exceptions.HTTPError('anerror'))
                sr.get_algorithms()
                self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Received HTTPError getting '
                             'algorithms : anerror',
                             str(ce))

    def test_get_algorithms_no_json(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            with requests_mock.Mocker() as m:
                m.get('http://foo/algorithms',
                      status_code=200)
                sr.get_algorithms()
                self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertTrue('Error result not in JSON format : ' in str(ce))

    def test_get_algorithms_success(self):
        sr = ServiceRunner(service_endpoint='http://foo')

        with requests_mock.Mocker() as m:
            m.get('http://foo/algorithms',
                  status_code=200, json={'hi': 'there'})
            res = sr.get_algorithms()
            self.assertEqual({'hi': 'there'}, res)

    def test_wait_for_task_to_complete_none_for_taskid(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            sr.wait_for_task_to_complete(None)
            self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Task id is empty string or None',
                             str(ce))

    def test_wait_for_task_to_complete_immediately_done(self):
        sr = ServiceRunner(service_endpoint='http://foo')

        with requests_mock.Mocker() as m:
            m.get('http://foo/taskid/status', status_code=200,
                  json={'progress': 100})
            res = sr.wait_for_task_to_complete('taskid', poll_interval=0)
            self.assertEqual({'progress': 100}, res)

    def test_wait_for_task_to_complete_retry_count_exceeded(self):
        sr = ServiceRunner(service_endpoint='http://foo')

        with requests_mock.Mocker() as m:
            m.get('http://foo/taskid/status',
                  [{'status_code': 500},
                   {'status_code': 200, 'json': {'foo': None}},
                   {'exc': requests.exceptions.HTTPError('error')}])
            try:
                sr.wait_for_task_to_complete('taskid', poll_interval=0,
                                             max_retries=3)
                self.fail('Expected CommunityDetectionError')
            except CommunityDetectionError as ce:
                self.assertEqual('Max retry count 3 exceeded',
                                 str(ce))

    def test_wait_for_task_to_complete_consecutive_error_exceeded(self):
        sr = ServiceRunner(service_endpoint='http://foo')

        with requests_mock.Mocker() as m:
            m.get('http://foo/taskid/status',
                  [{'status_code': 500},
                   {'status_code': 200, 'json': {'foo': None}},
                   {'status_code': 200, 'json': {'progress': 50}},
                   {'status_code': 500},
                   {'status_code': 410},
                   {'exc': requests.exceptions.HTTPError('error')}])
            try:
                sr.wait_for_task_to_complete('taskid', poll_interval=0,
                                             consecutive_fail_retry=2)
                self.fail('Expected CommunityDetectionError')
            except CommunityDetectionError as ce:
                self.assertEqual('Received 3 consecutive errors',
                                 str(ce))

    def test_get_result_none_for_task_id(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            sr.get_result(None)
            self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Task id is empty string or None',
                             str(ce))

    def test_get_result_success(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        with requests_mock.Mocker() as m:
            m.get('http://foo/taskid', status_code=200,
                  json={'progress': 100})
            res = sr.get_result('taskid')
            self.assertEqual({'progress': 100}, res)

    def test_get_result_error_html_code_no_json_or_text(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        with requests_mock.Mocker() as m:
            m.get('http://foo/taskid', status_code=500)
            try:
                sr.get_result('taskid')
                self.fail('Expected CommunityDetectionError')
            except CommunityDetectionError as ce:
                self.assertEqual('Received 500 HTTP response status code : ', str(ce))

    def test_get_result_error_html_code_with_text(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        with requests_mock.Mocker() as m:
            m.get('http://foo/taskid', status_code=503,
                  text='some error')
            try:
                sr.get_result('taskid')
                self.fail('Expected CommunityDetectionError')
            except CommunityDetectionError as ce:
                self.assertEqual('Received 503 HTTP response status code : some error', str(ce))

    def test_submit_None_for_algorithm(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            sr.submit(algorithm=None)
            self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Algorithm is empty string or None',
                             str(ce))

    def test_submit_raises_httperror(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            with requests_mock.Mocker() as m:
                m.post('http://foo',
                       exc=requests.exceptions.HTTPError('some error'))
                sr.submit(algorithm='myalgo', data={'hi': 'there'})
                self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Received HTTPError submitting myalgo with '
                             'parameters None : some error', str(ce))

    def test_submit_raises_invalidstatuscode(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            with requests_mock.Mocker() as m:
                m.post('http://foo',
                       status_code=500)
                sr.submit(algorithm='myalgo', data={'hi': 'there'})
                self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertEqual('Received unexpected HTTP response status code: '
                             '500 from request: ', str(ce))

    def test_submit_nojson(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        try:
            with requests_mock.Mocker() as m:
                m.post('http://foo',
                       status_code=202)
                sr.submit(algorithm='myalgo', data={'hi': 'there'})
                self.fail('Expected CommunityDetectionError')
        except CommunityDetectionError as ce:
            self.assertTrue('Unable to parse result from submit: '
                            'Expecting' in str(ce))

    def test_submit_success(self):
        sr = ServiceRunner(service_endpoint='http://foo')
        with requests_mock.Mocker() as m:
            m.post('http://foo',
                   status_code=202, json={'id': 'taskid'})
            res = sr.submit(algorithm='myalgo', data={'hi': 'there'})
            self.assertEqual({'id': 'taskid'}, res)


if __name__ == '__main__':
    sys.exit(unittest.main())
