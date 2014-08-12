#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import os
import sys
import platform

if sys.version_info < (2, 5):
    raise Exception('Kallithea requires python 2.5 or later')


here = os.path.abspath(os.path.dirname(__file__))


def _get_meta_var(name, data, callback_handler=None):
    import re
    matches = re.compile(r'(?:%s)\s*=\s*(.*)' % name).search(data)
    if matches:
        if not callable(callback_handler):
            callback_handler = lambda v: v

        return callback_handler(eval(matches.groups()[0]))

_meta = open(os.path.join(here, 'kallithea', '__init__.py'), 'rb')
_metadata = _meta.read()
_meta.close()

callback = lambda V: ('.'.join(map(str, V[:3])) + '.'.join(V[3:]))
__version__ = _get_meta_var('VERSION', _metadata, callback)
__license__ = _get_meta_var('__license__', _metadata)
__author__ = _get_meta_var('__author__', _metadata)
__url__ = _get_meta_var('__url__', _metadata)
# defines current platform
__platform__ = platform.system()

is_windows = __platform__ in ['Windows']

requirements = [
    "waitress==0.8.8",
    "webob==1.0.8",
    "webtest==1.4.3",
    "Pylons==1.0.0",
    "Beaker==1.6.4",
    "WebHelpers==1.3",
    "formencode>=1.2.4,<=1.2.6",
    "SQLAlchemy==0.7.10",
    "Mako>=0.9.0,<=1.0.0",
    "pygments>=1.5",
    "whoosh>=2.4.0,<=2.5.7",
    "celery>=2.2.5,<2.3",
    "babel>=0.9.6,<=1.3",
    "python-dateutil>=1.5.0,<2.0.0",
    "dulwich>=0.9.3,<=0.9.7",
    "markdown==2.2.1",
    "docutils>=0.8.1,<=0.11",
    "simplejson==2.5.2",
    "mock",
    "pycrypto>=2.6.0,<=2.6.1",
    "URLObject==2.3.4",
    "Routes==1.13",
]

if sys.version_info < (2, 6):
    requirements.append("pysqlite")

if sys.version_info < (2, 7):
    requirements.append("importlib==1.0.1")
    requirements.append("unittest2")
    requirements.append("argparse")

if is_windows:
    requirements.append("mercurial>=2.8.2,<3.2")
else:
    requirements.append("py-bcrypt>=0.3.0,<=0.4")
    requirements.append("mercurial>=2.8.2,<3.2")


dependency_links = [
]

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Framework :: Pylons',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Software Development :: Version Control',
]


# additional files from project that goes somewhere in the filesystem
# relative to sys.prefix
data_files = []

# additional files that goes into package itself
package_data = {'kallithea': ['i18n/*/LC_MESSAGES/*.mo', ], }

description = ('Kallithea is a fast and powerful management tool '
               'for Mercurial and GIT with a built in push/pull server, '
               'full text search and code-review.')

keywords = ' '.join([
    'kallithea', 'mercurial', 'git', 'code review',
    'repo groups', 'ldap', 'repository management', 'hgweb replacement',
    'hgwebdir', 'gitweb replacement', 'serving hgweb',
])

# long description
README_FILE = 'README.rst'
CHANGELOG_FILE = 'docs/changelog.rst'
try:
    long_description = open(README_FILE).read() + '\n\n' + \
        open(CHANGELOG_FILE).read()

except IOError, err:
    sys.stderr.write(
        "[WARNING] Cannot find file specified as long_description (%s)\n or "
        "changelog (%s) skipping that file" % (README_FILE, CHANGELOG_FILE)
    )
    long_description = description

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
# packages
packages = find_packages(exclude=['ez_setup'])

setup(
    name='Kallithea',
    version=__version__,
    description=description,
    long_description=long_description,
    keywords=keywords,
    license=__license__,
    author=__author__,
    author_email='kallithea@sfconservancy.org',
    dependency_links=dependency_links,
    url=__url__,
    install_requires=requirements,
    classifiers=classifiers,
    setup_requires=["PasteScript>=1.6.3"],
    data_files=data_files,
    packages=packages,
    include_package_data=True,
    test_suite='nose.collector',
    package_data=package_data,
    message_extractors={'kallithea': [
            ('**.py', 'python', None),
            ('templates/**.mako', 'mako', {'input_encoding': 'utf-8'}),
            ('templates/**.html', 'mako', {'input_encoding': 'utf-8'}),
            ('public/**', 'ignore', None)]},
    zip_safe=False,
    paster_plugins=['PasteScript', 'Pylons'],
    entry_points="""
    [console_scripts]
    kallithea-api =    kallithea.bin.kallithea_api:main
    kallithea-gist =   kallithea.bin.kallithea_gist:main
    kallithea-config = kallithea.bin.kallithea_config:main

    [paste.app_factory]
    main = kallithea.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller

    [paste.global_paster_command]
    setup-db=kallithea.lib.paster_commands.setup_db:Command
    update-repoinfo=kallithea.lib.paster_commands.update_repoinfo:Command
    make-rcext=kallithea.lib.paster_commands.make_rcextensions:Command
    repo-scan=kallithea.lib.paster_commands.repo_scan:Command
    cache-keys=kallithea.lib.paster_commands.cache_keys:Command
    ishell=kallithea.lib.paster_commands.ishell:Command
    make-index=kallithea.lib.paster_commands.make_index:Command
    upgrade-db=kallithea.lib.dbmigrate:UpgradeDb
    celeryd=kallithea.lib.celerypylons.commands:CeleryDaemonCommand
    """,
)
