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
kallithea.lib.celerylib.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

celery libs for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 27, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import socket
import traceback
import logging
from os.path import join as jn
from pylons import config

from hashlib import md5
from decorator import decorator

from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea import CELERY_ON, CELERY_EAGER
from kallithea.lib.utils2 import str2bool, safe_str
from kallithea.lib.pidlock import DaemonLock, LockHeld
from kallithea.model import init_model
from kallithea.model import meta

from sqlalchemy import engine_from_config


log = logging.getLogger(__name__)


class ResultWrapper(object):
    def __init__(self, task):
        self.task = task

    @LazyProperty
    def result(self):
        return self.task


def run_task(task, *args, **kwargs):
    global CELERY_ON
    if CELERY_ON:
        try:
            t = task.apply_async(args=args, kwargs=kwargs)
            log.info('running task %s:%s' % (t.task_id, task))
            return t

        except socket.error, e:
            if isinstance(e, IOError) and e.errno == 111:
                log.debug('Unable to connect to celeryd. Sync execution')
                CELERY_ON = False
            else:
                log.error(traceback.format_exc())
        except KeyError, e:
                log.debug('Unable to connect to celeryd. Sync execution')
        except Exception, e:
            log.error(traceback.format_exc())

    log.debug('executing task %s in sync mode' % task)
    return ResultWrapper(task(*args, **kwargs))


def __get_lockkey(func, *fargs, **fkwargs):
    params = list(fargs)
    params.extend(['%s-%s' % ar for ar in fkwargs.items()])

    func_name = str(func.__name__) if hasattr(func, '__name__') else str(func)

    lockkey = 'task_%s.lock' % \
        md5(func_name + '-' + '-'.join(map(safe_str, params))).hexdigest()
    return lockkey


def locked_task(func):
    def __wrapper(func, *fargs, **fkwargs):
        lockkey = __get_lockkey(func, *fargs, **fkwargs)
        lockkey_path = config['app_conf']['cache_dir']

        log.info('running task with lockkey %s' % lockkey)
        try:
            l = DaemonLock(file_=jn(lockkey_path, lockkey))
            ret = func(*fargs, **fkwargs)
            l.release()
            return ret
        except LockHeld:
            log.info('LockHeld')
            return 'Task with key %s already running' % lockkey

    return decorator(__wrapper, func)


def get_session():
    if CELERY_ON:
        engine = engine_from_config(config, 'sqlalchemy.db1.')
        init_model(engine)
    sa = meta.Session()
    return sa


def dbsession(func):
    def __wrapper(func, *fargs, **fkwargs):
        try:
            ret = func(*fargs, **fkwargs)
            return ret
        finally:
            if CELERY_ON and not CELERY_EAGER:
                meta.Session.remove()

    return decorator(__wrapper, func)
