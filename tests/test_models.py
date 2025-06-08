import logging
import unittest

from sqlalchemy import select, text
import sqlalchemy.exc

from . import context as ctx

Session = ctx.mondojazz.Session
SpinitronPlaylist = ctx.mondojazz.models.SpinitronPlaylist

class SessionSetup:
    def setUp(self):
        self.sess = Session()

    def tearDown(self):
        self.sess.close()


class TestSession(SessionSetup, unittest.TestCase):
    def test_Session(self):
        s = self.sess.scalars(select(text('"Hello World"'))).one()
        self.assertEqual(s, 'Hello World')


class TestSpinitronPlaylist(SessionSetup, unittest.TestCase):
    def test_empty(self):
        pls = self.sess.scalars(select(SpinitronPlaylist)).all()
        self.assertEqual(pls, [])


if __name__ == '__main__':
    unittest.main()
