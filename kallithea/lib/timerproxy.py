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

import time
import logging
from sqlalchemy.interfaces import ConnectionProxy

log = logging.getLogger('timerproxy')

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = xrange(30, 38)


def color_sql(sql):
    COLOR_SEQ = "\033[1;%dm"
    COLOR_SQL = YELLOW
    normal = '\x1b[0m'
    return ''.join([COLOR_SEQ % COLOR_SQL, sql, normal])


class TimerProxy(ConnectionProxy):

    def __init__(self):
        super(TimerProxy, self).__init__()

    def cursor_execute(self, execute, cursor, statement, parameters,
                       context, executemany):

        now = time.time()
        try:
            log.info(color_sql(">>>>> STARTING QUERY >>>>>"))
            return execute(cursor, statement, parameters, context)
        finally:
            total = time.time() - now
            log.info(color_sql("<<<<< TOTAL TIME: %f <<<<<" % total))
