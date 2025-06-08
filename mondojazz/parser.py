from datetime import datetime
import logging

from bs4 import BeautifulSoup, SoupStrainer

logger = logging.getLogger(__name__)

def parseSpinTime(s):
    return datetime.strptime(s, '%I:%M %p').time()


def parseTimeslot(s):
    return datetime.strptime(s[:s.index('\xa0')], '%b %d, %Y %I:%M %p')


class Page:
    container = el = 'div'

    def __init__(self, markup):
        self.soup = BeautifulSoup(
            markup,
            'html.parser',
            parse_only=SoupStrainer(self.container, id=self.container_id))

    def getItems(self):
        return list(map(
            self.parseEl,
            self.soup.find_all(self.el, class_=self.el_class)))


class ShowPage(Page):
    container_id = 'playlist-list-0'
    el_class = 'list-item'

    def getNextPageNum(self):
        pager = self.soup.find('div', class_='infpager infpager_next')
        if pager['data-has-more'] == '1':
            return int(pager['data-current-page']) + 2

    def parseEl(self, tag):
        d = {}
        d['spinitron_id'] = int(tag['data-key'])
        d['timeslot'] = parseTimeslot(tag.find('p', class_='timeslot').text)
        try:
            d['title'] = tag.find('h4', class_='episode-name').text
        except AttributeError:
            d['title'] = ''
            logger.warning(f'episode {d["spinitron_id"]} has no title')
        try:
            d['desc'] = tag.find('div', class_='episode-description').text
        except AttributeError:
            d['desc'] = ''
            logger.warning(f'playlist {d["spinitron_id"]} has no description')
        return d


class PlaylistPage(Page):
    container_id = 'public-spins-0'
    el = 'tr'
    el_class = 'spin-item'

    def parseEl(self, tag):
        d = {}
        d['spinitron_id'] = int(tag['data-key'])
        d['artist'] = tag.find('span', class_='artist').text
        d['title'] = tag.find('span', class_='song').text
        try:
            d['album'] = tag.find('span', class_='release').text
        except AttributeError:
            d['album'] = ''
            logger.warning(f'spin {d["title"]} has no album')
        try:
            d['year'] = int(tag.find('span', class_='released').text)
        except AttributeError:
            d['year'] = 0
            logger.warning(f'spin {d["title"]} has no year')
        d['start_time'] = parseSpinTime(tag.find('td', class_='spin-time').a.text)
        return d

