Quick Tutorial
================

The code snippets below show how to run Community Detection via a locally installed
Docker or with the service.


Running Community Detection
----------------------------

The code blocks below use the `NDEx2 Python client <https://pypi.org/ndex2-client>`_ to download
`BioGRID: Protein-Protein Interactions (SARS-CoV) <http://ndexbio.org/viewer/networks/669f30a3-cee6-11ea-aaef-0ac135e8bacf>`_
network from `NDEx <https://ndexbio.org>`_ as a `NiceCXNetwork <https://ndex2.readthedocs.io/en/latest/ndex2.html#nicecxnetwork>`_.
The Community Detection algorithm `HiDeF <https://github.com/idekerlab/cdhidef>`_ is then run on the network using the
`CDAPS REST Service <https://cdaps.readthedocs.io>`_ or via a locally installed `Docker <https://docker.com>`_. The result is a
`NiceCXNetwork <https://ndex2.readthedocs.io/en/latest/ndex2.html#nicecxnetwork>`_ stored in ``hier_net`` object.

Remotely Via CDAPS REST Service
********************************

.. code-block:: python

    from cdapsutil.cd import CommunityDetection

    # Run HiDeF on CDAPS REST service where net_cx is a NiceCXNetwork of input network
    hier_net = cd.run_community_detection(net_cx, algo_or_docker='hidef', via_service=True)

.. note::

    To run on remote service set **via_service** to ``True``

**Fully runnable block of code:**

.. code-block:: python

    import json
    from cdapsutil.cd import CommunityDetection
    import ndex2


    # Create NDEx2 python client
    client = ndex2.client.Ndex2()

    # Download BioGRID: Protein-Protein Interactions (SARS-CoV) from NDEx
    # http://ndexbio.org/viewer/networks/669f30a3-cee6-11ea-aaef-0ac135e8bacf
    client_resp = client.get_network_as_cx_stream('669f30a3-cee6-11ea-aaef-0ac135e8bacf')

    # Convert downloaded network to NiceCXNetwork object
    net_cx = ndex2.create_nice_cx_from_raw_cx(json.loads(client_resp.content))

    # Create CommunityDetection object
    cd = CommunityDetection()

    # Run HiDeF on CDAPS REST service
    hier_net = cd.run_community_detection(net_cx, algo_or_docker='hidef', via_service=True)

    # Print information about hierarchy
    print('Hierarchy name: ' + str(hier_net.get_name()))
    print('# nodes: ' + str(len(hier_net.get_nodes())))
    print('# edges: ' + str(len(hier_net.get_edges())))

    # Display 1st 500 characters of hierarchy network CX
    print(json.dumps(hier_net.to_cx())[0:500])

Locally via Docker
********************

.. code-block:: python

    from cdapsutil.cd import CommunityDetection

    # Run HiDeF on CDAPS REST service where net_cx is a NiceCXNetwork of input network
    hier_net = cd.run_community_detection(net_cx, algo_or_docker='coleslawndex/cdhidef:0.2.2',
                                          temp_dir=temp_dir)

.. note::

    To run locally omit set **via_service** but be sure to set **temp_dir** to directory that can
    be accessed by `Docker <https://docker.com>`_

**Fully runnable block of code:**

.. code-block:: python

    import os
    import tempfile
    import shutil
    import json
    from cdapsutil.cd import CommunityDetection
    import ndex2


    # Create NDEx2 python client
    client = ndex2.client.Ndex2()

    # Download BioGRID: Protein-Protein Interactions (SARS-CoV) from NDEx
    # http://ndexbio.org/viewer/networks/669f30a3-cee6-11ea-aaef-0ac135e8bacf
    client_resp = client.get_network_as_cx_stream('669f30a3-cee6-11ea-aaef-0ac135e8bacf')

    # Convert downloaded network to NiceCXNetwork object
    net_cx = ndex2.create_nice_cx_from_raw_cx(json.loads(client_resp.content))

    # Create CommunityDetection object
    cd = CommunityDetection()


    # Run HiDeF via local Docker
    temp_dir = tempfile.mkdtemp(dir=os.getcwd())
    try:
        hier_net = cd.run_community_detection(net_cx, algo_or_docker='coleslawndex/cdhidef:0.2.2',
                                              temp_dir=temp_dir)
    finally:
        shutil.rmtree(temp_dir)

    # Print information about hierarchy
    print('Hierarchy name: ' + str(hier_net.get_name()))
    print('# nodes: ' + str(len(hier_net.get_nodes())))
    print('# edges: ' + str(len(hier_net.get_edges())))

    # Display 1st 500 characters of hierarchy network CX
    print(json.dumps(hier_net.to_cx())[0:500])

Example run of Functional Enrichment::

    from cdapsutil.cd import FunctionalEnrichment

