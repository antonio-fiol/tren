from functools import wraps
from time import time,sleep
import tornado.ioloop


class timed_avg(object):
  def __init__(self, n=1):
    self.elapsed = 0.0
    self.count = 0
    self.n = n

  def __call__(self, f):
      def wrapped(*args, **kwds):
          start = tornado.ioloop.IOLoop.current().time()
          result = f(*args, **kwds)
          self.elapsed += tornado.ioloop.IOLoop.current().time() - start
          self.count += 1
          if self.count >= self.n:
              print( "%s took %f s on average for %d calls" % (f.__name__, self.elapsed / self.count, self.count) )
              self.elapsed = 0.0
              self.count = 0
          return result
      return wrapped

class timed_avg_and_freq(object):
  def __init__(self, n=1):
    self.elapsed = 0.0
    self.freq_start = None
    self.count = 0
    self.n = n

  def __call__(self, f):
      def wrapped(*args, **kwds):
          start = tornado.ioloop.IOLoop.current().time()
          if not self.freq_start:
              self.freq_start = start
          result = f(*args, **kwds)
          now = tornado.ioloop.IOLoop.current().time()
          self.elapsed += now - start
          self.count += 1
          if self.count >= self.n:
              freq_elapsed = now - self.freq_start
              print( "%s took %f s on average for %d calls (called every %f s) %.2f%% active" % (f.__name__, self.elapsed / self.count, self.count, freq_elapsed / self.count, 100.0*self.elapsed/freq_elapsed) )
              self.elapsed = 0.0
              self.count = 0
              self.freq_start = start
          return result
      return wrapped

#@timed_avg(2)
#def fun(i):
#   sleep(i)

