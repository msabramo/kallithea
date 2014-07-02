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
kallithea.bin.kallithea_gist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gist CLI client for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 9, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import with_statement
import os
import sys
import stat
import argparse
import fileinput

from kallithea.bin.base import json, api_call, RcConf, FORMAT_JSON, FORMAT_PRETTY


def argparser(argv):
    usage = (
      "kallithea-gist [-h] [--format=FORMAT] [--apikey=APIKEY] [--apihost=APIHOST] "
      "[--config=CONFIG] [--save-config] [GIST OPTIONS] "
      "[filename or stdin use - for terminal stdin ]\n"
      "Create config file: kallithea-gist --apikey=<key> --apihost=http://your.kallithea.server --save-config"
    )

    parser = argparse.ArgumentParser(description='Kallithea Gist cli',
                                     usage=usage)

    ## config
    group = parser.add_argument_group('config')
    group.add_argument('--apikey', help='api access key')
    group.add_argument('--apihost', help='api host')
    group.add_argument('--config', help='config file path DEFAULT: ~/.config/kallithea')
    group.add_argument('--save-config', action='store_true',
                       help='save the given config into a file')

    group = parser.add_argument_group('GIST')
    group.add_argument('-p', '--private', action='store_true',
                       help='create private Gist')
    group.add_argument('-f', '--filename',
                       help='set uploaded gist filename, '
                            'also defines syntax highlighting')
    group.add_argument('-d', '--description', help='Gist description')
    group.add_argument('-l', '--lifetime', metavar='MINUTES',
                       help='gist lifetime in minutes, -1 (DEFAULT) is forever')
    group.add_argument('--format', dest='format', type=str,
                       help='output format DEFAULT: `%s` can '
                       'be also `%s`' % (FORMAT_PRETTY, FORMAT_JSON),
            default=FORMAT_PRETTY
    )
    args, other = parser.parse_known_args()
    return parser, args, other


def _run(argv):
    conf = None
    parser, args, other = argparser(argv)

    api_credentials_given = (args.apikey and args.apihost)
    if args.save_config:
        if not api_credentials_given:
            raise parser.error('--save-config requires --apikey and --apihost')
        conf = RcConf(config_location=args.config,
                      autocreate=True, config={'apikey': args.apikey,
                                               'apihost': args.apihost})
        sys.exit()

    if not conf:
        conf = RcConf(config_location=args.config, autoload=True)
        if not conf:
            if not api_credentials_given:
                parser.error('Could not find config file and missing '
                             '--apikey or --apihost in params')

    apikey = args.apikey or conf['apikey']
    host = args.apihost or conf['apihost']
    DEFAULT_FILENAME = 'gistfile1.txt'
    if other:
        # skip multifiles for now
        filename = other[0]
        if filename == '-':
            filename = DEFAULT_FILENAME
            gist_content = ''
            for line in fileinput.input('-'):
                gist_content += line
        else:
            with open(filename, 'rb') as f:
                gist_content = f.read()

    else:
        filename = DEFAULT_FILENAME
        gist_content = None
        # little bit hacky but cross platform check where the
        # stdin comes from we skip the terminal case it can be handled by '-'
        mode = os.fstat(0).st_mode
        if stat.S_ISFIFO(mode):
            # "stdin is piped"
            gist_content = sys.stdin.read()
        elif stat.S_ISREG(mode):
            # "stdin is redirected"
            gist_content = sys.stdin.read()
        else:
            # "stdin is terminal"
            pass

    # make sure we don't upload binary stuff
    if gist_content and '\0' in gist_content:
        raise Exception('Error: binary files upload is not possible')

    filename = os.path.basename(args.filename or filename)
    if gist_content:
        files = {
            filename: {
                'content': gist_content,
                'lexer': None
            }
        }

        margs = dict(
            lifetime=args.lifetime,
            description=args.description,
            gist_type='private' if args.private else 'public',
            files=files
        )

        json_data = api_call(apikey, host, 'create_gist', **margs)['result']
        if args.format == FORMAT_JSON:
            print json.dumps(json_data)
        elif args.format == FORMAT_PRETTY:
            print json_data
            print 'Created %s gist %s' % (json_data['gist']['type'],
                                          json_data['gist']['url'])
    return 0


def main(argv=None):
    """
    Main execution function for cli

    :param argv:
    """
    if argv is None:
        argv = sys.argv

    try:
        return _run(argv)
    except Exception, e:
        print e
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
