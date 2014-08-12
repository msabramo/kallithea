# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
kallithea.config.conf
~~~~~~~~~~~~~~~~~~~~~

Various config settings for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Mar 7, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from kallithea.lib.utils2 import __get_lem


# language map is also used by whoosh indexer, which for those specified
# extensions will index it's content
LANGUAGES_EXTENSIONS_MAP = __get_lem()

#==============================================================================
# WHOOSH INDEX EXTENSIONS
#==============================================================================
# EXTENSIONS WE WANT TO INDEX CONTENT OFF USING WHOOSH
INDEX_EXTENSIONS = LANGUAGES_EXTENSIONS_MAP.keys()

# list of readme files to search in file tree and display in summary
# attached weights defines the search  order lower is first
ALL_READMES = [
    ('readme', 0), ('README', 0), ('Readme', 0),
    ('doc/readme', 1), ('doc/README', 1), ('doc/Readme', 1),
    ('Docs/readme', 2), ('Docs/README', 2), ('Docs/Readme', 2),
    ('DOCS/readme', 2), ('DOCS/README', 2), ('DOCS/Readme', 2),
    ('docs/readme', 2), ('docs/README', 2), ('docs/Readme', 2),
]

# extension together with weights to search lower is first
RST_EXTS = [
    ('', 0), ('.rst', 1), ('.rest', 1),
    ('.RST', 2), ('.REST', 2),
    ('.txt', 3), ('.TXT', 3)
]

MARKDOWN_EXTS = [
    ('.md', 1), ('.MD', 1),
    ('.mkdn', 2), ('.MKDN', 2),
    ('.mdown', 3), ('.MDOWN', 3),
    ('.markdown', 4), ('.MARKDOWN', 4)
]

PLAIN_EXTS = [('.text', 2), ('.TEXT', 2)]

ALL_EXTS = MARKDOWN_EXTS + RST_EXTS + PLAIN_EXTS

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

DATE_FORMAT = "%Y-%m-%d"
