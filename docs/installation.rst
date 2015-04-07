.. _installation:

==========================
Installation on Unix/Linux
==========================

**Kallithea** is written entirely in Python_ and requires Python version
2.6 or higher. Python 3.x is currently not supported.

There are several ways to install Kallithea:

- :ref:`installation-source`: The Kallithea development repository is stable
  and can be used in production. In fact, the Kallithea maintainers do
  use it in production. The advantage of installation from source and regularly
  updating it is that you take advantage of the most recent improvements, which
  is particularly useful because Kallithea is evolving rapidly.

- :ref:`installation-virtualenv`: If you prefer to only use released versions
  of Kallithea, the recommended method is to install Kallithea in a virtual
  Python environment using `virtualenv`. The advantages of this method over
  direct installation is that Kallithea and its dependencies are completely
  contained inside the virtualenv (which also means you can have multiple
  installations side by side or remove it entirely by just removing the
  virtualenv directory) and does not require root privileges.

- :ref:`installation-without-virtualenv`: The alternative method of installing
  a Kallithea release is using standard pip. The package will be installed in
  the same location as all other Python packages you have ever installed. As a
  result, removing it is not as straightforward as with a virtualenv, as you'd
  have to remove its dependencies manually and make sure that they are not
  needed by other packages.

.. _installation-source:

Installation from repository source
-----------------------------------

To install Kallithea from source in a virtualenv, follow the instructions
below::

        hg clone https://kallithea-scm.org/repos/kallithea
        cd kallithea
        virtualenv ../kallithea-venv
        source ../kallithea-venv/bin/activate
        python setup.py develop
        python setup.py compile_catalog   # for translation of the UI

You can now proceed to :ref:`setup`.

To upgrade, simply update the repository with ``hg pull -u`` and restart the
server.

.. _installation-virtualenv:

Installing a released version in a virtualenv
---------------------------------------------

It is highly recommended to use a separate virtualenv_ for installing Kallithea.
This way, all libraries required by Kallithea will be installed separately from your
main Python installation and other applications and things will be less
problematic when upgrading the system or Kallithea.
An additional benefit of virtualenv_ is that it doesn't require root privileges.

- Assuming you have installed virtualenv_, create a new virtual environment
  for example, in `/srv/kallithea/venv`, using the virtualenv command::

    virtualenv /srv/kallithea/venv

- Activate the virtualenv_ in your current shell session by running::

    source /srv/kallithea/venv/bin/activate

.. note:: You can't use UNIX ``sudo`` to source the ``virtualenv`` script; it
   will "activate" a shell that terminates immediately. It is also perfectly
   acceptable (and desirable) to create a virtualenv as a normal user.

- Make a folder for Kallithea data files, and configuration somewhere on the
  filesystem. For example::

    mkdir /srv/kallithea

- Go into the created directory and run this command to install Kallithea::

    pip install kallithea

  Alternatively, download a .tar.gz from http://pypi.python.org/pypi/Kallithea,
  extract it and run::

    python setup.py install

- This will install Kallithea together with pylons_ and all other required
  python libraries into the activated virtualenv.

You can now proceed to :ref:`setup`.

.. _installation-without-virtualenv:

Installing a released version without virtualenv
------------------------------------------------

For installation without virtualenv, 'just' use::

    pip install kallithea

Note that this method requires root privileges and will install packages
globally without using the system's package manager.

To install as a regular user in ``~/.local``, you can use::

    pip install --user kallithea

You can now proceed to :ref:`setup`.

Upgrading Kallithea from Python Package Index (PyPI)
-----------------------------------------------------

.. note::
   It is strongly recommended that you **always** perform a database and
   configuration backup before doing an upgrade.

   These directions will use '{version}' to note that this is the version of
   Kallithea that these files were used with.  If backing up your Kallithea
   instance from version 0.1 to 0.2, the ``my.ini`` file could be
   backed up to ``my.ini.0-1``.


If using a SQLite database, stop the Kallithea process/daemon/service, and
then make a copy of the database file::

 service kallithea stop
 cp kallithea.db kallithea.db.{version}


Back up your configuration file::

 cp my.ini my.ini.{version}


Ensure that you are using the Python virtual environment that you originally
installed Kallithea in by running::

 pip freeze

This will list all packages installed in the current environment.  If
Kallithea isn't listed, activate the correct virtual environment::

 source /srv/kallithea/venv/bin/activate


Once you have verified the environment you can upgrade Kallithea with::

 pip install --upgrade kallithea


Then run the following command from the installation directory::

 paster make-config Kallithea my.ini

This will display any changes made by the new version of Kallithea to your
current configuration. It will try to perform an automerge. It is recommended
that you recheck the content after the automerge.

.. note::
   Please always make sure your .ini files are up to date. Errors can
   often be caused by missing parameters added in new versions.


It is also recommended that you rebuild the whoosh index after upgrading since
the new whoosh version could introduce some incompatible index changes. Please
read the changelog to see if there were any changes to whoosh.


The final step is to upgrade the database. To do this simply run::

 paster upgrade-db my.ini

This will upgrade the schema and update some of the defaults in the database,
and will always recheck the settings of the application, if there are no new
options that need to be set.


.. note::
   The DB schema upgrade library has some limitations and can sometimes fail if you try to
   upgrade from older major releases. In such a case simply run upgrades sequentially, e.g.,
   upgrading from 0.1.X to 0.3.X should be done like this: 0.1.X. > 0.2.X > 0.3.X
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
.. _Python: http://www.python.org/
.. _pylons: http://www.pylonsproject.org/
