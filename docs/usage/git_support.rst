.. _git_support:

===========
GIT support
===========


Kallithea Git support is enabled by default. You just need a git
command line client installed on the server to make Git work fully.

Web server with chunked encoding
--------------------------------

Large Git pushes do however require a http server with support for chunked encoding for POST.

The Python web servers waitress_ and gunicorn_ (linux only) can be used.
By default, Kallithea uses waitress_ for `paster serve` instead of the built-in `paste` WSGI server. 

The default paste server is controlled in the .ini file::

    use = egg:waitress#main

or::

    use = egg:gunicorn#main


Also make sure to comment out the following options::

    threadpool_workers =
    threadpool_max_requests =
    use_threadpool =


Disabling Git
-------------

You can always disable git/hg support by editing a
file **kallithea/__init__.py** and commenting out the backend.

.. code-block:: python

   BACKENDS = {
       'hg': 'Mercurial repository',
       #'git': 'Git repository',
   }

.. _waitress: http://pypi.python.org/pypi/waitress
.. _gunicorn: http://pypi.python.org/pypi/gunicorn
