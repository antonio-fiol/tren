from tornado import httpclient, ioloop
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import socket
from typing import cast
import logging
from registro import RegistroIP


    

class ZCEnabled(object):
    logging.basicConfig(level=logging.DEBUG)
    #logging.getLogger('zeroconf').setLevel(logging.DEBUG)
    zeroconf = Zeroconf()
    browsing = None

    @classmethod
    def retrieve(cls, url):
        """Download the page at `url`."""
        def http_done(response):
            print("url %s done, error=%s" % (url, response.error))
        print('fetching %s' % url)
        httpclient.AsyncHTTPClient().fetch(url, http_done)

    @classmethod
    def cb(cls, future):
        print("************************************************")
        print("*************************************************")
        print("**************************************************")
        print("**************************************************")
        print("{}.cb({})".format(cls.__name__, future))
        print(future.result())
        cls.retrieve("http://{}/reboot".format(future.result()))

    @classmethod
    def ossc(cls):
        def on_service_state_change(zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange) -> None:
           print("%s: Service %s of type %s state changed: %s" % (cls.__name__, name, service_type, state_change))

           if state_change is ServiceStateChange.Added:
              info = zeroconf.get_service_info(service_type, name)
              if info:
                  ip_port = "%s:%d" % (socket.inet_ntoa(cast(bytes, info.address)), cast(int, info.port))
                  print("  IP:Port: %s" % ip_port)
                  print("  Weight: %d, priority: %d" % (info.weight, info.priority))
                  print("  Server: %s" % (info.server,))
                  if info.properties:
                      print("  Properties are:")
                      for key, value in info.properties.items():
                          print("    %s: %s" % (key, value))
                  else:
                      print("  No properties")
                  fut = RegistroIP.instance(cls.__name__).ip(ip_port)
                  ioloop.IOLoop.current().add_future(fut, cls.cb)
              else:
                  print("  No info")
              print('\n')
        return on_service_state_change

    def start_browse(self, service="_http._tcp"):
        print("start_browse")
        RegistroIP.instance(self.__class__.__name__).registrar(self)
        if not self.__class__.browsing:
            print("Arrancando Browse")
            self.__class__.browsing = ServiceBrowser(self.__class__.zeroconf, service+".local.", handlers=[self.__class__.ossc()])

    @classmethod
    def end_browse(cls):
        if cls.browsing:
            print("Cancelling browser\n")
            cls.browsing.cancel()
            print("Cancelled\n")
            cls.browsing = None


