.. _installation:

==========================
Installation on Unix/Linux
==========================

**Kallithea** is written entirely in Python.  Kallithea requires Python version
2.6 or higher.

.. Note:: Alternative very detailed installation instructions for Ubuntu Server
   with celery, indexer and daemon scripts: https://gist.github.com/4546398

Installing Kallithea from repository source
-------------------------------------------

The Kallithea development repository is stable and can be used in production.
Follow these instructions::

        hg clone https://kallithea-scm.org/repos/kallithea
        cd kallithea
        virtualenv ../kallithea-venv
        source ../kallithea-venv/bin/activate
        python setup.py develop

You can now proceed to :ref:`setup`.

To upgrade, simply update the repository with ``hg pull -u`` and restart the
server.

Installing Kallithea from Python Package Index (PyPI)
-----------------------------------------------------

**Kallithea** can be installed from PyPI with::

    pip install kallithea


Installation in virtualenv
--------------------------

It is highly recommended to use a separate virtualenv_ for installing Kallithea.
This way, all libraries required by Kallithea will be installed separately from your
main Python installation and things will be less problematic when upgrading the
system or Kallithea.
An additional benefit of virtualenv_ is that it doesn't require root privileges. 

- Assuming you have installed virtualenv_, create a new virtual environment
  using virtualenv command::

    virtualenv /srv/kallithea/venv

.. note:: Older versions of virtualenv required ``--no-site-packages`` to work
   correctly. It should no longer be necessary.

- this will install new virtualenv_ into `/srv/kallithea/venv`.
- Activate the virtualenv_ in your current shell session by running::

    source /srv/kallithea/venv/bin/activate

.. note:: If you're using UNIX, *do not* use ``sudo`` to run the
   ``virtualenv`` script.  It's perfectly acceptable (and desirable)
   to create a virtualenv as a normal user.

- Make a folder for Kallithea data files, and configuration somewhere on the
  filesystem. For example::

    mkdir /srv/kallithea

- Go into the created directory run this command to install kallithea::

    pip install kallithea

  Alternatively, download a .tar.gz from http://pypi.python.org/pypi/Kallithea,
  extract it and run::

    python setup.py install

- This will install Kallithea together with pylons and all other required
  python libraries into the activated virtualenv.


Requirements for Celery (optional)
----------------------------------

In order to gain maximum performance
there are some third-party you must install. When Kallithea is used
together with celery you have to install some kind of message broker,
recommended one is rabbitmq_ to make the async tasks work.

Of course Kallithea works in sync mode also and then you do not have to install
any third party applications. However, using Celery_ will give you a large
speed improvement when using many big repositories. If you plan to use
Kallithea for say 7 to 10 repositories, Kallithea will perform perfectly well
without celery running.

If you make the decision to run Kallithea with celery make sure you run
celeryd using paster and message broker together with the application.

.. note::
   Installing message broker and using celery is optional, Kallithea will
   work perfectly fine without them.


**Message Broker**

- preferred is `RabbitMq <http://www.rabbitmq.com/>`_
- A possible alternative is `Redis <http://code.google.com/p/redis/>`_

For installation instructions you can visit:
http://ask.github.com/celery/getting-started/index.html.
This is a very nice tutorial on how to start using celery_ with rabbitmq_


Next
----

You can now proceed to :ref:`setup`.


Upgrading Kallithea from Python Package Index (PyPI)
-----------------------------------------------------

.. note::
   Firstly, it is recommended that you **always** perform a database and
   configuration backup before doing an upgrade.

   (These directions will use '{version}' to note that this is the version of
   Kallithea that these files were used with.  If backing up your Kallithea
   instance from version 0.1 to 0.2, the ``my.ini`` file could be
   backed up to ``my.ini.0-1``.)


If using a SQLite database, stop the Kallithea process/daemon/service, and
then make a copy of the database file::

 service kallithea stop
 cp kallithea.db kallithea.db.{version}


Back up your configuration file::

 cp my.ini my.ini.{version}


Ensure that you are using the Python Virtual Environment that you'd originally
installed Kallithea in::

 pip freeze

will list all packages installed in the current environment.  If Kallithea
isn't listed, change virtual environments to your venv location::

 source /srv/kallithea/venv/bin/activate


Once you have verified the environment you can upgrade Kallithea with::

 pip install --upgrade kallithea


Then run the following command from the installation directory::

 paster make-config Kallithea my.ini

This will display any changes made by the new version of Kallithea to your
current configuration. It will try to perform an automerge. It's recommended
that you re-check the content after the automerge.

.. note::
   Please always make sure your .ini files are up to date. Often errors are
   caused by missing params added in new versions.


It is also recommended that you rebuild the whoosh index after upgrading since
the new whoosh version could introduce some incompatible index changes. Please
read the changelog to see if there were any changes to whoosh.


The final step is to upgrade the database. To do this simply run::

 paster upgrade-db my.ini

This will upgrade the schema and update some of the defaults in the database,
and will always recheck the settings of the application, if there are no new
options that need to be set.


.. note::
   DB schema upgrade library has some limitations and can sometimes fail if you try to
   upgrade from older major releases. In such case simply run upgrades sequentially, eg.
   upgrading from 0.1.X to 0.3.X should be done like that: 0.1.X. > 0.2.X > 0.3.X
   You can always specify what version of Kallithea you want to install for example in pip
   `pip install Kallithea==0.2`

You may find it helpful to clear out your log file so that new errors are
readily apparent::

 echo > kallithea.log

Once that is complete, you may now start your upgraded Kallithea Instance::

 service kallithea start

Or::

 paster serve /srv/kallithea/my.ini

.. note::
   If you're using Celery, make sure you restart all instances of it after
   upgrade.


.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _python: http://www.python.org/
.. _mercurial: http://mercurial.selenic.com/
.. _celery: http://celeryproject.org/
.. _rabbitmq: http://www.rabbitmq.com/
