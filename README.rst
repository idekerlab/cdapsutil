===============================
CDAPS Python Utilities
===============================

.. image:: https://img.shields.io/pypi/v/cdapsutil.svg
        :target: https://pypi.python.org/pypi/cdapsutil

.. image:: https://travis-ci.com/idekerlab/cdapsutil.svg?branch=master
    :target: https://travis-ci.com/idekerlab/cdapsutil

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

.. code-block::

    git clone https://github.com/idekerlab/cdapsutil
    cd cdapsutil
    make dist
    pip install dist/cdapsutil*whl

Usage
-------

Run Community Detection

.. code-block::

    from cdapsutil.cd import CommunityDetection

    # Run HiDeF on CDAPS REST service where net_cx is a NiceCXNetwork of input network
    hier_net = cd.run_community_detection(net_cx, algo_or_docker='hidef', via_service=True)


Run Functional Enrichment

Coming soon...

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
