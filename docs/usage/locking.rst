.. _locking:

==================
Repository locking
==================

Kallithea has a ``repository locking`` feature, disabled by default. When
enabled, every initial clone and every pull gives users (with write permission)
the exclusive right to do a push.

When repository locking is enabled, repositories get a ``locked`` state that
can be true or false.  The hg/git commands ``hg/git clone``, ``hg/git pull``,
and ``hg/git push`` influence this state:

- A ``clone`` or ``pull`` action on the repository locks it (``locked=true``)
  if the user has write/admin permissions on this repository.

- Kallithea will remember the user who locked the repository so only this
  specific user can unlock the repo (``locked=false``) by performing a ``push``
  command.

- Every other command on a locked repository from this user and every command
  from any other user will result in an HTTP return code 423 (Locked).
  Additionally, the HTTP error includes the <user> that locked the repository
  (e.g., “repository <repo> locked by user <user>”).

Each repository can be manually unlocked by an administrator from the
repository settings menu.
