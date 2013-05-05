# Lumberjack
## Real time file streaming over HTTP

A tornado app for watching what happens to files through your browser.
Lumberjack also provides websocket and HTTP streaming JSON interfaces to attached files.

For usage tips, try --help

Here's something to get you started:
    
    lumberjack --logging=debug --log-to-stderr --listenport=9098 log0.log log1.log log2.log log3.log

Then go to localhost:9098 in your web browser.


## Lodges - clusters of lumberjacks

On host 1:
    
    lumberjack --listenport=9098 \
    	       /var/log/mysqld.log \
	       /opt/backend_app/log/debug.log

On host 2:
   
    lumberjack --listenport=9098 --lodge=host1.example.tld \
    	       /var/log/httpd/error_log \
	       /var/log/php.log \
	       /var/www/frontend_app/log/debug.log

Now visit host1.example.tld or host2.example.tld on port 9098 to monitor
logs under any lumberjack.


## JSON interface
Just include the header "Accept: application/json" 
(or Accept:-ing something json) in your requests.
For example:
    wget -O- -q --header 'Accept: application/json' \
         host1.example.tld:9098/log1.log

Or if you're a websockets type of person, 
try pointing a client at ws://host1.example.tld:9098/log1.log/socket
