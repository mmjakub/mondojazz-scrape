import logging
import os
import sys

logging.basicConfig(level=logging.DEBUG)

TESTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.abspath(os.path.join(TESTS_DIR, 'data'))

sys.path.insert(0, TESTS_DIR)

os.environ['ENGINE_URL'] = f'sqlite:///{DATA_DIR}/test.db'

import mondojazz
import mondojazz.parser
import mondojazz.models
