# -*- coding: utf-8 -*-

import os
import logging
import json
import math
from json.decoder import JSONDecodeError
import ndex2
from ndex2.nice_cx_network import NiceCXNetwork
from cdapsutil.runner import DockerRunner
from cdapsutil.runner import ServiceRunner
from cdapsutil.exceptions import CommunityDetectionError

LOGGER = logging.getLogger(__name__)


REST_ENDPOINT = 'http://cdservice.cytoscape.org/cd/' \
                       'communitydetection/v1'
"""
Default REST endpoint
"""


class CommunityDetection(object):
    """
    Runs Community Detection Algorithms packaged as
    `Docker <https://www.docker.com/>`_ containers built for
    `CDAPS service <https://cdaps.readthedocs.io/>`_ locally or remotely

    """

    def __init__(self,
                 service=ServiceRunner(service_endpoint=REST_ENDPOINT),
                 docker=DockerRunner()):
        """
        Constructor

        :param service: Object used to run CommunityDetection via
                        CDAPS REST service
        :type service: :py:class:`~cdapsutil.runner.ServiceRunner`
        :param docker: Object used to run CommunityDetection via locally
                       installed Docker
        :type docker: :py:class:`~cdapsutil.runner.DockerRunner`
        :raises CommunityDetectionError: If `service` or `docker` is ``None``
        """
        if docker is None:
            raise CommunityDetectionError('docker is None')
        self._docker = docker

        if service is None:
            raise CommunityDetectionError('service is None')
        self._service = service

    def run_community_detection(self, net_cx, algo_or_docker=None,
                                temp_dir=None,
                                arguments=None,
                                via_service=False,
                                max_retries=600,
                                poll_interval=1):
        """
        Runs community detection on **net_cx** network. The result
        is a new hierarchy network.

        This method can run the community detection algorithm denoted
        by the **algo_or_docker** parameter via two ways.

        If **via_service** parameter is ``True`` then the algorithm is
        run remotely on `CDAPS REST service <https://cdaps.readthedocs.io/>`_
        denoted in the constructor. In this case **algo_or_docker**
        should be set to the name of the algorithm to run.

        If **via_service** parameter is ``False`` or ``None`` then
        algorithm is run via `Docker <https://www.docker.com/>`_
        locally. In this case **algo_or_docker** parameter should be set to
        the name of the `Docker <https://www.docker.com/>`_ image.

        :param net_cx: network to run community detection on
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param algo_or_docker: name of algorithm if **via_service** parameter
                               is ``True``, otherwise name of Docker image
                               (ie ``coleslawndex/cdhidef:0.1.0``)
        :type algo_or_docker: str
        :param temp_dir: path to temporary directory, which if running
                         locally via `Docker <https://www.docker.com/>`_
                         must be a path that can be seen by the
                         `Docker <https://www.docker.com/>`_ with
                         ``-v`` parameter
        :type temp_dir: str
        :param arguments: flags to pass to algorithm. Should be in format
                          where key is parameter name and value is parameter
                          value. For flags this value should be ``None``
        :type arguments: dict
        :param via_service: If ``True`` algorithm will be run on
                            remote service. Otherwise algorithm will be
                            run locally utilizing local install of
                            `Docker <https://www.docker.com/>`_
        :type via_service: bool
        :param max_retries: Number of times to check for task completion when
                            `via_service` is set to ``True``
        :type max_retries: int
        :param poll_interval: Time to wait in seconds between checks for task
                              completion when `via_service` is set to ``True``
        :type poll_interval: int
        :raises CommunityDetectionError: If there was an error running the
                                         algorithm
        :return: Hierarchy network generated
        :rtype: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        """
        if via_service is None or via_service is False:
            edgelist = CommunityDetection._write_edge_list(net_cx, temp_dir)
            full_args = {os.path.abspath(edgelist): None}

            if arguments is not None:
                full_args.update(arguments)
            algo_name = algo_or_docker[algo_or_docker.index('/') + 1:]
            e_code, out, err = self._docker.run(algorithm=algo_or_docker,
                                                arguments=full_args,
                                                temp_dir=temp_dir)
            if e_code != 0:
                raise CommunityDetectionError('Non-zero exit code from '
                                              'algorithm: ' +
                                              str(e_code) + ' : ' + str(err) +
                                              ' : ' + str(out))
        else:
            edgelist = CommunityDetection._get_edge_list(net_cx)
            algo_name = algo_or_docker
            task_id = self._service.submit(algorithm=algo_name, data=edgelist,
                                           arguments=arguments)['id']
            LOGGER.debug('Waiting for task ' + str(task_id) + ' to complete')
            self._service.wait_for_task_to_complete(task_id,
                                                    max_retries=max_retries,
                                                    poll_interval=poll_interval)
            resp_as_json = self._service.get_result(task_id)
            if resp_as_json['status'] != 'complete':
                CommunityDetectionError('Error running algorithm. '
                                        'Raw JSON: ' +
                                        str(resp_as_json))
            out = resp_as_json['result']
        LOGGER.debug(str(task_id) + ' completed. Generating hierarchy')
        clusters_dict,\
            children_dict,\
            res_as_json = self.\
            _derive_hierarchy_from_result(result=out)

        flattened_dict = \
            self._flatten_children_dict(clusters_dict=clusters_dict,
                                        children_dict=children_dict)

        hier_net = self._create_network(docker_image=algo_or_docker,
                                        algo_name=algo_name,
                                        net_cx=net_cx,
                                        cluster_members=flattened_dict,
                                        clusters_dict=clusters_dict,
                                        res_as_json=res_as_json,
                                        arguments=arguments)
        CommunityDetection._apply_style(hier_net)

        return hier_net

    def _create_empty_hierarchy_network(self, docker_image=None,
                                        algo_name=None,
                                        source_network=None,
                                        arguments=None):
        """
        Creates an empty hierarchy network with appropriate network attributes

        :param docker_image: docker image, used to set value
                             `prov:wasGeneratedBy`
                             network attribute
        :type docker_image: str
        :param algo_name: name of algorithm, used in `description` network
                          attribute
        :type algo_name: str
        :param source_network: source network, name is used to set name of
                               network returned by this method
        :type source_network: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :return: empty network except for network attributes
        :rtype: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        """

        cust_params = ''
        if arguments is not None:
            for a in arguments.keys():
                cust_params += a + ' '
                if arguments[a] is not None:
                    cust_params += arguments[a] + ' '

        hier_net = NiceCXNetwork()
        hier_net.set_name(algo_name + '_(none)_' + source_network.get_name())
        hier_net.set_network_attribute('__CD_OriginalNetwork',
                                       values='0', type='long')
        hier_net.set_network_attribute('description',
                                       values='Original network: ' +
                                              source_network.get_name() +
                                              '\n ' +
                                              'Algorithm used for '
                                              'community detection: ' +
                                              algo_name + '\n ' +
                                              'Edge table column used '
                                              'as weight: (none)\n ' +
                                              'CustomParameters: {' +
                                              cust_params + '}')
        hier_net.set_network_attribute('prov:wasDerivedFrom',
                                       values=source_network.get_name())
        hier_net.set_network_attribute('prov:wasGeneratedBy',
                                       values='run_community'
                                              'detection.py '
                                              'Docker image: ' + docker_image)
        return hier_net

    def _flatten_children_dict(self, clusters_dict=None, children_dict=None):
        """
        An issue with the children_dict is that only immediate members of that
        cluster are listed. This method examines all the children clusters
        and adds their members to each cluster.

        :param clusters_dict: dictionary where key is cluster node id and value
                              is a set of direct children clusters
        :param children_dict: dictionary where key is parent node id and
                              value is a set of children node ids
        :type children_dict: dict
        :return: dictionary where key is cluster node id and value is set of
                 all members for that cluster which includes members of any
                 children clusters
        :rtype: dict
        """
        flattened_dict = dict()

        # iterate through all the clusters
        for key in sorted(clusters_dict.keys()):
            flattened_dict[key] = set()
            subclusters_to_check = set()

            # for this cluster add all immediate children to
            # subclusters_to_check
            subclusters_to_check.update(clusters_dict[key])

            # add any immediate children members to flatten_dict
            if key in children_dict and children_dict[key] is not None:
                flattened_dict[key].update(children_dict[key])

            # this loop iterates over the children clusters in
            # subclusters_to_check adding any additional children
            # clusters encountered. At the same time children members
            # are added to the flattend_dict[key] until no more
            # clusters are found
            while len(subclusters_to_check) > 0:
                subsubcluster = subclusters_to_check.pop()
                if subsubcluster in children_dict:
                    val = children_dict[subsubcluster]
                    if val is not None:
                        flattened_dict[key].update(val)
                if subsubcluster is not None and subsubcluster in clusters_dict:
                    subclusters_to_check.update(clusters_dict[subsubcluster])

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('Flattened dict size: ' + str(len(flattened_dict)))
            for key in flattened_dict:
                LOGGER.debug(str(key) + ' => ' + str(flattened_dict[key]))
        return flattened_dict

    def _derive_hierarchy_from_result(self, result=None):
        """
        Given result output in either old or new result format
        this method creates two dictionaries. One holding relationship
        of parent to children nodes and the other to nodes to member nodes

        :param result:
        :return: (map of cluster node id to set of children node ids,
                  map of cluster node id to set of member node ids)
        :rtype: tuple
        """
        if result is None:
            raise CommunityDetectionError('Result is None')

        if isinstance(result, dict):
            res_as_json = result
        else:
            # TODO rework this cause result can be str or bytes
            try:
                res_as_json = json.loads(result)
            except JSONDecodeError as je:
                LOGGER.debug('caught jsondecode error: ' + str(je))
                if isinstance(result, str):
                    res_as_json = {'communityDetectionResult': result}
                else:
                    res_as_json = {'communityDetectionResult': result.decode('utf-8')}
        hier_list = res_as_json['communityDetectionResult']

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(str(hier_list))

        clusters_dict = dict()
        children_dict = dict()
        for line in hier_list.split(';'):
            splitline = line.split(',')
            if len(splitline) != 3:
                continue
            source = int(splitline[0])
            target = int(splitline[1])
            relationship = splitline[2]
            if relationship[2] == 'm':
                if source not in clusters_dict:
                    clusters_dict[source] = set()
                if source not in children_dict:
                    children_dict[source] = set()
                children_dict[source].add(target)
            else:
                if source not in clusters_dict:
                    clusters_dict[source] = set()
                clusters_dict[source].add(target)

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('clusters_dict size: ' + str(len(clusters_dict)))
            LOGGER.debug('children dict size: ' + str(len(children_dict)))
            clust_keys = sorted(clusters_dict.keys())
            for key in sorted(children_dict.keys()):
                if key not in clust_keys:
                    LOGGER.debug(str(key) + ' not in children')
            for key in sorted(clusters_dict.keys()):
                LOGGER.debug('Cluster ' + str(key) + ' => ' + str(clusters_dict[key]))
                if key in children_dict:
                    LOGGER.debug('\tChildren ' + str(children_dict[key]))
                else:
                    LOGGER.debug('\tChildren => None')

        return clusters_dict, children_dict, res_as_json

    def _create_network(self, docker_image=None,
                        algo_name=None,
                        net_cx=None,
                        cluster_members=None,
                        clusters_dict=None,
                        res_as_json=None,
                        arguments=None):
        """
        Takes `result` output from docker and source network `net_cx` to
        create a complete hierarchy that is similar to result from
        CDAPS Cytoscape App

        :param docker_image: docker image
        :type docker_image: str
        :param algo_name: name of algorithm
        :type algo_name: str
        :param net_cx: source parent network
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param result: JSON data of result from running docker image
        :type result: str
        :param arguments: user arguments passed to docker
        :type arguments: list
        :return: complete hierarchy network that is similar to the one
                 generated in CDAPS Cytoscape App
        :rtype: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        """

        node_dict = CommunityDetection._get_node_dictionary(net_cx)
        hier_net = self._create_empty_hierarchy_network(docker_image=docker_image,
                                                        algo_name=algo_name,
                                                        source_network=net_cx,
                                                        arguments=arguments)

        # this is a map of cluster id => node id in hierarchy network
        cluster_nodes_dict = dict()

        # create nodes for clusters
        for source in clusters_dict:
            if source not in cluster_nodes_dict:
                node_id = hier_net.create_node('C' + str(source))
                cluster_nodes_dict[source] = node_id
            for target in clusters_dict[source]:
                if target not in cluster_nodes_dict:
                    node_id = hier_net.create_node('C' + str(target))
                    cluster_nodes_dict[target] = node_id
                # create edge connecting clusters
                hier_net.create_edge(edge_source=cluster_nodes_dict[source],
                                     edge_target=cluster_nodes_dict[target])

        # create dict where key is cluster node id and value
        # is a set of member node names storing them in updated_nodes_dict
        updated_nodes_dict = dict()
        for node in cluster_members.keys():
            mem_set = set()
            for cnode in cluster_members[node]:
                mem_set.add(node_dict[cnode])
            updated_nodes_dict[cluster_nodes_dict[node]] = mem_set

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug('updated_nodes_dict: ' + str(updated_nodes_dict))

        # iterate through all the nodes in the hierarchy and add the member
        # nodes along with necessary statistics
        for node_id, node_obj in hier_net.get_nodes():
            if node_id in updated_nodes_dict:
                member_list_size = len(updated_nodes_dict[node_id])
                member_list = ' '.join(updated_nodes_dict[node_id])
                member_list_logsize = math.log(member_list_size) / math.log(2)
            else:
                member_list_size = 0
                member_list = ''
                member_list_logsize = 0

            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_MemberList',
                                        values=member_list)
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_MemberList_Size',
                                        values=str(member_list_size),
                                        type='integer')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_Labeled', values=str(False),
                                        type='boolean')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_MemberList_LogSize',
                                        values=str(member_list_logsize),
                                        type='double')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_CommunityName', values='')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_AnnotatedMembers', values='')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_AnnotatedMembers_Size',
                                        values=str(0),
                                        type='integer')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_AnnotatedMembers_Overlap',
                                        values=str(0.0),
                                        type='double')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_AnnotatedMembers_Pvalue',
                                        values=str(0.0),
                                        type='double')

        # using raw JSON output add any custom annotations.
        # Currently used by HiDeF
        self._add_custom_annotations(net_cx=hier_net,
                                     nodes_dict=cluster_nodes_dict,
                                     res_as_json=res_as_json)
        return hier_net

    def _add_custom_annotations(self, net_cx=None,
                                nodes_dict=None,
                                res_as_json=None):
        """
        Adds any custom annotations to nodes from community
        detection result which would be stored under 'nodeAttributesAsCX2'
        and 'nodes' under 'result' of json

        :param net_cx:
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param res_as_json:
        :type res_as_json: dict
        :return: None
        """
        if 'nodeAttributesAsCX2' not in res_as_json:
            return
        n_a_d = dict()
        attr_dec = res_as_json['nodeAttributesAsCX2']['attributeDeclarations']
        for entry in attr_dec:
            if 'nodes' not in entry:
                continue
            for key in entry['nodes'].keys():
                n_a_d[entry['nodes'][key]['a']] = (key,
                                                   entry['nodes'][key]['v'],
                                                   entry['nodes'][key]['d'])

        for entry in res_as_json['nodeAttributesAsCX2']['nodes']:
            node_id = nodes_dict[entry['id']]
            for n_alias in entry['v'].keys():
                attr_name, attr_value, attr_type = n_a_d[n_alias]
                net_cx.add_node_attribute(property_of=node_id,
                                          name=attr_name,
                                          values=str(entry['v'][n_alias]),
                                          type=attr_type)

    @staticmethod
    def _write_edge_list(net_cx, tempdir):
        """
        Writes edges from 'net_cx' network to file named 'input.edgelist'
        in 'tempdir' as a tab delimited file of source target

        :param net_cx: Network to extract edges from
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param tempdir: directory to write edge list to
        :type tempdir: str
        :return: path to edgelist file
        :rtype: str
        """
        edgelist = os.path.join(tempdir, 'input.edgelist')
        with open(edgelist, 'w') as f:
            for edge_id, edge_obj in net_cx.get_edges():
                f.write(str(edge_obj['s']) + '\t' + str(edge_obj['t']) + '\n')
        return edgelist

    @staticmethod
    def _get_edge_list(net_cx):
        """
        Writes edges from 'net_cx' network to file named 'input.edgelist'
        in 'tempdir' as a tab delimited file of source target

        :param net_cx: Network to extract edges from
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param tempdir: directory to write edge list to
        :type tempdir: str
        :return: path to edgelist file
        :rtype: str
        """
        edgelist = []

        for edge_id, edge_obj in net_cx.get_edges():
            edgelist.append(str(edge_obj['s']) + '\t' + str(edge_obj['t']) + '\n')
        return ''.join(edgelist)

    @staticmethod
    def _get_node_dictionary(net_cx):
        """
        Creates a dictionary from 'net_cx' passed in where
        key is id of node and value is name of node

        :param net_cx:
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :return: { 'NODEID': NODE_NAME }
        :rtype: dict
        """
        node_id_set = set()
        node_dict = dict()
        for node_id, node_obj in net_cx.get_nodes():
            node_dict[node_id] = node_obj['n']
            node_id_set.add(node_id)
        return node_dict

    @staticmethod
    def _apply_style(net_cx,
                     style='default_style.cx'):
        """
        Applies default hierarchy style to network

        :param net_cx: network to update style on
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param style: path to CX file with style to use
        :type style: str
        :return: None
        """
        if os.path.isfile(style):
            style_file = style
        else:
            style_file = os.path.join(os.path.dirname(__file__), style)
        style_cx = ndex2.create_nice_cx_from_file(style_file)
        net_cx.apply_style_from_network(style_cx)
