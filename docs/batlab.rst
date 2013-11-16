Polyphemus Continuous Integration
_______________________________________________________________________

Continuous Integration in Polyphemus uses the University of Wisconsin - Madison's `Batlab <http://batlab.org>`_

------------------------------------------------------------------
Running Tests on Batlab
------------------------------------------------------------------
First you have to create a Batlab account and have logged into the submit node.
Runs in Batlab are defined in run specification files (``.run-spec`` files). These files
contain a list of input files, scripts to run at Batlab-defined stages, and other test options.
The scripts Batlab runs on the test node must be copied from somewhere (git, scp,wget) using
input scripts defined in the ``.run-spec``  

To submit Batlab tests without making any changes, simply call ::

    ~/path_to_repo/$ nmi_submit file.run_spec

An example set of Batlab scripts can be found at the `Ciclus github page <http://github.com/cyclus/ciclus>`_

------------------------------------------------------------------
Customizing Your Tests on Batlab
------------------------------------------------------------------
There are many ways to customize the files in this repo to have Batlab run useful tests.

1) Have Batlab run code from a different repo
Say you want to test a fork of a repo before making a pull request. To 
customize what git repos are pulled from, look in ``fetch/cyclus.git``
and ``fetch/cycamore.git`` respectively.  In these files you can change the url to point 
to the repo of your choice.

2) Have Batlab run code in a non-default git branch
Batlab does not formally give options to change branches easily in fetch scripts,
but it is still easy to make the change.  See fetch/cyclus.v0.2.git to see how.

3) Get email updates when your job is finished
To get email updates, add a line in your local run-spec file a reading
``notify=<your_email_address>``

4) Test a new build process
To alter Cyclus or Cycamore's build process, look at ``build.sh`` (or ``build.mac.sh`` if 
you want to change the build process for OSX) in CYCLUS and CYCAMORE respectively.
Please note that Batlab provides a bare minimum of installed files, so most of
the dependencies are built locally.

5) Set up nightly runs
To set up what Batlab refers to as recurring runs, you must set the ``cron_minute`` and 
``cron_hour`` fields in your run-spec to specify the hour and minute you want the run
to occur each day.

6) Run tests only ins OSX or Ubuntu (or try a new OS)
There is a ``platforms`` field in all run specification files that list the operating
systems to run.  Some stages also have platform prefixes to specify which script should
be run in each OS stage.  To get a complete list of available systems run
``nmi_list_platforms`` on Batlab's submit node.

7) Bring something back from the execute node
If you create a results.tar.gz somewhere in your Batlab run, Batlab will know to bring
that file back, and it can be found in that tests run directory. The submit script should
print the run directory for a test when you submit it.

8) Bypass the lengthy build process
There may be some situations where you know the problem lies with unit tests and do not
want to wait for a complete rebuild between launching tests.  Use 7) above to bring back
the install directory, then in future runs have Batlab copy the install directory to the
execute node.  You can then use these files for unit testing instead of building them from scratch.



