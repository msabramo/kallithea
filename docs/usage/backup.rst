.. _backup:

====================
Backing up Kallithea
====================


Settings
--------

Just copy your .ini file, it contains all Kallithea settings.

Whoosh index
------------

Whoosh index is located in **/data/index** directory where you installed
Kallithea ie. the same place where the ini file is located


Database
--------

When using sqlite just copy kallithea.db.
Any other database engine requires a manual backup operation.

Database backup will contain all gathered statistics
