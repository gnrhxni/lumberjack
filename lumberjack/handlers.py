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

import tornado.gen
import tornado.web
import tornado.ioloop
import tornado.websocket
import tornado.httpclient
from tornado.options import options

from .util import (
    slug, deslug,
)


class BaseHandler(tornado.web.RequestHandler):

    def sender_wants_json(self):
        return 'Accept' in self.request.headers and \
               self.request.headers['Accept'].find('json') > 0


    def render_template_or_json(self, template, *args, **kwargs):
        if self.sender_wants_json():
            return self.write(kwargs)
        else:
            return self.render(template, **kwargs)



class MainHandler(BaseHandler):

    def initialize(self, lodge=None):
        self.lodge = lodge


    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        if self.lodge.authoritative:
            self.render_template_or_json("main.html", lodge=self.lodge)
        else:
            client = tornado.httpclient.AsyncHTTPClient()
            response = yield client.fetch( 
                "http://"+self.host+":"+options.listenport+"/",
                headers=dict(Accept="application/json")
                )
            self.render_template_or_json( "main.html", 
                                          lodge=response.body )


class LodgeHandler(BaseHandler):
    
    def initialize(self, lodge=None):
        self.lodge = lodge


    def post(self):
        fellow = Fellow.deserialize(self.request.body)
        if fellow.alive():
            logging.debug('Fellow %s checked in', fellow.name)
            if fellow.name in self.lodge:
                self.lodge[fellow.name].last_checked_in = fellow.last_checked_in
            else:
                self.lodge[fellow.name] = fellow
        else: # not alive
            logging.warning('Fellow lumberjack %s tried to check '+
                            'in past curfew. Denied.', fellow.name)



class LumberHandler(BaseHandler):

    def initialize(self, cache=None):
        self.cache = cache

    @tornado.web.asynchronous
    def get(self, lumberfile):
        logging.debug(lumberfile)
        lumberfile = deslug(lumberfile)
        logging.debug(lumberfile)

        if lumberfile in self.cache:
            if self.sender_wants_json():
                # stream it out in json forever by keeping the request open
                # note: tornado writes json whenever you give a dict to 
                #   self.write()
                self.write( dict(logs=[chunk for chunk in self.cache[lumberfile]]) )
                self.flush()

                def _push(data):
                    self.write(dict(logs=data))
                    self.flush()
                
                self.cache[lumberfile].subscribe( id(self.request), _push )

                logging.debug( "Subscribed as streaming request: %s" % (lumberfile) )
            else:
                self.render( "lumber.html", 
                             filename=lumberfile, 
                             lumberfile=reduce( lambda x,y: x+'\n'+y, self.cache[lumberfile]) )
        else: # not in the cache
            self.send_error(status_code=404)
            self.flush()
            self.finish()



class LumberSocket(tornado.websocket.WebSocketHandler):

    def initialize(self, cache=None):
        self.cache = cache

    def open(self, lumberfile):
        self.lumberfile = deslug(lumberfile)
        self.cache[self.lumberfile].subscribe( id(self.stream), 
                                               lambda data: self.write_message(dict(logs=data)) )
        logging.debug( "Subscribed as websocket: %s" % (self.lumberfile) )

    def on_message(self):
        pass

    def on_close(self):
        # unsubscribe to the lumberbuffer
        self.cache[self.lumberfile].unsubscribe( id(self.stream) )
        logging.debug( "Unsubscribed from websocket: %s" % (self.lumberfile) )



class ProxyHandler(BaseHandler):

    @tornado.web.asynchronous
    def get(self, host, lumberfile):
        self.lumberfile, self.host = deslug(lumberfile), host

        if self.sender_wants_json():
            request = tornado.httpclient.HTTPRequest(
                "ws://"+host+':'+str(options.listenport)+'/'+lumberfile+'/socket', 
                connect_timeout=900
                )
            request = tornado.httpclient._RequestProxy(
                request, tornado.httpclient.HTTPRequest._DEFAULTS)

            self.conn = ProxyStreamer( tornado.ioloop.IOLoop.current(),
                                       request,
                                       output_stream=self ) 
            # once ProxyStreamer is instantiated, it'll keep writing things to the handler
            logging.debug( "Subscribed as streaming proxy host %s file: %s" 
                           % (self.host, self.lumberfile) )
        else:
            self.render( "proxy.html", 
                         host=self.host,
                         filename=lumberfile )


    def on_connection_close(self):
        self.conn.close()
        logging.debug( "Unsubscribed as streaming proxy host %s file: %s" 
                       % (self.host, self.lumberfile) )



class ProxySocket(tornado.websocket.WebSocketHandler):
    def open(self, host, lumberfile):
        self.host = host
        self.lumberfile = deslug(lumberfile)

        request = tornado.httpclient.HTTPRequest(
            "ws://"+host+':'+str(options.listenport)+'/'+self.lumberfile+'/socket', 
            connect_timeout=900
            )
        request = tornado.httpclient._RequestProxy(
            request, tornado.httpclient.HTTPRequest._DEFAULTS)

        self.conn = ProxyStreamer( tornado.ioloop.IOLoop.current(), 
                                   request, 
                                   output_stream=self, 
                                   as_websocket=True ) 

        logging.debug( "Subscribed as websocket proxy to host %s file %s" 
                       % (self.host, self.lumberfile) )


    def on_message(self):
        pass


    def on_close(self):
        self.conn.close()
        logging.debug( "Unsubscribed websocket proxy to host %s file %s" 
                       % (self.host, self.lumberfile) )

