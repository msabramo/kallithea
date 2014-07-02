.. _contributing:

=========================
Contributing to Kallithea
=========================

If you would like to contribute to Kallithea, please contact us, any help is
greatly appreciated!

Could I request that you make your source contributions by first forking the
Kallithea repository on bitbucket_
https://bitbucket.org/conservancy/kallithea and then make your changes to
your forked repository. Please post all fixes into **dev** bookmark since your
change might be already fixed there and i try to merge all fixes from dev into
stable, and not the other way. Finally, when you are finished with your changes,
please send us a pull request.

To run Kallithea in a development version you always need to install the latest
required libs. Simply clone Kallithea and switch to beta branch::

    hg clone https://kallithea-scm.org/repos/kallithea

after downloading/pulling Kallithea make sure you run::

    python setup.py develop

command to install/verify all required packages, and prepare development
enviroment.

There are two files in the directory production.ini and developement.ini copy
the `development.ini` file as rc.ini (which is excluded from version controll)
and put all your changes like db connection or server port in there.

After finishing your changes make sure all tests passes ok. You can run
the testsuite running ``nosetest`` from the project root, or if you use tox
run tox for python2.5-2.7 with multiple database test. When using `nosetests`
test.ini file is used and by default it uses sqlite for tests, edit this file
to change your testing enviroment.


There's a special set of tests for push/pull operations, you can runn them using::

    paster serve test.ini --pid-file=test.pid --daemon
    RC_WHOOSH_TEST_DISABLE=1 RC_NO_TMP_PATH=1 nosetests -x kallithea/tests/other/test_vcs_operations.py
    kill -9 $(cat test.pid)


| Thank you for any contributions!


.. _bitbucket: http://bitbucket.org/
