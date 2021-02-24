# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import json
import math
import time
import tempfile
import shutil
from multiprocessing import Pool
import ndex2
from ndex2.nice_cx_network import NiceCXNetwork
from tqdm import tqdm


LOGGER = logging.getLogger(__name__)


def cur_time_in_seconds():
    return int(round(time.time()))


def run_functional_enrichment_docker(docker_dict):
    """
    Function that runs docker dumping results to
    file path specified by docker_dict['outfile']

    {'index': counter,
     'node_id': node_id,
     'outfile': <output file, must be in temp_dir>,
     'image': <docker_image>,
     'arguments': <list of arguments>,
     'temp_dir': <temp directory where input data resides and output will be written>,
     'docker_runner': <instance of DockerRunner class>}

    :param docker_dict: {'outfile': <PATH WHERE OUTPUT RESULT SHOULD BE WRITTEN>}
    :type docker_dict: dict
    :return: None

    """
    start_time = cur_time_in_seconds()
    e_code, out, err = docker_dict['docker_runner'].run_docker(docker_image=docker_dict['image'],
                                                               temp_dir=docker_dict['temp_dir'],
                                                               arguments=docker_dict['arguments'])
    res = dict()
    res['e_code'] = e_code
    res['out'] = out.decode('utf-8')
    res['err'] = err.decode('utf-8')
    res['elapsed_time'] = cur_time_in_seconds() - start_time
    with open(docker_dict['outfile'], 'w') as f:
        json.dump(res, f)


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
        :param res_as_json:
        :return:
        """
        if 'nodeAttributesAsCX2' not in res_as_json:
            return
        node_alias_dict = dict()
        for entry in res_as_json['nodeAttributesAsCX2']['attributeDeclarations']:
            if 'nodes' in entry:
                for key in entry['nodes'].keys():
                    node_alias_dict[entry['nodes'][key]['a']] = (key,
                                                                 entry['nodes'][key]['v'],
                                                                 entry['nodes'][key]['d'])

        for entry in res_as_json['nodeAttributesAsCX2']['nodes']:
            node_id = nodes_dict[entry['id']]
            for n_alias in entry['v'].keys():
                attr_name, attr_value, attr_type = node_alias_dict[n_alias]
                net_cx.add_node_attribute(property_of=node_id,
                                          name=attr_name,
                                          values=entry['v'][n_alias],
                                          type=attr_type)

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

    @staticmethod
    def apply_style(cx_network,
                    style='default_style.cx'):
        """
        Applies default hierarchy style to network

        :param cx_network:
        :return:
        """
        cx_network.apply_style_from_network(
            ndex2.create_nice_cx_from_file(os.path.join(os.path.dirname(__file__),
                                                        style)))


class FunctionalEnrichment(object):
    """
    Runs Community Detection Functional Enrichment Algorithms
    packaged as Docker containers built for CDAPS service

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

    def _write_gene_list(self, net_cx=None, node_id=None,
                         tempdir=None, counter=None, max_gene_list=500):
        """

        :param net_cx:
        :param tempdir:
        :return:
        """
        outfile = os.path.join(tempdir, str(counter) + '.input')
        with open(outfile, 'w') as f:
            gene_list = self._get_node_memberlist(net_cx, node_id)
            if gene_list is None or len(gene_list) == 0 or len(gene_list) > max_gene_list:
                return None, None
            f.write(','.join(gene_list))
        return outfile, gene_list

    def _get_node_memberlist(self, net_cx, node_id,
                             node_attrib_name='CD_MemberList'):
        """

        :param net_cx:
        :return:
        """
        n_attr = net_cx.get_node_attribute(node_id, node_attrib_name)
        if n_attr is None:
            return None
        return n_attr['v'].split(' ')

    def _annotate_node_with_best_hit(self, docker_image, member_list, net_cx, node_id, hit,
                                     custom_params=None):
        hit_name = '(none)'
        labeled = False
        if hit['name'] is not None and len(hit['name']) > 0:
            hit_name = hit['name']
            labeled = True

        non_members = set()
        if member_list is not None:
            for gene in member_list:
                if gene not in hit['intersections']:
                    non_members.add(gene)
        net_cx.remove_node_attribute(node_id, 'CD_CommunityName')
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_CommunityName',
                                  values=hit_name,
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_AnnotatedMembers',
                                  values=' '.join(hit['intersections']),
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_AnnotatedMembers_Size',
                                  values=len(non_members),
                                  type='integer',
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_AnnotatedMembers_Overlap',
                                  values=round(hit['jaccard'], 3),
                                  type='double',
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_Annotated_Pvalue',
                                  values=hit['p_value'],
                                  type='double',
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_Labeled',
                                  values=labeled,
                                  type='boolean',
                                  overwrite=True)
        algo_summary = 'Annotated by [Docker: ' + docker_image + '] {'
        if custom_params is not None:
            algo_summary += ' '.join(custom_params) + '}'
        else:
            algo_summary += '}'
        algo_summary + ' via run_functionalenrichment.py'

        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_AnnotatedAlgorithm',
                                  values=algo_summary,
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_NonAnnotatedMembers',
                                  values=' '.join(non_members),
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_AnnotatedMembers_SourceDB',
                                  values=hit['source'],
                                  overwrite=True)
        net_cx.add_node_attribute(property_of=node_id,
                                  name='CD_AnnotatedMembers_SourceTerm',
                                  values=hit['sourceTermId'],
                                  overwrite=True)

    def _update_network_with_result(self, docker_image, member_list, net_cx, node_id, result,
                                   custom_params=None):
        """

        :param result:
        :return:
        """
        res_as_json = json.loads(result)
        if isinstance(res_as_json, dict):
            res_list = [res_as_json]

        self._annotate_node_with_best_hit(docker_image, member_list, net_cx, node_id, res_list[0],
                                    custom_params=custom_params)

        return net_cx

    def run_functional_enrichment(self, net_cx, docker_image=None,
                                  temp_dir=None,
                                  arguments=None,
                                  numthreads=2,
                                  max_gene_list=500,
                                  disable_tqdm=False):
        """

        :param net_cx:
        :param docker_image:
        :param temp_dir:
        :return:
        """
        if docker_image is None:
            raise CommunityDetectionError('Docker image cannot be None')

        num_nodes = len(net_cx.get_nodes())
        counter = 0
        docker_cmds = []
        tempdir = tempfile.mkdtemp(prefix='run_funcenrichment', dir=temp_dir)
        try:
            t_progress = tqdm(total=num_nodes, desc='Create tasks', unit=' tasks',
                              disable=disable_tqdm)
            for node_id, node_obj in net_cx.get_nodes():
                gene_list_file, gene_list = self._write_gene_list(net_cx=net_cx,
                                                                 node_id=node_id,
                                                                 tempdir=tempdir,
                                                                 counter=counter,
                                                                 max_gene_list=max_gene_list)
                t_progress.update()
                counter += 1
                if gene_list_file is None:
                    continue

                full_genelist_path = os.path.abspath(gene_list_file)

                full_args = [full_genelist_path]
                if arguments is not None:
                    full_args.extend(arguments)

                cmd_dict = {'index': counter,
                            'node_id': node_id,
                            'outfile': os.path.join(tempdir, str(counter) + '.out'),
                            'image': docker_image,
                            'arguments': full_args,
                            'temp_dir': tempdir,
                            'docker_runner': self._docker}

                docker_cmds.append(cmd_dict)

            t_progress.close()
            # run all the docker commands
            with Pool(numthreads) as p:
                num_cmds = len(docker_cmds)
                with tqdm(total=num_cmds, desc='Running tasks', unit=' tasks',
                          disable=disable_tqdm) as pbar:
                    for i, _ in enumerate(p.imap_unordered(run_functional_enrichment_docker, docker_cmds)):
                        pbar.update()

            # process_pool.map(run_docker, tqdm(docker_cmds, desc='Running Docker'))

            for docker_cmd in tqdm(docker_cmds, desc='Add results', disable=disable_tqdm):
                if not os.path.isfile(docker_cmd['outfile']):
                    continue
                with open(docker_cmd['outfile'], 'r') as f:
                    res = json.load(f)

                if res['e_code'] is 0 and len(res['out']) > 0:
                    self._update_network_with_result(docker_image, gene_list,
                                               net_cx, docker_cmd['node_id'],
                                               res['out'], custom_params=arguments)
                else:
                    net_cx.add_node_attribute(property_of=docker_cmd['node_id'],
                                              name='CD_CommunityName',
                                              values='(none)',
                                              overwrite=True)
                    net_cx.add_node_attribute(property_of=docker_cmd['node_id'],
                                              name='CD_Labeled',
                                              values=False,
                                              type='boolean',
                                              overwrite=True)

            return net_cx
        finally:
            shutil.rmtree(tempdir)

