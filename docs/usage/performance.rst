.. _performance:

================================
Optimizing Kallithea Performance
================================

When serving a large amount of big repositories, Kallithea can start
performing slower than expected. Because of the demanding nature of handling large
amounts of data from version control systems, here are some tips on how to get
the best performance.

* Kallithea will perform better on machines with faster disks (SSD/SAN). It's
  more important to have a faster disk than a faster CPU.

* Slowness on initial page can be easily fixed by grouping repositories, and/or
  increasing cache size (see below). This includes using the lightweight dashboard
  option and ``vcs_full_cache`` setting in .ini file


Follow these few steps to improve performance of Kallithea system.


1. Increase cache

    In the .ini file::

     beaker.cache.sql_cache_long.expire=3600 <-- set this to higher number

    This option affects the cache expiration time for the main
    page. Having several hundreds of repositories on main page can
    sometimes make the system behave slowly when the cache expires for
    all of them. Increasing the ``expire`` option to a day (86400) or a
    week (604800) will improve general response times for the main
    page. Kallithea has an intelligent cache expiration system and it
    will expire the cache for repositories that have been changed.

2. Switch from sqlite to postgres or mysql

    sqlite is a good option when having a small load on the system. But due to
    locking issues with sqlite, it is not recommended to use it for larger
    deployments. Switching to mysql or postgres will result in an immediate
    performance increase.

3. Scale Kallithea horizontally

    Scaling horizontally can give huge performance increases when dealing with
    large traffic (large amount of users, CI servers etc). Kallithea can be
    scaled horizontally on one (recommended) or multiple machines. In order
    to scale horizontally you need to do the following:

    - Each instance needs its own .ini file and unique ``instance_id`` set.
    - Each instance's ``data`` storage needs to be configured to be stored on a
      shared disk storage, preferably together with repositories. This ``data``
      dir contains template caches, sessions, whoosh index and is used for
      task locking (so it is safe across multiple instances). Set the
      ``cache_dir``, ``index_dir``, ``beaker.cache.data_dir``, ``beaker.cache.lock_dir``
      variables in each .ini file to a shared location across Kallithea instances
    - If celery is used each instance should run a separate Celery instance, but
      the message broker should be common to all of them (e.g.,  one
      shared RabbitMQ server)
    - Load balance using round robin or IP hash, recommended is writing LB rules
      that will separate regular user traffic from automated processes like CI
      servers or build bots.
