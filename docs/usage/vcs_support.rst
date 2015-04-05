.. _vcs_support:

===============================
Version control systems support
===============================

Kallithea supports Git and Mercurial repositories out-of-the-box.
For Git, you do need the ``git`` command line client installed on the server.

You can always disable Git or Mercurial support by editing the
file ``kallithea/__init__.py`` and commenting out the backend.

.. code-block:: python

   BACKENDS = {
       'hg': 'Mercurial repository',
       #'git': 'Git repository',
   }

Git support
-----------

Web server with chunked encoding
````````````````````````````````
Large Git pushes require an HTTP server with support for
chunked encoding for POST. The Python web servers waitress_ and
gunicorn_ (Linux only) can be used. By default, Kallithea uses
waitress_ for `paster serve` instead of the built-in `paste` WSGI
server.

The default paste server is controlled in the .ini file::

    use = egg:waitress#main

or::

    use = egg:gunicorn#main


Also make sure to comment out the following options::

    threadpool_workers =
    threadpool_max_requests =
    use_threadpool =



.. _waitress: http://pypi.python.org/pypi/waitress
.. _gunicorn: http://pypi.python.org/pypi/gunicorn
