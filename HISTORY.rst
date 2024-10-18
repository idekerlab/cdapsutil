=======
History
=======

0.3.0 (2024-10-14)
----------------------

* Added support to run community detection on CX2 networks and generate HCX hierarchy

0.2.2 (2024-02-09)
----------------------

* Removed the "DISCLAIMER: cdapsutil is experimental..." warning level log message

0.2.1 (2023-10-04)
----------------------

* Removed scale, x, y, and z coordinates from visual properties aspect of default style
  stored in this tool. Done so UI tools will just fit content

0.2.0 (2022-10-04)
----------------------

* Fixed bug where not setting a name on a network
  would cause ``CommunityDetection.run_community_detection()``
  to raise a ``TypeError``. When encountered code now sets network
  name to **unknown** `Issue #1 <https://github.com/idekerlab/cdapsutil/issues/1>`__

0.2.0a1 (2021-03-30)
----------------------

* First release on PyPI.
