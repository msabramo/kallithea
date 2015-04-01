.. _general:

=======================
General Kallithea usage
=======================


Repository deleting
-------------------

Currently when an admin or owner deletes a repository, Kallithea does
not physically delete said repository from the filesystem, but instead
renames it in a special way so that it is not possible to push, clone
or access the repository.

There is a special command for cleaning up such archived repos::

    paster cleanup-repos --older-than=30d my.ini

This command scans for archived repositories that are older than
30 days, displays them, and asks if you want to delete them (unless given
the ``--dont-ask`` flag). If you host a large amount of repositories with
forks that are constantly being deleted, it is recommended that you run this
command via crontab.

It is worth noting that even if someone is given administrative access to
Kallithea and deletes a repository, you can easily restore such an action by
renaming the repository directory, removing the ``rm__<date>`` prefix.

Follow current branch in file view
----------------------------------

In file view when this checkbox is checked the << and >> arrows will jump
to changesets within the same branch currently being viewed. So for example
if someone is viewing files in the ``beta`` branch and marks the `follow current branch`
checkbox the << and >> buttons will only show revisions for the `'beta`` branch.


Compare view from changelog
---------------------------

Checkboxes in the compare view allow users to view a combined compare
view. You can only show the range between the first and last checkbox
(no cherry pick).  Clicking more than one checkbox will activate a
link at the top saying ``Show selected changesets <from-rev> ->
<to-rev>``. Clicking this will activate the compare view. In this view
it is also possible to switch to combined compare.

Compare view is also available from the journal on pushes having more than
one changeset.


Non changeable repository urls
------------------------------

Due to the complicated nature of repository grouping, URLs of repositories
can often change.

example::

  #before
  http://server.com/repo_name
  # after insertion to test_group group the url will be
  http://server.com/test_group/repo_name

This can be an issue for build systems and any other hardcoded scripts, moving
a repository to a group leads to a need for changing external systems. To
overcome this Kallithea introduces a non-changable replacement URL. It's
simply a repository ID prefixed with ``_``. The above URLs are also accessible as::

  http://server.com/_<ID>

Since IDs are always the same, moving the repository will not affect
such a URL.  the ``_<ID>`` syntax can be used anywhere in the system so
URLs with ``repo_name`` for changelogs and files can be exchanged
with the ``_<ID>`` syntax.


Mailing
-------

When the administrator configures the mailing settings in .ini files
Kallithea will send mails on user registration, or when Kallithea
errors occur.

Mails are also sent for code comments. If someone comments on a changeset
mail is sent to all participants, the person who commited the changeset
(if present in Kallithea), and to all people mentioned with the @mention system.


Trending source files
---------------------

Trending source files are calculated based on a pre-defined dict of known
types and extensions. If you miss some extension or would like to scan some
custom files, it is possible to add new types in the ``LANGUAGES_EXTENSIONS_MAP`` dict
located in ``kallithea/lib/celerylib/tasks.py``.


Cloning remote repositories
---------------------------

Kallithea has the ability to clone remote repos from given remote locations.
Currently it supports the following options:

- hg  -> hg clone
- svn -> hg clone
- git -> git clone


.. note:: svn -> hg cloning requires tge ``hgsubversion`` library to be installed.

If you need to clone repositories that are protected via basic auth, you
might pass the url with stored credentials inside, e.g.,
``http://user:passw@remote.server/repo``, Kallithea will try to login and clone
using the given credentials. Please take note that they will be stored as
plaintext inside the database. Kallithea will remove auth info when showing the
clone url in summary page.



Visual settings in admin pannel
-------------------------------


Visualisation settings in Kallithea settings view are extra customizations
of server behavior. There are 3 main sections in the settings.

General
~~~~~~~

The `Use repository extra fields` option allows to set a custom fields
for each repository in the system. Each new field consists of 3
attributes: ``field key``, ``field label``, ``field
description``. Example usage of such fields would be to define company
specific information into repositories, e.g., defining a
``repo_manager`` key that would give info about a manager of each
repository. There's no limit for adding custom fields. Newly created
fields are accessible via API.

The `Show Kallithea version` option toggles displaying the exact
Kallithea version in the footer


Dashboard items
~~~~~~~~~~~~~~~

Number of items in main page dashboard before pagination is displayed.


Icons
~~~~~

Show public repo icon / Show private repo icon on repositories - defines if
public/private icons should be shown in the UI.


Meta-Tagging
~~~~~~~~~~~~

With this option enabled, special metatags that are recognisible by Kallithea
will be turned into colored tags. Currently available tags are::

    [featured]
    [stale]
    [dead]
    [lang => lang]
    [license => License]
    [requires => Repo]
    [recommends => Repo]
    [see => URI]
