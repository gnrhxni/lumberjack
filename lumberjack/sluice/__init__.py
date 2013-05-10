# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from __future__ import absolute_import

import sys
import time
import logging
import optparse
import importlib
from itertools import chain

log = logging.getLogger(__name__)

import tornado.ioloop

from .models import Sluice
from ..util import import_config_file


opt_list = [
    optparse.make_option('-c', '--config', action="store", type="string",
                         dest="config_file", default="",
                         help=""),
    optparse.make_option('-l', '--logging', action="store", type="string",
                         dest="logging", default="INFO",
                         help="Logging verbosity, options are debug, info, "+
                         "warning, and critical"),
    optparse.make_option('-i', '--report-interval', action="store", type="int",
                         dest="report_interval", default=10,
                         help="If logging is at info or debug, print reports "+
                         "at this interval in seconds. Default: 10")
    ]

open_sluices = dict()


def print_report(conns):
    """Nicely print out open_sluices"""

    message = list()
    for url, sluice in conns.iteritems():
        message.append( 
            url + '\t' + '\t'.join([str(v) for v in 
                                    sluice.stats.__dict__.values()]) 
        )
    header = '\t'.join( chain(['host'], conns.values()[0].stats.__dict__.keys()) )
    lines = '-'*len(max(message))
    print >> sys.stderr, lines
    print >> sys.stderr, header
    print >> sys.stderr, lines
    print >> sys.stderr, '\n'.join(message)
    print >> sys.stderr, lines
        

def main():
    """Command line interface for sluices"""

    global open_sluices

    parser = optparse.OptionParser(option_list=opt_list)
    (opts, args) = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, opts.logging.upper()))
    logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s: %(message)s")
    
    try:
        import_config_file(open(opts.config_file), opts.__dict__, opts.__dict__)
    except IOError:
        print >> sys.stderr, "Couldn't find a config file to parse"
        parser.print_help()
        sys.exit(1)

    ioloop = tornado.ioloop.IOLoop.instance()

    for url, cfg in opts.sluice_config.iteritems():
        log.info('Adding sluice for %s', url)
        open_sluices[url] = Sluice( 
            url, 
            cfg['parser'],
            io_loop=ioloop
        ).open()
        
    if opts.logging.upper() in ('INFO', 'DEBUG'):
        # periodically print reports
        tornado.ioloop.PeriodicCallback(
            callback=lambda : print_report(open_sluices),
            callback_time=(opts.report_interval*1000), # in ms
            io_loop=ioloop
        ).start()

    log.info('Starting streaming now...')

    try:
        ioloop.start()
    except KeyboardInterrupt:
        print >> sys.stderr, "Shutting down..."
    finally:
        [ val.close() for val in open_sluices.values() ]


if __name__ == '__main__':
    main()
