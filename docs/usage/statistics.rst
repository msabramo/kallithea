.. _statistics:

=====================
Repository statistics
=====================

Kallithea has a ``repository statistics`` feature, disabled by default. When
enabled, the amount of commits per committer is visualized in a timeline. This
feature can be enabled using the ``Enable statistics`` checkbox on the
repository ``Settings`` page.

The statistics system makes heavy demands on the server resources, so
in order to keep a balance between usability and performance, statistics are
cached inside the database and gathered incrementally.

When Celery is disabled:

  On each first visit to the summary page a set of 250 commits are parsed and
  added to the statistics cache. This incremental gathering also happens on each
  visit to the statistics page, until all commits are fetched.

  Statistics are kept cached until additional commits are added to the
  repository. In such a case Kallithea will only fetch the new commits when
  updating its statistics cache.

When Celery is enabled:

  On the first visit to the summary page, Kallithea will create tasks that will
  execute on Celery workers. These tasks will gather all of the statistics until
  all commits are parsed. Each task parses 250 commits, then launches a new
  task.
