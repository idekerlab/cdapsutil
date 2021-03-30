# -*- coding: utf-8 -*-

import os
import logging
import json
import math
from json.decoder import JSONDecodeError
import ndex2
from ndex2.nice_cx_network import NiceCXNetwork
import cdapsutil
from cdapsutil.runner import ServiceRunner
from cdapsutil.exceptions import CommunityDetectionError

LOGGER = logging.getLogger(__name__)


class CommunityDetection(object):
    """
    Runs Community Detection Algorithms packaged as
    `Docker <https://www.docker.com/>`_ containers built for
    `CDAPS service <https://cdaps.readthedocs.io/>`_ via
    :py:class:`~cdapsutil.runner.Runner`

    :param runner: Object used to run CommunityDetection algorithm.
    :type runner: :py:class:`~cdapsutil.runner.Runner`
    :raises CommunityDetectionError: If `runner` is ``None``
    """

    def __init__(self,
                 runner=ServiceRunner()):
        """
        Constructor. See class description for usage

        """
        if runner is None:
            raise CommunityDetectionError('runner is None')
        self._runner = runner

    def run_community_detection(self, net_cx, algorithm=None,
                                temp_dir=None,
                                arguments=None,
                                weight_col=None,
                                default_weight=None):
        """
        Generates hierarchy network by running community detection algorithm
        specified by **algorithm** parameter on **net_cx** network.

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
        :param weight_col: Name of column containing weights, Set to ``None``
                           for unweighted
        :type weight_col: str
        :param default_weight: Default weight value for edges where no weight
                               was found. Only applicable if `weight_col`
                               parameter is set. **WARNING** This not
                               yet supported and will raise a
                               :py:class:`~cdapsutil.exceptions.CommunityDetectionError`
        :type default_weight: float
        :raises CommunityDetectionError: If there was an error running the
                                         algorithm or if `weight_col` parameter
                                         is set which is not yet supported
        :return: Hierarchy network
        :rtype: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        """
        if weight_col is not None:
            raise CommunityDetectionError('Weighted graphs are not yet '
                                          'supported')

        e_code, out, err = self._runner.run(net_cx, algorithm=algorithm,
                                            arguments=arguments,
                                            temp_dir=temp_dir)
        if e_code != 0:
            raise CommunityDetectionError('Non-zero exit code from '
                                          'algorithm: ' +
                                          str(e_code) + ' : ' + str(err) +
                                          ' : ' + str(out))

        LOGGER.debug('Task completed. Generating hierarchy')
        clusters_dict,\
            children_dict,\
            res_as_json = self.\
            _derive_hierarchy_from_result(result=out)

        flattened_dict = \
            self._flatten_children_dict(clusters_dict=clusters_dict,
                                        children_dict=children_dict)

        hier_net = self._create_network(docker_image=self._runner.get_docker_image(),
                                        algo_name=self._runner.get_algorithm_name(),
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

        :param docker_image: Docker image, used to set value
                             `prov:wasGeneratedBy`
                             network attribute
        :type docker_image: str
        :param algo_name: Name of algorithm, used in `description` network
                          attribute
        :type algo_name: str
        :param source_network: Source network, name is used to set name of
                               network returned by this method
        :type source_network: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :return: Empty network except for network attributes
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
                                       values='cdapsutil ' +
                                              cdapsutil.__version__ + ' ' +
                                              'Docker image: ' + docker_image)
        return hier_net

    def _flatten_children_dict(self, clusters_dict=None, children_dict=None):
        """
        An issue with the children_dict is that only immediate members of that
        cluster are listed. This method examines all the children clusters
        and adds their members to each cluster.

        :param clusters_dict: Dictionary where key is cluster node id and value
                              is a set of direct children clusters
        :type clusters_dict: dict
        :param children_dict: Dictionary where key is parent node id and
                              value is a set of children node ids
        :type children_dict: dict
        :return: Dictionary where key is cluster node id and value is set of
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
            try:
                res_as_json = json.loads(result)
            except JSONDecodeError as je:
                LOGGER.debug('caught jsondecode error: ' + str(je))
                if isinstance(result, str):
                    res_as_json = {'communityDetectionResult': result}
                else:
                    res_as_json = {'communityDetectionResult': result.decode('utf-8')}
        if 'communityDetectionResult' in res_as_json:
            hier_list = res_as_json['communityDetectionResult']
        else:
            if 'result' not in res_as_json:
                raise CommunityDetectionError('Expected result key in JSON')
            hier_list = res_as_json['result']

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

        :param docker_image: Docker image
        :type docker_image: str
        :param algo_name: Name of algorithm
        :type algo_name: str
        :param net_cx: Source parent network
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param result: JSON data of result from running docker image
        :type result: str
        :param arguments: User arguments passed to docker
        :type arguments: list
        :return: Complete hierarchy network that is similar to the one
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
                member_list_logsize = round(math.log(member_list_size) / math.log(2), 3)
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

        :param net_cx: Network to update style on
        :type net_cx: :py:class:`ndex2.nice_cx_network.NiceCXNetwork`
        :param style: Path to CX file with style to use
        :type style: str
        :return: None
        """
        if os.path.isfile(style):
            style_file = style
        else:
            style_file = os.path.join(os.path.dirname(__file__), style)
        style_cx = ndex2.create_nice_cx_from_file(style_file)
        net_cx.apply_style_from_network(style_cx)
