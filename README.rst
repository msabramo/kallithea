=========
RhodeCode
=========

About
-----

``RhodeCode`` is a fast and powerful management tool for Mercurial_ and GIT_
with a built in push/pull server, full text search and code-review.
It works on http/https and has a built in permission/authentication system with
the ability to authenticate via LDAP or ActiveDirectory. RhodeCode also provides
simple API so it's easy integrable with existing external systems.

RhodeCode is similar in some respects to github_ or bitbucket_,
however RhodeCode can be run as standalone hosted application on your own server.
It is open source and donation ware and focuses more on providing a customized,
self administered interface for Mercurial_ and GIT_  repositories.
RhodeCode works on \*nix systems and Windows it is powered by a vcs_ library
that Lukasz Balcerzak and Marcin Kuzminski created to handle multiple
different version control systems.

RhodeCode uses `PEP386 versioning <http://www.python.org/dev/peps/pep-0386/>`_

Installation
------------
Stable releases of RhodeCode are best installed via::

    pip install https://rhodecode.com/dl/latest

Detailed instructions and links may be found on the Installation page.

Please visit https://rhodecode.com/docs/installation.html for more details


Source code
-----------

The latest sources can be obtained from official RhodeCode instance
https://secure.rhodecode.org


RhodeCode Features
------------------

Check out all features of RhodeCode at https://rhodecode.com/features

License
-------

``RhodeCode`` is released under the GPLv3 license. Please see
LICENSE file for details


Getting help
------------

Listed bellow are various support resources that should help.

.. note::

   Please try to read the documentation before posting any issues, especially
   the **troubleshooting section**

- Search the `Knowledge base <https://rhodecode.com/help/dashboard/kb>`_ for
  known issues or problems.

- Search the old `Discussion group <http://groups.google.com/group/rhodecode>`_ for
  known issues or problems. (Depracated)

- Open an issue at `support page <https://rhodecode.com/help>`_

- Join #rhodecode on FreeNode (irc.freenode.net)
  or use http://webchat.freenode.net/?channels=rhodecode for web access to irc.

- You can also follow RhodeCode on twitter **@RhodeCode** where we often post
  news and other interesting stuff about RhodeCode.


Online documentation
--------------------

Online documentation for the current version of RhodeCode is available at
 - http://rhodecode.com/docs

You may also build the documentation for yourself - go into ``docs/`` and run::

   make html

(You need to have sphinx_ installed to build the documentation. If you don't
have sphinx_ installed you can install it via the command:
``pip install sphinx``)

.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _python: http://www.python.org/
.. _sphinx: http://sphinx.pocoo.org/
.. _mercurial: http://mercurial.selenic.com/
.. _bitbucket: http://bitbucket.org/
.. _github: http://github.com/
.. _subversion: http://subversion.tigris.org/
.. _git: http://git-scm.com/
.. _celery: http://celeryproject.org/
.. _vcs: http://pypi.python.org/pypi/vcs
