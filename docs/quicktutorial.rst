Quick Tutorial
================

The code snippets below show how to run Community Detection via a locally installed
Docker or with the service.


Running Community Detection
----------------------------

The code block below uses the `NDEx2 Python client <https://pypi.org/ndex2-client>`_ to download
`NCI PID PDGFR-beta signaling pathway <http://ndexbio.org/viewer/networks/640e2cef-795d-11e8-a4bf-0ac135e8bacf>`_
network from `NDEx <https://ndexbio.org>`_ as a `NiceCXNetwork <https://ndex2.readthedocs.io/en/latest/ndex2.html#nicecxnetwork>`_.
The Community Detection algorithm `HiDeF <https://github.com/idekerlab/cdhidef>`_ is then run on the network with using the
`CDAPS REST Service <https://cdaps.readthedocs.io>`_. The result is a
`NiceCXNetwork <https://ndex2.readthedocs.io/en/latest/ndex2.html#nicecxnetwork>`_ stored in ``hier_net`` object.

.. code-block:: python

    import json
    from cdapsutil.cd import CommunityDetection
    import ndex2

    # Create NDEx2 python client
    client = ndex2.client.Ndex2()

    # Download NCI PID PDGFR-beta signaling pathway from NDEx: http://ndexbio.org/viewer/networks/640e2cef-795d-11e8-a4bf-0ac135e8bacf
    client_resp = client.get_network_as_cx_stream('c901a3e4-6194-11e5-8ac5-06603eb7f303')

    # Convert downloaded network to NiceCXNetwork object
    net_cx = ndex2.create_nice_cx_from_raw_cx(json.loads(client_resp.content))

    # Create CommunityDetection object
    cd = CommunityDetection()

    # Run HiDeF on CDAPS REST service
    hier_net = cd.run_community_detection(net_cx, algo_or_docker='hidef', via_service=True)

    # To Run HiDeF via local Docker comment above line and uncomment the line below
    # hier_net = cd.run_community_detection(net_cx, algo_or_docker='coleslawndex/cdhidef:0.2.2')

    # print information about hierarchy
    print('Hierarchy name: ' + str(hier_net.get_name()))
    print('# nodes: ' + str(len(hier_net.get_nodes())))
    print('# edges: ' + str(len(hier_net.get_edges())))

    # Display 1st 500 characters of hierarchy network CX
    print(json.dumps(hier_net.to_cx())[0:500])


Link to `NCI PID PDGFR-beta signaling pathway <http://ndexbio.org/viewer/networks/640e2cef-795d-11e8-a4bf-0ac135e8bacf>`_

Example run of Functional Enrichment::

    from cdapsutil.cd import FunctionalEnrichment

