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

=======================
Rackspace Install
=======================
1.  apt-get install -y  git python-argcomplete python-flask python-paramiko apache2 libapache2-mod-wsgi
2.  easy_install github3.py  
3.  git clone https://github.com/polyphemus-ci/polyphemus
4.  cd polyphemus
5.  python setup.py install
6.  cd ..
7.  git clone https://github.com/cyclus/polyphemusrc
8.  cd polyphemusrc
9.  ssh-keygen -t rsa
10. service apache2 stop
11. polyphemus --rc cyclusrc.py --plugins polyphemus.apache2 --apache2-setup
12. polyphemus --rc cyclusrc.py
13. a2ensite cyclus-ci.fuelcycle.org
14. cp -r ~/.ssh/ /var/www/.ssh
15. chmod +rx /var/www/
16. chmod +rx /var/www/.ssh
17. chmod +r /var/www/.ssh/id_rsa
18. chmod +rx /root
19. chmod +rx /root/polyphemusrc
20. service apache2 start

