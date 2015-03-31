.. _backup:

====================
Backing up Kallithea
====================


Settings
--------

Just copy your .ini file, it contains all Kallithea settings.

Whoosh index
------------

The Whoosh index is located in the ``data/index`` directory where you installed
Kallithea, i.e., the same place where the ini file is located


Database
--------

When using sqlite just copy kallithea.db.
Any other database engine requires a manual backup operation.

A database backup will contain all gathered statistics.
