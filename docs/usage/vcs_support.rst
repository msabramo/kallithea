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
Example usage of Subrepos with Kallithea::

    ## init a simple repo
    hg init repo1
    cd repo1
    echo "file1" > file1
    hg add file1
    hg ci --message "initial file 1"

    #clone subrepo we want to add
    hg clone http://kallithea.local/subrepo

    ## use path like url to existing repo in Kallithea
    echo "subrepo = http://kallithea.local/subrepo" > .hgsub

    hg add .hgsub
    hg ci --message "added remote subrepo"


In the file list of a clone of ``repo1`` you will see a connected
subrepo at the revision it was at during cloning. Clicking in
subrepos link should send you to the proper repository in Kallithea.

Cloning ``repo1`` will also clone the attached subrepository.

Next we can edit the subrepo data, and push back to Kallithea. This will update
both of the repositories.

See http://mercurial.aragost.com/kick-start/en/subrepositories/ for more
information about subrepositories.

.. _waitress: http://pypi.python.org/pypi/waitress
.. _gunicorn: http://pypi.python.org/pypi/gunicorn
