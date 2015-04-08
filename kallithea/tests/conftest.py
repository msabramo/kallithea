import os
import sys

import pkg_resources
from paste.deploy import loadapp
import pylons.test


def pytest_configure():
    path = os.getcwd()
    sys.path.insert(0, path)
    pkg_resources.working_set.add_entry(path)
    pylons.test.pylonsapp = loadapp('config:test.ini', relative_to=path)
    return pylons.test.pylonsapp
