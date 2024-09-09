import time

class Timer:
    def __enter__(self):
        self.start = time.time()
        self.is_running = True
        return self

    def record(self):
        self.end = time.time()
        self.interval = self.end - self.start
        return self.interval

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start
        self.is_running = False
    
    def __str__(self):
        if self.is_running:
            return f"Timer(start={self.start}, interval={time.time() * 1000 - self.start})"
        return f"Timer(start={self.start}, end={self.end}, interval={self.interval})"
    
    def __repr__(self):
        return str(self)
