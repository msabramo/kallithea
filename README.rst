=========
Kallithea
=========

About
-----

``Kallithea`` is a fast and powerful management tool for Mercurial_ and GIT_
with a built in push/pull server, full text search and code-review.
It works on http/https and has a built in permission/authentication system with
the ability to authenticate via LDAP or ActiveDirectory. Kallithea also provides
simple API so it's easy integrable with existing external systems.

Kallithea is similar in some respects to github_ or bitbucket_,
however Kallithea can be run as standalone hosted application on your own server.
It is open source and donation ware and focuses more on providing a customized,
self administered interface for Mercurial_ and GIT_  repositories.
Kallithea works on \*nix systems and Windows it is powered by a vcs_ library
that Lukasz Balcerzak and Marcin Kuzminski created to handle multiple
different version control systems.

Installation
------------
Stable releases of Kallithea are best installed via::

    easy_install kallithea

Or::

    pip install kallithea

Detailed instructions and links may be found on the Installation page.

Please visit http://packages.python.org/Kallithea/installation.html for
more details


Source code
-----------

The latest sources can be obtained from https://kallithea-scm.org/repos/kallithea


MIRRORS:

Issue tracker and sources at bitbucket_

https://bitbucket.org/conservancy/kallithea



Kallithea Features
------------------

- Has its own middleware to handle mercurial_ and git_ protocol requests.
  Each request is authenticated and logged together with IP address.
- Build for speed and performance. You can make multiple pulls/pushes simultaneous.
  Proven to work with 1000s of repositories and users
- Supports http/https, LDAP, AD, proxy-pass authentication.
- Full permissions (private/read/write/admin) together with IP restrictions for each repository,
  additional explicit forking, repositories group and repository creation permissions.
- User groups for easier permission management.
- Repository groups let you group repos and manage them easier. They come with
  permission delegation features, so you can delegate groups management.
- Users can fork other users repos, and compare them at any time.
- Built in Gist functionality for sharing code snippets.
- Integrates easily with other systems, with custom created mappers you can connect it to almost
  any issue tracker, and with an JSON-RPC API you can make much more
- Build in commit-api let's you add, edit and commit files right from Kallithea
  web interface using simple editor or upload binary files using simple form.
- Powerfull pull-request driven review system with inline commenting,
  changeset statuses, and notification system.
- Importing and syncing repositories from remote locations for GIT_, Mercurial_ and  SVN.
- Mako templates let's you customize the look and feel of the application.
- Beautiful diffs, annotations and source code browsing all colored by pygments.
  Raw diffs are made in git-diff format for both VCS systems, including GIT_ binary-patches
- Mercurial_ and Git_ DAG graphs and yui-flot powered graphs with zooming and statistics
  to track activity for repositories
- Admin interface with user/permission management. Admin activity journal, logs
  pulls, pushes, forks, registrations and other actions made by all users.
- Server side forks. It is possible to fork a project and modify it freely
  without breaking the main repository.
- rst and markdown README support for repositories.
- Full text search powered by Whoosh on the source files, commit messages, and file names.
  Build in indexing daemons, with optional incremental index build
  (no external search servers required all in one application)
- Setup project descriptions/tags and info inside built in db for easy, non
  file-system operations.
- Intelligent cache with invalidation after push or project change, provides
  high performance and always up to date data.
- RSS / Atom feeds, gravatar support, downloadable sources as zip/tar/gz
- Optional async tasks for speed and performance using celery_
- Backup scripts can do backup of whole app and send it over scp to desired
  location
- Based on pylons / sqlalchemy / sqlite / whoosh / vcs


Incoming / Plans
----------------

- Finer granular permissions per branch, or subrepo
- Web based merges for pull requests
- Tracking history for each lines in files
- Simple issue tracker
- SSH based authentication with server side key management
- Commit based built in wiki system
- More statistics and graph (global annotation + some more statistics)
- Other advancements as development continues (or you can of course make
  additions and or requests)

License
-------

``Kallithea`` is released under the GPLv3 license.


Getting help
------------

Listed bellow are various support resources that should help.

.. note::

   Please try to read the documentation before posting any issues, especially
   the **troubleshooting section**

- Open an issue at `issue tracker <https://bitbucket.org/conservancy/kallithea/issues>`_

- Join #kallithea on FreeNode (irc.freenode.net)
  or use http://webchat.freenode.net/?channels=kallithea for web access to irc.

You can follow this project on Twitter, **@KallitheaSCM**.


Online documentation
--------------------

Online documentation for the current version of Kallithea is available at
 - http://packages.python.org/Kallithea/
 - http://kallithea.readthedocs.org/

You may also build the documentation for yourself - go into ``docs/`` and run::

   make html

(You need to have sphinx_ installed to build the documentation. If you don't
have sphinx_ installed you can install it via the command:
``easy_install sphinx``)


Converting from RhodeCode
-------------------------

Currently, you have two options for working with an existing RhodeCode database:
 - keep the database unconverted (intended for testing and evaluation)
 - convert the database in a one-time step

Maintaining Interoperability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Interoperability with RhodeCode 2.2.5 installations is provided so you don't
have to immediately commit to switching to Kallithea. This option will most
likely go away once the two projects have diverged significantly.

To run Kallithea on a Rhodecode database, run::

   echo "BRAND = 'rhodecode'" > kallithea/brand.py

This location will depend on where you installed Kallithea. If you installed via::

   python setup.py install

then you will find this location at
``$VIRTUAL_ENV/lib/python2.7/site-packages/Kallithea-2.2.5-py2.7.egg/kallithea``

One-time Conversion
~~~~~~~~~~~~~~~~~~~

Alternatively, if you would like to convert the database for good, you can use
a helper script provided by Kallithea. This script will operate directly on the
database, using the database string you can find in your ``production.ini`` (or
``development.ini``) file. For example, if using SQLite::

   cd /path/to/kallithea
   cp /path/to/rhodecode/rhodecode.db kallithea.db
   pip install sqlalchemy-migrate
   python kallithea/bin/rebranddb.py sqlite:///kallithea.db

.. WARNING::

   If you used the other method for interoperability, overwrite brand.py with
   an empty file (or watch out for stray brand.pyc after removing brand.py).

.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _python: http://www.python.org/
.. _sphinx: http://sphinx.pocoo.org/
.. _mercurial: http://mercurial.selenic.com/
.. _bitbucket: http://bitbucket.org/
.. _github: http://github.com/
.. _subversion: http://subversion.tigris.org/
.. _git: http://git-scm.com/
.. _celery: http://celeryproject.org/
.. _Sphinx: http://sphinx.pocoo.org/
.. _vcs: http://pypi.python.org/pypi/vcs
