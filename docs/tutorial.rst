.. _tutorial:

*******************
Tutorial
*******************
Polyphemus is a continuous integration tool that ties together services like 
GitHub to the build & test laboratory (BaTLab). There are many options that you 
might include.  

=======================
Putting It All Together
=======================
The following is a more complete, realistic example of a `polyphemusrc.py` file that
one might run across in a production level environment.

.. code-block:: python

    # Generic Settings
    # the URL or IP address where Polyphemus is running
    server_name = server_url = 'cycamore-ci.fuelcycle.org'
    # The port to run Polyphemus on
    port = 80

    # GitHub settings
    # a user name with rights to the target repository
    github_user = 'cyclus-ci'
    # the user or organization that owns the repo
    github_owner = 'cyclus'
    # the repo name
    github_repo = 'cycamore'
    # local file to store github login info
    github_credentials = '/root/polyphemusrc/gh.cred'

    # BaTLab settings
    # The BaTLab username
    batlab_user = 'cyclusci'
    # Location to grab batlab scripts from, may be a zip file or a git repo
    batlab_scripts_url = 'https://github.com/cyclus/ciclus/archive/master.zip'
    # the fetch file, will be overwritten with pull request location
    batlab_fetch_file = 'fetch/cycamore.git'
    # top-level run specification
    batlab_run_spec = 'cycamore.fast.run-spec'
    # Optional custom batlab submission command
    batlab_submit_cmd = './submit.sh'

    # Apache settings
    # Directory for log file, must be writeable and exist.
    log_dir = '/root/polyphemusrc'


=======================
Rackspace Install
=======================

.. code-block:: bash

    # Install Dependencies
    apt-get install -y  git python-argcomplete python-flask python-paramiko apache2 libapache2-mod-wsgi
    easy_install github3.py  
    service apache2 stop

    # Install Polyphemus
    git clone https://github.com/polyphemus-ci/polyphemus
    cd polyphemus
    python setup.py install
    cd ..

    # Make SSH key (if you haven't done so)
    ssh-keygen -t rsa

    # Get run control files
    git clone https://github.com/cyclus/polyphemusrc
    cd polyphemusrc

    # Setup polyphemus for a given run control file, 
    # kill these commands with ^C after they start
    polyphemus --only-setup --rc cyclusrc.py  
    polyphemus --only-setup --plugins polyphemus.apache2 --apache2-setup --rc cyclusrc.py
    a2ensite cyclus-ci.fuelcycle.org

    # Verify permissions for apache
    cp -r ~/.ssh/ /var/www/.ssh
    chmod +rx /var/www/ /var/www/.ssh /root /root/polyphemusrc 
    chmod +r /var/www/.ssh/id_rsa 

    # Start apache!
    service apache2 start


=======================
Server Restart
=======================
Say you have just pulled in new commits from the repo.  The following 
is how you restart the server.


.. code-block:: bash

    # Pull & Install Polyphemus Updates
    cd polyphemus
    git pull 
    python setup.py install

    # Restart apache
    service apache2 restart

    # Restart development server
    # kill running server though ^C, ^D, or kill
    polyphemus --debug --rc /path/to/rc/file
