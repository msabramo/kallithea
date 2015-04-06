================
Kallithea README
================

About
-----

**Kallithea** is a fast and powerful management tool for Mercurial_ and Git_
with a built-in push/pull server, full text search and code-review. It works on
http/https and has a built in permission/authentication system with the ability
to authenticate via LDAP or ActiveDirectory. Kallithea also provides simple API
so it's easy to integrate with existing external systems.

Kallithea is similar in some respects to GitHub_ or Bitbucket_, however
Kallithea can be run as standalone hosted application on your own server. It is
open-source donationware and focuses more on providing a customised,
self-administered interface for Mercurial_ and Git_ repositories. Kallithea
works on Unix-like systems and Windows, and is powered by the vcs_ library
created by Łukasz Balcerzak and Marcin Kuźmiński to uniformly handle multiple
version control systems.

Kallithea was forked from RhodeCode in July 2014 and has been heavily modified.

Installation
------------
Official releases of Kallithea can be installed via::

    pip install kallithea

The development repository is kept very stable and used in production by the
developers - you can do the same.

Please visit https://docs.kallithea-scm.org/en/latest/installation.html for
more details.


Source code
-----------

The latest sources can be obtained from
https://kallithea-scm.org/repos/kallithea.

The issue tracker and a repository mirror can be found at Bitbucket_ on
https://bitbucket.org/conservancy/kallithea.



Kallithea Features
------------------

- Has its own middleware to handle Mercurial_ and Git_ protocol requests. Each
  request is authenticated and logged together with IP address.
- Built for speed and performance. You can make multiple pulls/pushes
  simultaneously. Proven to work with thousands of repositories and users.
- Supports http/https, LDAP, AD, proxy-pass authentication.
- Full permissions (private/read/write/admin) together with IP restrictions for
  each repository, additional explicit forking, repositories group and
  repository creation permissions.
- User groups for easier permission management.
- Repository groups let you group repos and manage them easier. They come with
  permission delegation features, so you can delegate groups management.
- Users can fork other users repos, and compare them at any time.
- Built-in versioned paste functionality (Gist) for sharing code snippets.
- Integrates easily with other systems, with custom created mappers you can
  connect it to almost any issue tracker, and with a JSON-RPC API you can make
  much more.
- Built-in commit API lets you add, edit and commit files right from Kallithea
  web interface using simple editor or upload binary files using simple form.
- Powerful pull request driven review system with inline commenting, changeset
  statuses, and notification system.
- Importing and syncing repositories from remote locations for Git_, Mercurial_
  and Subversion.
- Mako templates let you customize the look and feel of the application.
- Beautiful diffs, annotations and source code browsing all colored by
  pygments. Raw diffs are made in Git-diff format for both VCS systems,
  including Git_ binary-patches.
- Mercurial_ and Git_ DAG graphs and Flot-powered graphs with zooming and
  statistics to track activity for repositories.
- Admin interface with user/permission management. Admin activity journal, logs
  pulls, pushes, forks, registrations and other actions made by all users.
- Server side forks. It is possible to fork a project and modify it freely
  without breaking the main repository.
- reST and Markdown README support for repositories.
- Full text search powered by Whoosh on the source files, commit messages, and
  file names. Built-in indexing daemons, with optional incremental index build
  (no external search servers required all in one application).
- Setup project descriptions/tags and info inside built in DB for easy,
  non-filesystem operations.
- Intelligent cache with invalidation after push or project change, provides
  high performance and always up to date data.
- RSS/Atom feeds, Gravatar support, downloadable sources as zip/tar/gz.
- Optional async tasks for speed and performance using Celery_.
- Backup scripts can do backup of whole app and send it over scp to desired
  location.
- Based on Pylons, SQLAlchemy, SQLite, Whoosh, vcs.


License
-------

**Kallithea** is released under the GPLv3 license. Kallithea is a `Software
Freedom Conservancy`_ project and thus controlled by a non-profit organization.
No commercial entity can take ownership of the project and change the
direction.

Kallithea started out as an effort to make sure the existing GPLv3 codebase
would stay available under a legal license. Kallithea thus has to stay GPLv3
compatible ... but we are also happy it is GPLv3 and happy to keep it that way.
A different license (such as AGPL) could perhaps help attract a different
community with a different mix of Free Software people and companies but we are
happy with the current focus.


Community
---------

**Kallithea** is maintained by its users who contribute the fixes they would
 like to see.

Get in touch with the rest of the community:

- Join the mailing list users and developers - see
  http://lists.sfconservancy.org/mailman/listinfo/kallithea-general.

- Use IRC and join #kallithea on FreeNode (irc.freenode.net) or use
  http://webchat.freenode.net/?channels=kallithea.

- Follow Kallithea on Twitter, **@KallitheaSCM**.

- Issues can be reported at `issue tracker
  <https://bitbucket.org/conservancy/kallithea/issues>`_.

   .. note::

       Please try to read the documentation before posting any issues,
       especially the **troubleshooting section**


Online documentation
--------------------

Online documentation for the current version of Kallithea is available at
https://pythonhosted.org/Kallithea/. Documentation for the current development
version can be found on https://docs.kallithea-scm.org/.

You can also build the documentation locally: go to ``docs/`` and run::

   make html

.. note:: You need to have Sphinx_ installed to build the
          documentation. If you don't have Sphinx_ installed you can
          install it via the command: ``pip install sphinx`` .


Converting from RhodeCode
-------------------------

Currently, you have two options for working with an existing RhodeCode
database:

- keep the database unconverted (intended for testing and evaluation)
- convert the database in a one-time step

Maintaining Interoperability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Interoperability with RhodeCode 2.2.X installations is provided so you don't
have to immediately commit to switching to Kallithea. This option will most
likely go away once the two projects have diverged significantly.

To run Kallithea on a RhodeCode database, run::

   echo "BRAND = 'rhodecode'" > kallithea/brand.py

This location will depend on where you installed Kallithea. If you installed
via::

   python setup.py install

then you will find this location at
``$VIRTUAL_ENV/lib/python2.7/site-packages/Kallithea-0.1-py2.7.egg/kallithea``.

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

.. Note::

   If you started out using the branding interoperability approach mentioned
   above, watch out for stray brand.pyc after removing brand.py.

.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _Python: http://www.python.org/
.. _Sphinx: http://sphinx.pocoo.org/
.. _Mercurial: http://mercurial.selenic.com/
.. _Bitbucket: http://bitbucket.org/
.. _GitHub: http://github.com/
.. _Subversion: http://subversion.tigris.org/
.. _Git: http://git-scm.com/
.. _Celery: http://celeryproject.org/
.. _vcs: http://pypi.python.org/pypi/vcs
.. _Software Freedom Conservancy: http://sfconservancy.org/
