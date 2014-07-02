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
kallithea.lib.paster_commands.ishell
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

interactive shell paster command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 4, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import with_statement

import os
import sys
import logging

from kallithea.lib.utils import BasePasterCommand

# Add location of top level folder to sys.path
from os.path import dirname as dn
rc_path = dn(dn(dn(os.path.realpath(__file__))))
sys.path.append(rc_path)

log = logging.getLogger(__name__)


class Command(BasePasterCommand):

    max_args = 1
    min_args = 1

    usage = "CONFIG_FILE"
    group_name = "Kallithea"
    takes_config_file = -1
    parser = BasePasterCommand.standard_parser(verbose=True)
    summary = "Interactive shell"

    def command(self):
        #get SqlAlchemy session
        self._init_session()

        # imports, used in ipython shell
        import os
        import sys
        import time
        import shutil
        import datetime
        from kallithea.model.db import *

        try:
            from IPython import embed
            from IPython.config.loader import Config
            cfg = Config()
            cfg.InteractiveShellEmbed.confirm_exit = False
            embed(config=cfg, banner1="Kallithea IShell.")
        except ImportError:
            print 'ipython installation required for ishell'
            sys.exit(-1)

    def update_parser(self):
        pass
