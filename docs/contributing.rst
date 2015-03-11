.. _contributing:

=========================
Contributing to Kallithea
=========================

Kallithea is developed and maintained by its users. Please join us and scratch
your own itch.


Infrastructure
--------------

The main repository is hosted at Our Own Kallithea (aka OOK) on
https://kallithea-scm.org/repos/kallithea/ (which is our self-hosted instance
of Kallithea).

For now, we use Bitbucket_ for `Pull Requests`_ and `Issue Tracker`_ services. The
issue tracker is for tracking bugs, not for "support", discussion or ideas -
please use the `mailing list`_ to reach the community.

We use Weblate_ to translate the user interface messages into languages other
than English. Join our project on `Hosted Weblate`_ to help us.
To register, you can use your Bitbucket or GitHub account.


Getting started
---------------

To get started with development::

        hg clone https://kallithea-scm.org/repos/kallithea
        cd kallithea
        virtualenv ../kallithea-venv
        source ../kallithea-venv/bin/activate
        python setup.py develop
        paster make-config Kallithea my.ini
        paster setup-db my.ini --user=user --email=user@example.com --password=password --repos=/tmp
        paster serve my.ini --reload &
        firefox http://127.0.0.1:5000/

You can also start out by forking https://bitbucket.org/conservancy/kallithea
on Bitbucket_ and create a local clone of your own fork.


Running tests
-------------

After finishing your changes make sure all tests pass cleanly. You can run
the testsuite running ``nosetest`` from the project root, or if you use tox
run tox for python2.6-2.7 with multiple database test. When using `nosetests`
test.ini file is used and by default it uses sqlite for tests, edit this file
to change your testing enviroment.

There's a special set of tests for push/pull operations, you can runn them using::

    paster serve test.ini --pid-file=test.pid --daemon
    KALLITHEA_WHOOSH_TEST_DISABLE=1 KALLITHEA_NO_TMP_PATH=1 nosetests -x kallithea/tests/other/test_vcs_operations.py
    kill -9 $(cat test.pid)


Coding/contribution guidelines
------------------------------

Kallithea is GPLv3 and we assume all contributions are made by the
committer/contributor and under GPLv3 unless explicitly stated. We do care a
lot about preservation of copyright and license information for existing code
that is brought into the project.

We don't have a formal coding/formatting standard. We are currently using a mix
of Mercurial (http://mercurial.selenic.com/wiki/CodingStyle), pep8, and
consistency with existing code. Run whitespacecleanup.sh to avoid stupid
whitespace noise in your patches.

We support both Python 2.6.x and 2.7.x and nothing else. For now we don't care
about Python 3 compatibility.

We try to support the most common modern web browsers. IE8 is still supported
to the extent it is feasible but we may stop supporting it very soon.

We primarily support Linux and OS X on the server side but Windows should also work.

Html templates should use 2 spaces for indentation ... but be pragmatic. We
should use templates cleverly and avoid duplication. We should use reasonable
semantic markup with classes and ids that can be used for styling and testing.
We should only use inline styles in places where it really is semantic (such as
display:none).

JavaScript must use ';' between/after statements. Indentation 4 spaces. Inline
multiline functions should be indented two levels - one for the () and one for
{}. jQuery value arrays should have a leading $.

Commit messages should have a leading short line summarizing the changes. For
bug fixes, put "(Issue #123)" at the end of this line.

Contributions will be accepted in most formats - such as pull requests on
bitbucket, something hosted on your own Kallithea instance, or patches sent by
mail to the kallithea-general mailing list.

Make sure to test your changes both manually and with the automatic tests
before posting.

We care about quality and review and keeping a clean repository history. We
might give feedback that requests polishing contributions until they are
"perfect". We might also rebase and collapse and make minor adjustments to your
changes when we apply them.

We try to make sure we have consensus on the direction the project is taking.
Everything non-sensitive should be discussed in public - preferably on the
mailing list.  We aim at having all non-trivial changes reviewed by at least
one other core developer before pushing. Obvious non-controversial changes will
be handled more casually.

For now we just have one official branch ("default") and will keep it so stable
that it can be (and is) used in production. Experimental changes should live
elsewhere (for example in a pull request) until they are ready.


"Roadmap"
---------

We do not have a road map but are waiting for your contributions. Here are some
ideas of places we might want to go - contributions in these areas are very
welcome:

* Front end:
    * kill YUI - more jQuery
    * remove other dependencies - especially the embedded cut'n'pasted ones
    * remove hardcoded styling in templates, make markup more semantic while moving all styling to css
    * switch to bootstrap or some other modern UI library and cleanup of style.css and contextbar.css
    * new fancy style that looks good
* testing
    * better test coverage with the existing high level test framework
    * test even more high level and javascript - selenium/robot and splinter seems like the top candidates
    * more unit testing
* code cleanup
    * move code from templates to controllers and from controllers to libs or models
    * more best practice for web apps and the frameworks
* features
    * relax dependency version requirements after thorough testing
    * support for evolve
    * updates of PRs ... while preserving history and comment context
    * auto pr merge/rebase
    * ssh
    * bitbucket compatible wiki
    * realtime preview / wysiwyg when editing comments and files
    * make journal more useful - filtering on branches and files
    * community mode with self registration and personal space
    * improve documentation

Thank you for your contribution!
--------------------------------


.. _Weblate: http://weblate.org/
.. _Issue Tracker: https://bitbucket.org/conservancy/kallithea/issues?status=new&status=open
.. _Pull Requests: https://bitbucket.org/conservancy/kallithea/pull-requests
.. _bitbucket: http://bitbucket.org/
.. _mailing list: http://lists.sfconservancy.org/mailman/listinfo/kallithea-general
.. _Hosted Weblate: https://hosted.weblate.org/projects/kallithea/kallithea/
