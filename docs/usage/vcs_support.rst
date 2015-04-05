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


Mercurial support
-----------------

Working with Mercurial subrepositories
``````````````````````````````````````
This section explains how to use Mercurial subrepositories_ in Kallithea.

Example usage::

    ## init a simple repo
    hg init mainrepo
    cd mainrepo
    echo "file" > file
    hg add file
    hg ci --message "initial file"

    # clone subrepo we want to add from Kallithea
    hg clone http://kallithea.local/subrepo

    ## specify URL to existing repo in Kallithea as subrepository path
    echo "subrepo = http://kallithea.local/subrepo" > .hgsub
    hg add .hgsub
    hg ci --message "added remote subrepo"

In the file list of a clone of ``mainrepo`` you will see a connected
subrepository at the revision it was cloned with. Clicking on the
subrepository link sends you to the proper repository in Kallithea.

Cloning ``mainrepo`` will also clone the attached subrepository.

Next we can edit the subrepository data, and push back to Kallithea. This will
update both repositories.

.. _waitress: http://pypi.python.org/pypi/waitress
.. _gunicorn: http://pypi.python.org/pypi/gunicorn
.. _subrepositories: http://mercurial.aragost.com/kick-start/en/subrepositories/
