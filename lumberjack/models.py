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

import socket
import logging
import datetime
from collections import deque
from functools import partial

log = logging.getLogger(__name__)

import tornado.ioloop
import tornado.websocket
import tornado.httpclient
from tornado.options import options

from .util import (
    serialize, deserialize,
    now
)

DEFAULT_CURFEW = datetime.timedelta(minutes=20)
DEFAULT_FELLOW_NAME = socket.gethostname()


class Lodge(object):
    """ Where all the lumberjacks check in. Shows living lumberjacks"""

    def __init__(self, fellow, host=None):
        if host is None:
            # start your own lodge
            self.fellows = dict( )
            self.fellows[fellow.name] = fellow
            self.authoritative = True
            check_in_func = partial(self.check_in_locally, fellow)
        else:
            # connect to a current lodge
            self.host = host
            self.fellows = dict( )
            self.fellows[fellow.name] = fellow
            self.httpclient = tornado.httpclient.AsyncHTTPClient()
            self.authoritative = False
            check_in_func = partial(self.check_in_remotely, fellow)

        check_in_func()
        check_in_frequency = (fellow.curfew.seconds - 10) * 1000 # in ms
        tornado.ioloop.PeriodicCallback( check_in_func, check_in_frequency ).start()
            

    def check_in_locally(self, fellow):
        self.fellows[fellow.name].last_checked_in = now()
        log.debug('Locally posted check-in for %s', fellow.name)

    
    def check_in_remotely(self, fellow):
        def _check_in_cb(resp):
            if resp.code == 200:
                log.debug('Posted check-in: %d', resp.code)
            else:
                msg = ('Failed to post check-in.\n'+
                       '%d: %s'%(resp.code, resp.body))
                log.error(msg)

        fellow.last_checked_in = now()

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Posting check-in: %s", serialize(fellow))

        request = tornado.httpclient.HTTPRequest(
            url="http://"+self.host+":"+str(options.listenport)+"/lodge",
            method="POST",
            body=serialize(fellow)
            )

        self.httpclient.fetch( request, callback=_check_in_cb )


    def alive_lumberjacks(self):
        return [ fellow for fellow in self.fellows.values() if fellow.alive() ]


    def _serialize(self):
        return dict( 
            host=self.host,
            fellows=self.fellows
            )
    


class Fellow(object):

    def __init__(self, name=None, curfew=None, 
                 lumberfiles=list(), last_checked_in=None):
        self.name            = DEFAULT_FELLOW_NAME if name is None else name
        self.curfew          = DEFAULT_CURFEW if curfew is None else curfew
        self.lumberfiles     = lumberfiles
        self.last_checked_in = now() if last_checked_in is None else last_checked_in


    def _serialize(self):
        return dict( 
            name=self.name,
            curfew=self.curfew.seconds,
            last_checked_in=self.last_checked_in.strftime('%s'),
            lumberfiles=self.lumberfiles
            )


    @staticmethod
    def deserialize(fellow):
        data = deserialize(fellow)
        data['last_checked_in'] = datetime.datetime.fromtimestamp(
            float(data['last_checked_in']) )
        data['curfew'] = datetime.timedelta(seconds=data['curfew'])
        data['lumberfiles'] = [ AttrBag(**l) for l in data['lumberfiles'] ]
        return Fellow(**data)

            
    def alive(self):
        return (now() - self.last_checked_in) < self.curfew

    

class LumberBuffer(deque):
    """
    LumberBuffer keeps a running, fixed-length, buffer of everything appended to it.
    Whenever something calls append(), LumberBuffer calls whatever callbacks added
    by previous calls to subscribe().

    Use should be something like:
    buf = LumberBuffer(maxlen=100)
    def my_callback(item):
        print "I just appended something"

    buf.subscribe(my_callback)

    for i in range(5):
        buf.append(i)
    """

    def __init__(self, maxlen=200):
        self.callbacks = dict()
        super(LumberBuffer, self).__init__(maxlen=maxlen)


    def __str__(self):
        return str( len(self) )

        
    def append(self, item):
        super(LumberBuffer, self).append(item)
        for callback in self.callbacks.values():
            callback(item)

        
    def append_list(self, l):
        super(LumberBuffer, self).extend(item for item in l)
        for callback in self.callbacks.values():
            callback(l)


    def subscribe(self, identifier, callback):
        self.callbacks[identifier] = callback


    def unsubscribe(self, identifier):
        del(self.callbacks[identifier])



class ProxyStreamer(tornado.websocket.WebSocketClientConnection):

    def __init__(self, *args, **kwargs):
        self.output_stream = kwargs.pop('output_stream')
        self.as_websocket = kwargs.pop('as_websocket', False)
        super(ProxyStreamer, self).__init__(*args, **kwargs)


    def on_message(self, message):
        if self.as_websocket:
            self.output_stream.write_message(message)
        else:
            self.output_stream.write(message)
            self.output_stream.flush()
            

    def _on_close(self):
        pass
    

    def close(self):
        if hasattr(self, "stream"):
            self.stream.close()



class AttrBag(object):

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)


    def __repr__(self):
        return str(self.__dict__)


    def _serialize(self):
        return self.__dict__

    @staticmethod
    def deserialize(s):

        return AttrBag(**deserialize(s))
