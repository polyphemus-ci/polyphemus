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

    # Generic parameters
    server_url = '198.101.154.53'  # the URL or IP address where Polyphemus is running
    port = 8080  # The port to run Polyphemus on

    # GitHub Parameters
    github_user = 'scopatz'  # a user name with rights to the target repository
    github_owner = 'cyclus'  # the user or organization that owns the repo
    github_repo = 'cyclus'   # the repo name

    # BaTLab Parameters
    batlab_user = 'cyclusci'  # The BaTLab username
    batlab_run_spec = 'cyclus.run-spec'  # top-level run specification
    # the fetch file, will be overwritten with pull request location
    batlab_fetch_file = 'fetch/cyclus.git'  
    # Location to grab batlab scripts from, may be a zip file or a git repo
    batlab_scripts_url = 'https://github.com/cyclus/ciclus/archive/master.zip'


