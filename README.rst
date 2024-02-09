===============================
CDAPS Python Utilities
===============================

.. image:: https://img.shields.io/pypi/v/cdapsutil.svg
        :target: https://pypi.python.org/pypi/cdapsutil

.. image:: https://app.travis-ci.com/idekerlab/cdapsutil.svg?branch=master
    :target: https://app.travis-ci.com/github/idekerlab/cdapsutil

.. image:: https://coveralls.io/repos/github/idekerlab/cdapsutil/badge.svg?branch=master
    :target: https://coveralls.io/github/idekerlab/cdapsutil?branch=master

.. image:: https://readthedocs.org/projects/cdapsutil/badge/?version=latest
        :target: https://cdapsutil.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status



Library that enables invocation of `Community Detection APplication and Service <https://cdaps.readthedocs.io/>`_
algorithms via Python


.. warning::

    cdapsutil is experimental and may contain errors and interfaces may change

Dependencies
-------------

* `ndex2 <https://pypi.org/project/ndex2>`_
* `requests <https://pypi.org/project/requests>`_
* `tqdm <https://pypi.org/project/tqdm>`_

Compatibility
---------------

* Python 3.4+

Installation
---------------

.. code-block:: console

    pip install cdapsutil

or directly via:

.. code-block::

    git clone https://github.com/idekerlab/cdapsutil
    cd cdapsutil
    python setup.py install

Usage
-------

Run Community Detection

.. code-block::

    import json
    import cdapsutil
    import ndex2


    # Download BioGRID: Protein-Protein Interactions (SARS-CoV) from NDEx
    client = ndex2.client.Ndex2()
    client_resp = client.get_network_as_cx_stream('669f30a3-cee6-11ea-aaef-0ac135e8bacf')
    net_cx = ndex2.create_nice_cx_from_raw_cx(json.loads(client_resp.content))

    # Create CommunityDetection object
    cd = cdapsutil.CommunityDetection()

    # Run HiDeF on CDAPS REST service
    hier_net = cd.run_community_detection(net_cx, algorithm='hidef')


Run Functional Enrichment

Coming soon...

Cite CDAPS
-----------

If you find this utility and service useful, please cite:

Singhal A, Cao S, Churas C, Pratt D, Fortunato S, Zheng F, et al. (2020) Multiscale community detection in Cytoscape. PLoS Comput Biol 16(10): e1008239. https://doi.org/10.1371/journal.pcbi.1008239


Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
