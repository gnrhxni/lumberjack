#!/usr/bin/env python
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

# TODO: split this into multiple modules, make an egg out of it.
from __future__ import absolute_import

import os
import socket
import logging
from functools import partial

import tornado.web
import tornado.ioloop
import tornado.process
import tornado.options 
from tornado.options import define, options

from .handlers import (
    MainHandler,
    LodgeHandler,
    LumberHandler, LumberSocket,
    ProxyHandler, ProxySocket
)
from .models import (
        LumberBuffer, 
        AttrBag, 
        Lodge,
        Fellow
)
from .util import slug

define( 'listenport', default=8080, 
        help="HTTP will be served on this port", 
        type=int )
define( 'bufferlen',  default=200,  
        help="Lines of logs to keep in memory", 
        type=int )
define( 'lodge',      default=None,   
        help="Lodge host. Connect to this host to show other running "+
        "lumberjacks. Defaults to set up a lodge that other "+
        "lumberjacks can connect to.",
        type=str )
define( 'name',      default=socket.gethostname(), 
        help="If using a lodge, use this name to identify myself. "+
        "Defaults to the system hostname",
        type=str )


def setup_global_models(logs_to_stream):
    lumberbuffers = dict()
    lodge = None # populated later in this function
    me = Fellow(name=options.name)

    def _logstream_cb(data=False, lumberbuffer=None):
        if data and filename:
            lines = data.rstrip('\r\n').split('\n')
            lumberbuffer.append_list(lines)
        else:
            logging.debug('Closing %s' % filename)
            
    for filename in logs_to_stream:
        lumberbuffers[filename] = LumberBuffer(maxlen=options.bufferlen)
        me.lumberfiles.append( 
            AttrBag( path=filename, slug=slug(filename) )
            )
        p = tornado.process.Subprocess(['tail', '-f', filename, '-n'+str(options.bufferlen)], 
                                       stdout=tornado.process.Subprocess.STREAM)
        p.stdout.read_until_close(
            callback=lambda *args, **kwargs: None, # called on stream close; should probably
            # Do something intelligent here (close something?)
            streaming_callback=partial(_logstream_cb, 
                                       lumberbuffer=lumberbuffers[filename])
            )
    
    lodge = Lodge(me, host=options.lodge)

    return (lumberbuffers, lodge)


def main():
    logs_to_stream = tornado.options.parse_command_line()
    logging.getLogger().setLevel(getattr(logging, options.logging.upper()))

    if logs_to_stream:
        # parse_command_line gives options if they're at the end
        # of the line. For example lumberjack log1 log2 --logging=debug
        # gives ['log1', 'log2', '--logging=debug'].
        lumberbuffers, lodge = setup_global_models(
            [log for log in logs_to_stream if not log.startswith('--')]
            )
            
    routes = (
        ( r'/', MainHandler, 
          dict(lodge=lodge) ),
        ( r'/lodge/?', LodgeHandler, 
          dict(lodge=lodge) ),
        ( r'/([\w.\.%]+)/?', LumberHandler, 
          dict(cache=lumberbuffers) ),
        ( r'/([\w.\.%]+)/socket.*', LumberSocket, 
          dict(cache=lumberbuffers) ),
        ( r'/([\w.\.]+)/([\w.\.%]+)/?', ProxyHandler ),
        ( r'/([\w.\.]+)/([\w.\.%]+)/socket.*', ProxySocket )
        )

    app_settings = dict(
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
        template_path=os.path.join(os.path.dirname(__file__), 'templates'),
        debug=(options.logging.lower() == 'debug')
        )

    app = tornado.web.Application( routes, **app_settings )
    
    app.listen(options.listenport)

    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.start()


if __name__ == "__main__":
    main()
