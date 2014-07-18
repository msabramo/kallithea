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
kallithea.lib.rcmail.smtp_mailer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Simple smtp mailer used in Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Sep 13, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import time
import logging
import smtplib
from socket import sslerror
from email.utils import formatdate
from kallithea.lib.rcmail.message import Message
from kallithea.lib.rcmail.utils import DNS_NAME


class SmtpMailer(object):
    """SMTP mailer class

    mailer = SmtpMailer(mail_from, user, passwd, mail_server, smtp_auth
                        mail_port, ssl, tls)
    mailer.send(recipients, subject, body, attachment_files)

    :param recipients might be a list of string or single string
    :param attachment_files is a dict of {filename:location}
        it tries to guess the mimetype and attach the file

    """

    def __init__(self, mail_from, user, passwd, mail_server, smtp_auth=None,
                 mail_port=None, ssl=False, tls=False, debug=False):

        self.mail_from = mail_from
        self.mail_server = mail_server
        self.mail_port = mail_port
        self.user = user
        self.passwd = passwd
        self.ssl = ssl
        self.tls = tls
        self.debug = debug
        self.auth = smtp_auth

    def send(self, recipients=[], subject='', body='', html='',
             attachment_files=None, headers=None):

        if isinstance(recipients, basestring):
            recipients = [recipients]
        if headers is None:
            headers = {}
        headers.setdefault('Date', formatdate(time.time()))
        msg = Message(subject, recipients, body, html, self.mail_from,
                      recipients_separator=", ", extra_headers=headers)
        raw_msg = msg.to_message()

        if self.ssl:
            smtp_serv = smtplib.SMTP_SSL(self.mail_server, self.mail_port,
                                         local_hostname=DNS_NAME.get_fqdn())
        else:
            smtp_serv = smtplib.SMTP(self.mail_server, self.mail_port,
                                     local_hostname=DNS_NAME.get_fqdn())

        if self.tls:
            smtp_serv.ehlo()
            smtp_serv.starttls()

        if self.debug:
            smtp_serv.set_debuglevel(1)

        smtp_serv.ehlo()
        if self.auth:
            smtp_serv.esmtp_features["auth"] = self.auth

        # if server requires authorization you must provide login and password
        # but only if we have them
        if self.user and self.passwd:
            smtp_serv.login(self.user, self.passwd)

        smtp_serv.sendmail(msg.sender, msg.send_to, raw_msg.as_string())
        logging.info('MAIL SENT TO: %s' % recipients)

        try:
            smtp_serv.quit()
        except sslerror:
            # sslerror is raised in tls connections on closing sometimes
            smtp_serv.close()
