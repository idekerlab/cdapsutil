# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import json
import math
import time
from ndex2.nice_cx_network import NiceCXNetwork

LOGGER = logging.getLogger(__name__)


def cur_time_in_seconds():
    return int(round(time.time()))


class CommunityDetectionError(Exception):
    """
    Base class for CommunityDetection Errors
    """
    pass


class DockerRunner(object):
    """
    Wrapper to run Docker containers
    """
    def __init__(self):
        """
        Constructor
        """
        pass

    def run_docker(self, docker_image=None, arguments=None,
                   temp_dir=None):
        """
        Runs docker command returning a tuple
        with error code, standard out and standard error

        :param docker_image: docker image to run
        :type docker_image: str
        :param arguments: list of arguments
        :type arguments: list
        :param temp_dir: temporary directory where docker can be run
                         this should be a directory that docker can
                         access when `-v X:X` flag is added to docker
                         command
        :type temp_dir: str
        :return:
        """
        full_args = ['docker', 'run',
                     '--rm', '-v',
                     temp_dir + ':' +
                     temp_dir,
                     docker_image]
        full_args.extend(arguments)
        start_time = cur_time_in_seconds()
        try:
            return self._run_docker_cmd(full_args)
        finally:
            LOGGER.debug('Running ' +
                         ' '.join(full_args) +
                         ' took ' +
                         str(cur_time_in_seconds() - start_time) +
                         ' seconds')

    def _run_docker_cmd(self, cmd):
        """
        Runs docker

        :param cmd_to_run: command to run as list
        :return:
        """

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        out, err = p.communicate()

        return p.returncode, out, err


class CommunityDetection(object):
    """
    Runs Community Detection Algorithms packaged as
    Docker containers built for CDAPS service

    """
    def __init__(self):
        """
        Constructor
        """
        self._docker = DockerRunner()

    def set_alternate_docker_runner(self, docker_runner):
        """

        :param docker_runner:
        :return:
        """
        self._docker = docker_runner

    def run_community_detection(self, net_cx, docker_image=None,
                                temp_dir=None,
                                arguments=None):
        """

        :param net_cx:
        :param docker_image:
        :param temp_dir:
        :return:
        """
        edgelist = CommunityDetection.write_edge_list(net_cx, temp_dir)
        full_args = [os.path.abspath(edgelist)]

        if arguments is not None:
            full_args.extend(arguments)

        e_code, out, err = self._docker.run_docker(docker_image=docker_image,
                                                   arguments=full_args,
                                                   temp_dir=temp_dir)

        algo_name = docker_image[docker_image.index('/') + 1:]

        hier_net = self.create_network_from_result(docker_image=docker_image,
                                                   algo_name=algo_name,
                                                   net_cx=net_cx, result=out,
                                                   arguments=arguments)

        return hier_net

    def create_hierarchy_network(self, docker_image=None,
                                 algo_name=None,
                                 source_network=None,
                                 arguments=None):
        """

        :param docker_image:
        :param algo_name:
        :param source_network:
        :return:
        """

        if arguments is None:
            cust_params = ''
        else:
            cust_params = ' '.join(arguments)

        hier_net = NiceCXNetwork()
        hier_net.set_name(algo_name + '_(none)_' + source_network.get_name())
        hier_net.set_network_attribute('__CD_OriginalNetwork',
                                       values=0, type='long')
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

    def create_network_from_result(self, docker_image=None,
                                   algo_name=None,
                                   net_cx=None,
                                   result=None,
                                   arguments=None):
        """

        :param docker_image:
        :param algo_name:
        :param net_cx:
        :param result:
        :return:
        """
        res_as_json = json.loads(result)
        node_dict = CommunityDetection.get_node_dictionary(net_cx)
        hier_list = res_as_json['communityDetectionResult']
        cluster_genes_dict = dict()
        hier_net = self.create_hierarchy_network(docker_image=docker_image,
                                                 algo_name=algo_name,
                                                 source_network=net_cx,
                                                 arguments=arguments)
        cluster_nodes_dict = dict()
        for line in hier_list.split(';'):
            splitline = line.split(',')
            if len(splitline) != 3:
                continue
            source = int(splitline[0])
            target = int(splitline[1])
            relationship = splitline[2]
            if relationship[2] == 'm':
                if source not in cluster_genes_dict:
                    cluster_genes_dict[source] = []
                cluster_genes_dict[source].append(node_dict[target])
            else:
                if source not in cluster_nodes_dict:
                    node_id = hier_net.create_node('C' + str(source))
                    cluster_nodes_dict[source] = node_id
                if target not in cluster_nodes_dict:
                    node_id = hier_net.create_node('C' + str(target))
                    cluster_nodes_dict[target] = node_id
                hier_net.create_edge(edge_source=cluster_nodes_dict[target],
                                     edge_target=cluster_nodes_dict[source])

        updated_nodes_dict = dict()
        for node in cluster_genes_dict.keys():
            updated_nodes_dict[cluster_nodes_dict[node]] = cluster_genes_dict[node]

        for node_id, node_obj in hier_net.get_nodes():
            if node_id in updated_nodes_dict:
                member_list_size = len(updated_nodes_dict[node_id])
                member_list = ' '.join(updated_nodes_dict[node_id])
            else:
                member_list_size = 0
                member_list = ''
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_MemberList',
                                        values=member_list)
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_MemberList_Size',
                                        values=member_list_size,
                                        type='integer')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_Labeled', values=False,
                                        type='boolean')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_MemberList_LogSize',
                                        values=math.log(member_list_size) / math.log(2),
                                        type='double')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_CommunityName', values='')
            hier_net.add_node_attribute(property_of=node_id,
                                        name='CD_AnnotatedMembers_Overlap', values=0.0,
                                        type='double')

        return hier_net


    @staticmethod
    def write_edge_list(net_cx, tempdir):
        """

        :param net_cx:
        :param tempdir:
        :return:
        """
        edgelist = os.path.join(tempdir, 'input.edgelist')
        with open(edgelist, 'w') as f:
            for edge_id, edge_obj in net_cx.get_edges():
                f.write(str(edge_obj['s']) + '\t' + str(edge_obj['t']) + '\n')
        return edgelist

    @staticmethod
    def get_node_dictionary(net_cx):
        """

        :param net_cx:
        :return:
        """
        node_dict = dict()
        for node_id, node_obj in net_cx.get_nodes():
            node_dict[node_id] = node_obj['n']
        return node_dict
