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
import logging
import optparse
import importlib
from functools import wraps
from itertools import chain

log = logging.getLogger(__name__)

import tornado.ioloop
import tornado.httpclient

from .util import deserialize

opt_list = [
    optparse.make_option('-c', '--config', action="store", type="string",
                         dest="config_file", default="",
                         help=""),
    optparse.make_option('-l', '--logging', action="store", type="string",
                         dest="logging", default="INFO",
                         help="Logging verbosity, options are debug, info, "+
                         "warning, and critical")
    ]

alive_connections = dict()

def parsefxn_wrapper(f, url):
    @wraps(f, assigned=[], updated=('__dict__',))
    def wrapper(*args, **kwargs):
        data, con = args[0], alive_connections[url]
        con['raw_received'] += len(data)
        data = deserialize(data)
        con['des_received'] += len(data)
        try:
            return f(*args, **kwargs)
        except Exception as e:
            log.exception(e)
    return wrapper


def import_config_file(f, globs, locs):
    code = compile(f.read(), '<string>', 'exec')
    exec(code, globs, locs)


def print_report(conns):
    """Nicely print out alive_connections"""
    message = list()
    for key, val in conns.iteritems():
        message.append( 
            key + '\t' + '\t'.join([str(v) for v in val.values()]) 
        )
    header = '\t'.join( chain(['host'], conns.values()[0].keys()) )
    lines = '-'*len(max(message))
    print >> sys.stderr, lines
    print >> sys.stderr, header
    print >> sys.stderr, lines
    print >> sys.stderr, '\n'.join(message)
    print >> sys.stderr, lines


def add_stream(url, parsefxn):
    request = tornado.httpclient.HTTPRequest( 
        url,
        connect_timeout=30,
        request_timeout=0,
        streaming_callback=parsefxn_wrapper(parsefxn, url),
        headers=dict(Accept="application/json")
    )
    alive_connections[url] = dict( conn=tornado.httpclient.AsyncHTTPClient(),
                                   raw_received=int(),
                                   des_received=int() )
    alive_connections[url]['conn'].fetch(request)
    
    log.info( "Subscribed: "+ url)
        

def main():
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
        
    for sluice, cfg in opts.sluice_config.iteritems():
        log.info('Adding stream for %s', sluice)
        add_stream( sluice, cfg['parser'] )
        
    if opts.logging.upper() in ('INFO', 'DEBUG'):
        tornado.ioloop.PeriodicCallback(
            callback=lambda : print_report(alive_connections),
            callback_time=(10*1000), # 10 s in ms
            io_loop=ioloop
            ).start()

    log.info('Starting streaming now...')

    try:
        ioloop.start()
    except KeyboardInterrupt:
        print >> sys.stderr, "Shutting down..."
    finally:
        [ val['conn'].close() for val in alive_connections.values() ]

if __name__ == '__main__':
        main()
