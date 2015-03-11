.. _subrepos:

=============================================
Working with Kallithea and Mercurial subrepos
=============================================

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


In the file list of a clone of repo1 you will see a connected subrepo at
revision it was during cloning.
Clicking in subrepos link should send you to proper repository in Kallithea.

Cloning repo1 will also clone attached subrepository.

Next we can edit the subrepo data, and push back to Kallithea. This will update
both of repositories.

See http://mercurial.aragost.com/kick-start/en/subrepositories/ for more
information about subrepositories.
