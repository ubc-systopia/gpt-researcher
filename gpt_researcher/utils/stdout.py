import sys
import os
from contextlib import contextmanager

class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

@contextmanager
def stdout_to_file(filepath):
    """
    Redirects stdout to both the original stdout and a file.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    f = open(filepath, 'w', encoding='utf-8')
    original_stdout = sys.stdout
    sys.stdout = Tee(sys.stdout, f)
    try:
        yield
    finally:
        sys.stdout = original_stdout
        f.close()
