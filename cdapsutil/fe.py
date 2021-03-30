# -*- coding: utf-8 -*-

import os
import logging
import json
import tempfile
import shutil
from multiprocessing import Pool
from tqdm import tqdm
import cdapsutil
from cdapsutil.exceptions import CommunityDetectionError
from cdapsutil import runner
from cdapsutil.runner import DockerRunner


LOGGER = logging.getLogger(__name__)


class FunctionalEnrichment(object):
    """
    **WARNING:** This is class is a work in progress and not ready for use

    :param docker: Object used to run FunctionalEnrichment via locally
                   installed Docker
    :type docker: :py:class:`~cdapsutil.runner.DockerRunner`
    :raises CommunityDetectionError: If `docker` is ``None``
    """
    def __init__(self, docker=DockerRunner()):
        """
        Constructor
        """
        if docker is None:
            raise CommunityDetectionError('docker is None')
        self._docker = docker

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
        algo_summary + ' via cdapsutil ' + str(cdapsutil.__version__)

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

    def _update_network_with_result(self, docker_image, member_list, net_cx,
                                    node_id, result,
                                    custom_params=None):
        """

        :param result:
        :return:
        """
        res_as_json = json.loads(result)
        if isinstance(res_as_json, dict):
            res_list = [res_as_json]

        self._annotate_node_with_best_hit(docker_image, member_list,
                                          net_cx, node_id, res_list[0],
                                          custom_params=custom_params)

        return net_cx

    def run_functional_enrichment(self, net_cx, algo_or_docker=None,
                                  temp_dir=None,
                                  arguments=None,
                                  numthreads=2,
                                  max_gene_list=500,
                                  disable_tqdm=False,
                                  via_service=False):
        """
        This is code is prototype and not ready for use

        :param net_cx:
        :param algo_or_docker:
        :param temp_dir:
        :return:
        """
        if algo_or_docker is None:
            raise CommunityDetectionError('Docker image cannot be None')

        if via_service is not None and via_service is True:
            raise CommunityDetectionError('Functional enrichment via service not supported')

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
                            'image': algo_or_docker,
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
                    for i, _ in enumerate(p.imap_unordered(runner._run_functional_enrichment_docker,
                                                           docker_cmds)):
                        pbar.update()

            for docker_cmd in tqdm(docker_cmds, desc='Add results', disable=disable_tqdm):
                if not os.path.isfile(docker_cmd['outfile']):
                    continue
                with open(docker_cmd['outfile'], 'r') as f:
                    res = json.load(f)

                if res['e_code'] is 0 and len(res['out']) > 0:
                    self._update_network_with_result(algo_or_docker, gene_list,
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
