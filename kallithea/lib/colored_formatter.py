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

import logging

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = xrange(30, 38)

# Sequences
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[0;%dm"
BOLD_SEQ = "\033[1m"

COLORS = {
    'CRITICAL': MAGENTA,
    'ERROR': RED,
    'WARNING': CYAN,
    'INFO': GREEN,
    'DEBUG': BLUE,
    'SQL': YELLOW
}


def one_space_trim(s):
    if s.find("  ") == -1:
        return s
    else:
        s = s.replace('  ', ' ')
        return one_space_trim(s)


def format_sql(sql):
    sql = sql.replace('\n', '')
    sql = one_space_trim(sql)
    sql = sql\
        .replace(',', ',\n\t')\
        .replace('SELECT', '\n\tSELECT \n\t')\
        .replace('UPDATE', '\n\tUPDATE \n\t')\
        .replace('DELETE', '\n\tDELETE \n\t')\
        .replace('FROM', '\n\tFROM')\
        .replace('ORDER BY', '\n\tORDER BY')\
        .replace('LIMIT', '\n\tLIMIT')\
        .replace('WHERE', '\n\tWHERE')\
        .replace('AND', '\n\tAND')\
        .replace('LEFT', '\n\tLEFT')\
        .replace('INNER', '\n\tINNER')\
        .replace('INSERT', '\n\tINSERT')\
        .replace('DELETE', '\n\tDELETE')
    return sql


class ColorFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        # can't do super(...) here because Formatter is an old school class
        logging.Formatter.__init__(self, *args, **kwargs)

    def format(self, record):
        """
        Changes record's levelname to use with COLORS enum
        """

        levelname = record.levelname
        start = COLOR_SEQ % (COLORS[levelname])
        def_record = logging.Formatter.format(self, record)
        end = RESET_SEQ

        colored_record = ''.join([start, def_record, end])
        return colored_record


class ColorFormatterSql(logging.Formatter):

    def __init__(self, *args, **kwargs):
        # can't do super(...) here because Formatter is an old school class
        logging.Formatter.__init__(self, *args, **kwargs)

    def format(self, record):
        """
        Changes record's levelname to use with COLORS enum
        """

        start = COLOR_SEQ % (COLORS['SQL'])
        def_record = format_sql(logging.Formatter.format(self, record))
        end = RESET_SEQ

        colored_record = ''.join([start, def_record, end])
        return colored_record
