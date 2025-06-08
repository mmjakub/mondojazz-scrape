from datetime import datetime
import json
import os
import unittest

from . import context as ctx
ShowPage = ctx.mondojazz.parser.ShowPage
PlaylistPage = ctx.mondojazz.parser.PlaylistPage

class LoadFile:
    @classmethod
    def setUp(cls):
        for fname, attr, func in cls._data:
            with open(os.path.join(ctx.DATA_DIR, fname)) as fp:
                setattr(cls, attr, func(fp))

class TestShowPage(LoadFile, unittest.TestCase):
    _data = [('show.html', 'parser', ShowPage)]

    def test_page_num(self):
        self.assertEqual(self.parser.getNextPageNum(), 2)

    def test_playlist_ids(self):
        playlists = self.parser.getItems()
        self.assertEqual([pl['spinitron_id'] for pl in playlists], [
            19251102,
            19249654,
            19222256,
            19220195,
            19191746,
            19189528,
            19160705,
            19158303,
            19127196,
            19127036,
            19067134,
            19064879,
            19036166,
            19033914,
            19005314,
            19003066,
            18974239,
            18973930,
            18954909,
            18954736,
        ])

class TestLastShowPage(LoadFile, unittest.TestCase):
    _data = [('show_last.html', 'parser', ShowPage)]

    def test_has_no_next_page(self):
        self.assertIsNone(self.parser.getNextPageNum())

    def test_items(self):
        items = self.parser.getItems()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['spinitron_id'], 4100337)


class TestPlaylistPage(LoadFile, unittest.TestCase):
    _data = [
        ('pl1.html', 'parser', PlaylistPage),
        ('pl1.json', 'correct', json.load),
    ]


    def test_playlist(self):
        items = self.parser.getItems()
        self.assertEqual(len(items), 20)
        for item in items:
            del item['start_time']
        self.assertEqual(items, self.correct)
    

if __name__ == '__main__':
    unittest.main()
