.. _tutorial:

*******************
Tutorial
*******************
Polyphemus is a continuous integration tool that ties together services like 
GitHub to the build & test laboratory (BaTLab). 


=======================
Putting It All Together
=======================
The following is a more complete, realistic example of a polyphemusrc.py file that
one might run across in a production level environment.

.. code-block:: python

    # GitHub Parameters
    github_user = 'scopatz'  # a user name with rights to the target repository
