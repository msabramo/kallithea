import os
import sys
import socket
import traceback
import logging

from rhodecode.lib.pidlock import DaemonLock, LockHeld
from vcs.utils.lazy import LazyProperty
from decorator import decorator
from hashlib import md5
from pylons import  config

log = logging.getLogger(__name__)

def str2bool(v):
    return v.lower() in ["yes", "true", "t", "1"] if v else None

CELERY_ON = str2bool(config['app_conf'].get('use_celery'))

class ResultWrapper(object):
    def __init__(self, task):
        self.task = task

    @LazyProperty
    def result(self):
        return self.task

def run_task(task, *args, **kwargs):
    if CELERY_ON:
        try:
            t = task.delay(*args, **kwargs)
            log.info('running task %s:%s', t.task_id, task)
            return t
        except socket.error, e:
            if  e.errno == 111:
                log.debug('Unable to connect to celeryd. Sync execution')
            else:
                log.error(traceback.format_exc())
        except KeyError, e:
                log.debug('Unable to connect to celeryd. Sync execution')
        except Exception, e:
            log.error(traceback.format_exc())

    log.debug('executing task %s in sync mode', task)
    return ResultWrapper(task(*args, **kwargs))


def locked_task(func):
    def __wrapper(func, *fargs, **fkwargs):
        params = list(fargs)
        params.extend(['%s-%s' % ar for ar in fkwargs.items()])

        lockkey = 'task_%s' % \
            md5(str(func.__name__) + '-' + \
                '-'.join(map(str, params))).hexdigest()
        log.info('running task with lockkey %s', lockkey)
        try:
            l = DaemonLock(lockkey)
            ret = func(*fargs, **fkwargs)
            l.release()
            return ret
        except LockHeld:
            log.info('LockHeld')
            return 'Task with key %s already running' % lockkey

    return decorator(__wrapper, func)








