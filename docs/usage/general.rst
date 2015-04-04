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

File view: follow current branch
--------------------------------

In the file view, left and right arrows allow to jump to the previous and next
revision. Depending on the way revisions were created in the repository, this
could jump to a different branch.  When the checkbox ``Follow current branch``
is checked, these arrows will only jump to revisions on the same branch as the
currently visible revision.  So for example, if someone is viewing files in the
``beta`` branch and marks the `Follow current branch` checkbox, the < and >
arrows will only show revisions on the ``beta`` branch.


Changelog features
------------------

The core feature of a repository's ``changelog`` page is to show the revisions
in a repository. However, there are several other features available from the
changelog.

Branch filter
  By default, the changelog shows revisions from all branches in the
  repository. Use the branch filter to restrict to a given branch.

Viewing a changeset
  A particular changeset can be opened by clicking on either the changeset
  hash or the commit message, or by ticking the checkbox and clicking the
  ``Show selected changeset`` button at the top.

Viewing all changes between two changesets
  To get a list of all changesets between two selected changesets, along with
  the changes in each one of them, tick the checkboxes of the first and
  last changeset in the desired range and click the ``Show selected changesets``
  button at the top. You can only show the range between the first and last
  checkbox (no cherry-picking).

  From that page, you can proceed to viewing the overall delta between the
  selected changesets, by clicking the ``Compare revisions`` button.

Creating a pull request
  You can create a new pull request for the changes of a particular changeset
  (and its ancestors) by selecting it and clicking the ``Open new pull request
  for selected changesets`` button.

Permanent repository URLs
-------------------------

Due to the complicated nature of repository grouping, URLs of repositories
can often change. For example, a repository originally accessible from::

  http://server.com/repo_name

would get a new URL after moving it to test_group::

  http://server.com/test_group/repo_name

Such moving of a repository to a group can be an issue for build systems and
other scripts where the repository paths are hardcoded. To mitigate this,
Kallithea provides permanent URLs using the repository ID prefixed with an
underscore. In all Kallithea URLs, for example those for the changelog and the
file view, a repository name can be replaced by this ``_ID`` string. Since IDs
are always the same, moving the repository to a different group will not affect
such URLs.

In the example, the repository could also be accessible as::

  http://server.com/_<ID>

The ID of a given repository can be shown from the repository ``Summary`` page,
by selecting the ``Show by ID`` button next to ``Clone URL``.

E-mail notifications
--------------------

When the administrator correctly specified the e-mail settings in the Kallithea
configuration file, Kallithea will send e-mails on user registration and when
errors occur.

Mails are also sent for comments on changesets. In this case, an e-mail is sent
to the committer of the changeset (if known to Kallithea), to all reviewers of
the pull request (if applicable) and to all people mentioned in the comment
using @mention notation.


Trending source files
---------------------

Trending source files are calculated based on a predefined dictionary of known
types and extensions. If an extension is missing or you would like to scan
custom files, it is possible to extend the ``LANGUAGES_EXTENSIONS_MAP``
dictionary located in ``kallithea/config/conf.py`` with new types.


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



Specific features configurable in the Admin settings
----------------------------------------------------

In general, the Admin settings should be self-explanatory and will not be
described in more detail in this documentation. However, there are a few
features that merit further explanation.

Repository extra fields
~~~~~~~~~~~~~~~~~~~~~~~

In the `Visual` tab, there is an option `Use repository extra
fields`, which allows to set custom fields for each repository in the system.
Each new field consists of 3 attributes: ``field key``, ``field label``,
``field description``.

Example usage of such fields would be to define company-specific information
into repositories, e.g., defining a ``repo_manager`` key that would give info
about a manager of each repository.  There's no limit for adding custom fields.
Newly created fields are accessible via the API.

Meta-Tagging
~~~~~~~~~~~~

In the `Visual` tab, option `Stylify recognised meta tags` will cause Kallithea
to turn certain meta-tags, detected in repository and repository group
descriptions, into colored tags. Currently recognised tags are::

    [featured]
    [stale]
    [dead]
    [lang => lang]
    [license => License]
    [requires => Repo]
    [recommends => Repo]
    [see => URI]
