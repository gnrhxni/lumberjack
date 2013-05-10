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

import logging
from functools import wraps
from datetime import timedelta

log = logging.getLogger(__name__)

from tornado.ioloop import IOLoop
import tornado.httpclient

from ..util import deserialize
from ..models import AttrBag


class Sluice(object):
    
    def __init__(self, url, parsefxn, 
                 reopen_delay=1,   io_loop=None):
        self.url             = url
        self.parsefxn        = parsefxn
        self.reopen_delay    = reopen_delay
        self.io_loop          = IOLoop.instance() if io_loop is None else io_loop

        self.parsefxn   = self.wrap_parsefxn(parsefxn)
        self.client     = None
        self.connection = None
        self.stats      = AttrBag( raw_received  = 0,
                                   log_received  = 0,
                                   recv_fail     = 0,
                                   parsefxn_fail = 0 )


    def wrap_parsefxn(self, f):
    
        @wraps(f, assigned=[], updated=('__dict__',))
        def wrapper(*args, **kwargs):

            data = args[0]

            self.stats.raw_received += len(data)
            data = deserialize(data)
            self.stats.log_received += len(data)
            
            if not data:
                self.reopen()
                return None

            try:
                return f(data)
            except Exception as e:
                self.stats.parsefxn_fail += 1
                log.exception(e)
        
        return wrapper
    

    def open(self):
        
        request = tornado.httpclient.HTTPRequest( 
            self.url,
            headers            = dict(Accept="application/json"),
            connect_timeout    = 10,
            request_timeout    = 0,
            streaming_callback = self.parsefxn
        )
        
        self.client = tornado.httpclient.AsyncHTTPClient(io_loop = self.io_loop)
        self.connection = self.client.fetch(
            request, 
            callback=lambda r: self.reopen()
        )
        log.info( "Subscribed: "+ self.url)
        
        return self
    
    def reopen(self):
        
        if not self.connection.done():
            log.error('Tried to reconnect while connection still open')
            return None
        else:
            self.stats.recv_fail += 1
            log.warning('Reconnecting in %d seconds', self.reopen_delay)
            self.io_loop.add_timeout(
                deadline = timedelta(seconds=self.reopen_delay),
                callback = self.open
            )
            self.reopen_delay *= 2
            return True


    def close(self):
        log.info('Shutting down sluice for url %s', self.url)
        del self.connection
        del self.client
        

            
