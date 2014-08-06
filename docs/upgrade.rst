.. _upgrade:

=======
Upgrade
=======

Upgrading from PyPI (aka "Cheeseshop")
---------------------------------------

.. note::
   Firstly, it is recommended that you **always** perform a database and
   configuration backup before doing an upgrade.

   (These directions will use '{version}' to note that this is the version of
   Kallithea that these files were used with.  If backing up your Kallithea
   instance from version 1.3.6 to 1.4.0, the ``production.ini`` file would be
   backed up to ``production.ini.1-3-6``.)


If using a sqlite database, stop the Kallithea process/daemon/service, and
then make a copy of the database file::

 service kallithea stop
 cp kallithea.db kallithea.db.{version}


Back up your configuration file::

 cp production.ini production.ini.{version}


Ensure that you are using the Python Virtual Environment that you'd originally
installed Kallithea in::

 pip freeze

will list all packages installed in the current environment.  If Kallithea
isn't listed, change virtual environments to your venv location::

 source /opt/kallithea-venv/bin/activate


Once you have verified the environment you can upgrade ``Kallithea`` with::

 easy_install -U kallithea

Or::

 pip install --upgrade kallithea


Then run the following command from the installation directory::

 paster make-config Kallithea production.ini

This will display any changes made by the new version of Kallithea to your
current configuration. It will try to perform an automerge. It's recommended
that you re-check the content after the automerge.

.. note::
   Please always make sure your .ini files are up to date. Often errors are
   caused by missing params added in new versions.


It is also recommended that you rebuild the whoosh index after upgrading since
the new whoosh version could introduce some incompatible index changes. Please
Read the changelog to see if there were any changes to whoosh.


The final step is to upgrade the database. To do this simply run::

 paster upgrade-db production.ini

This will upgrade the schema and update some of the defaults in the database,
and will always recheck the settings of the application, if there are no new
options that need to be set.


.. note::
   DB schema upgrade library has some limitations and can sometimes fail if you try to
   upgrade from older major releases. In such case simply run upgrades sequentially, eg.
   upgrading from 1.2.X to 1.5.X should be done like that: 1.2.X. > 1.3.X > 1.4.X > 1.5.X
   You can always specify what version of Kallithea you want to install for example in pip
   `pip install Kallithea==1.3.6`

You may find it helpful to clear out your log file so that new errors are
readily apparent::

 echo > kallithea.log

Once that is complete, you may now start your upgraded Kallithea Instance::

 service kallithea start

Or::

 paster serve /var/www/kallithea/production.ini

.. note::
   If you're using Celery, make sure you restart all instances of it after
   upgrade.

.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _python: http://www.python.org/
.. _mercurial: http://mercurial.selenic.com/
.. _celery: http://celeryproject.org/
.. _rabbitmq: http://www.rabbitmq.com/
