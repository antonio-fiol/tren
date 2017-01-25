import functools
import inspect
class entryexit(object):
    '''Logging decorator that allows you to log with a
specific logger.
'''
    # Customize these messages
    ENTRY_MESSAGE = 'Entering {}({} {})'
    EXIT_MESSAGE = 'Exiting {}: {}'
    STACK_MESSAGE = """  File "{}", line {}, in {}
          {}"""

    def __init__(self, logger=None):
        #self.logger = logger
        pass

    def __call__(self, func):
        '''Returns a wrapper that wraps func.
The wrapper will log the entry and exit points of the function.
'''
        # set logger if it was not set earlier
        #if not self.logger:
        #    logging.basicConfig()
        #    self.logger = logging.getLogger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwds):
            print(self.ENTRY_MESSAGE.format(func.__name__, str(args), str(kwds)))
            stack = inspect.stack()
            for frame in stack:
                print(self.STACK_MESSAGE.format(frame[1],frame[2],frame[3],frame[4]))
            f_result = func(*args, **kwds)
            print(self.EXIT_MESSAGE.format(func.__name__, str(f_result)))
            return f_result
        return wrapper
