cdapsutil package
=================

Community Detection
-----------------------

.. autoclass:: cdapsutil.cd.CommunityDetection
    :members:

Functional Enrichment
--------------------------

.. autoclass:: cdapsutil.fe.FunctionalEnrichment
    :members:

Runners
--------------------------

Runners provide different ways to run Community Detection Algorithms packaged
as `Docker <https://www.docker.com/>`__ containers built for
`CDAPS service <https://cdaps.readthedocs.io/>`__.

**Currently built Runners:**

* :py:class:`~cdapsutil.runner.ExternalResultsRunner` - Parses already run output file/stream

* :py:class:`~cdapsutil.runner.DockerRunner` - Runs locally via `Docker <https://www.docker.com>`__

* :py:class:`~cdapsutil.runner.ServiceRunner` - Runs remotely via `CDAPS REST Service <https://cdaps.readthedocs.io/>`__


.. autoclass:: cdapsutil.runner.DockerRunner
    :members:

.. autoclass:: cdapsutil.runner.ExternalResultsRunner
    :members:

.. autoclass:: cdapsutil.runner.ServiceRunner
    :members:

.. autoclass:: cdapsutil.runner.Runner
    :members:

.. autoclass:: cdapsutil.runner.ProcessWrapper
    :members:

Exceptions
---------------------------

.. automodule:: cdapsutil.exceptions
    :members:
    :undoc-members:
    :show-inheritance:
