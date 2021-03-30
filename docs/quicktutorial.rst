Quick Tutorial
================

This quick tutorial has two parts:

* **Example** is a complete fragment of code that will generate a
  hierarchy from an input network.

* The steps section below provide more information on how to use this library.

Example
-----------------------

Open a terminal and run the block of code below either in a Python terminal or as a
Python script (requires Python 3.4+ with cdapsutil and `ndex2 <https://pypi.org/ndex2-client>`_ packages installed)

.. code-block:: python

    import json
    import cdapsutil
    import ndex2


    # Create CommunityDetection object
    cd = cdapsutil.CommunityDetection(runner=cdapsutil.ServiceRunner())

    # Create NDEx2 python client
    client = ndex2.client.Ndex2()

    # Download BioGRID: Protein-Protein Interactions (SARS-CoV) from NDEx
    # http://ndexbio.org/viewer/networks/669f30a3-cee6-11ea-aaef-0ac135e8bacf
    client_resp = client.get_network_as_cx_stream('669f30a3-cee6-11ea-aaef-0ac135e8bacf')

    # Convert downloaded network to NiceCXNetwork object
    net_cx = ndex2.create_nice_cx_from_raw_cx(json.loads(client_resp.content))

    # Run HiDeF on CDAPS REST service
    hier_net = cd.run_community_detection(net_cx, algorithm='hidef')

    # Print information about hierarchy
    print('Hierarchy name: ' + str(hier_net.get_name()))
    print('# nodes: ' + str(len(hier_net.get_nodes())))
    print('# edges: ' + str(len(hier_net.get_edges())))

    # Display 1st 500 characters of hierarchy network CX
    print(json.dumps(hier_net.to_cx())[0:500])

The code blocks above use the `NDEx2 Python client <https://pypi.org/ndex2-client>`_ to download
`BioGRID: Protein-Protein Interactions (SARS-CoV) <http://ndexbio.org/viewer/networks/669f30a3-cee6-11ea-aaef-0ac135e8bacf>`_
network from `NDEx <https://ndexbio.org>`_ as a `NiceCXNetwork <https://ndex2.readthedocs.io/en/latest/ndex2.html#nicecxnetwork>`_.
The Community Detection algorithm `HiDeF <https://github.com/idekerlab/cdhidef>`_ is then run on the network using the
`CDAPS REST Service <https://cdaps.readthedocs.io>`_. The result is a
`NiceCXNetwork <https://ndex2.readthedocs.io/en/latest/ndex2.html#nicecxnetwork>`_ stored in ``hier_net`` object.


Step 1 - Choose what to run
---------------------------------------

.. code-block:: python

    import cdapsutil

    sr = cdapsutil.ServiceRunner()
    algos = sr.get_algorithms()['algorithms']
    for key in algos.keys():
        if 'EDGELIST' not in algos[key]['inputDataFormat']:
            continue
        if 'COMMUNITYDETECT' not in algos[key]['outputDataFormat']:
            continue
        print('Algorithm name: ' + str(key))
        print('\tDocker image: ' + str(algos[key]['dockerImage']))

Step 2 - Choose where to run
---------------------------------

Alternate **Runner** objects can be set in the **CommunityDetection** constructor
object to denote where to run the Community Detection Algorithm.

**Remotely Via CDAPS REST Service**

If **runner** is omitted this is the default behavior. When used the Community Detection
Algorithm is run remotely on CDAPS REST Service

.. code-block:: python

    cd = cdapsutil.CommunityDetection(runner=cdapsutil.ServiceRunner())


**Locally Via Docker**

The **DockerRunner** runs the Community Detection Algorithm using a locally installed
Docker.

.. code-block:: python

    cd = cdapsutil.CommunityDetection(runner=cdapsutil.DockerRunner())

**Use already generated output**

The **ExternalResultsRunner** assumes the **algorithm** passed into **run_community_detection**
is a path to a file containing the results from an externally run Community Detection Algorithm.
This is useful for the case where the algorithm was run on a cluster via Singularity.

.. code-block:: python

    cd = cdapsutil.CommunityDetection(runner=cdapsutil.ExternalResultsRunner())
