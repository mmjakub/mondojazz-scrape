import logging

import requests
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from mondojazz import Session
from mondojazz.models import SpinitronPlaylist, Spin
from mondojazz.parser import ShowPage, PlaylistPage

logger = logging.getLogger(__name__)

SHOW_URL = 'https://spinitron.com/RFB/show/103797/Mondo-Jazz'
PLAYLIST_FMT = 'https://spinitron.com/RFB/pl/{}/Mondo-Jazz'

def parseShowPage(page=None):
    params = {}
    if page is not None:
        params['page'] = page
    r = requests.get(SHOW_URL, params=params)
    sp = ShowPage(r.text)
    page = sp.getNextPageNum()
    return sp.getItems(), page


def parsePlaylistPage(pl_id):
    r = requests.get(PLAYLIST_FMT.format(pl_id))
    plp = PlaylistPage(r.text)
    return plp.getItems()


def scrapeShowPages(page=1, last_page=0):
    if not last_page:
        logger.info(f'Scraping all pages starting from page={page}')
    else:
        logger.info(f'Scraping pages [{page}...{last_page}]')
    with Session() as session, session.begin():
        while page and (not last_page or page <= last_page):
            page = scrapeSingleShowPage(page, session)


def scrapeSingleShowPage(page, session, skip=True):
    logger.info(f'Parsing page={page}')
    items, page = parseShowPage(page)
    logger.debug(f'Got {len(items)} items, next page={page}')
    for pl in items:
        logger.debug(f'Parsed item:\n\t{pl}')
        try: 
            with session.begin_nested() as sp:
                o = SpinitronPlaylist(**pl)
                session.add(o)
            logger.debug(f'Added object:\n\t{o}')
        except DBAPIError as e:
            logger.error(f'Item:\n\t{pl}\n\tCaused Exception:\n\t{e}')
            if not skip:
                raise e
    return page


def scrapePlaylistSpins(stpl, session):
    logger.info(f'Parsing spins from {stpl.spinitron_id}')
    spins = parsePlaylistPage(stpl.spinitron_id)
    if len(spins) == len(stpl.spins):
        logger.warning(f'Already got {len(spins)} spins, skipping {stpl}')
        return
    for i, spin in enumerate(spins):
        o = Spin(number=i, **spin)
        try: 
            with session.begin_nested() as sp:
                stpl.spins.append(o)
        except DBAPIError as e:
            logger.error(f'Spin:\n\t{spin}\n\tCaused Exception:\n\t{e}')


def scrapeAllSpins():
    with Session() as session, session.begin():
        stpls = session.scalars(select(SpinitronPlaylist)).all()
        for stpl in stpls:
            scrapePlaylistSpins(stpl, session)

def genPlaylists(page=1):
    while page:
        items, page = parseShowPage(page)
        yield from items


def scrapeLatest():
    with Session() as session, session.begin():
        latest = session.scalars(
                select(SpinitronPlaylist)
                .order_by(SpinitronPlaylist.timeslot.desc())
            ).first()
        count = 0
        for pl in genPlaylists():
            if pl['timeslot'] <= latest.timeslot or pl['spinitron_id'] == latest.spinitron_id:
                logger.info(f'Reached {latest} from {latest.timeslot.isoformat()}, aborting')
                break
            stpl = SpinitronPlaylist(**pl)
            logger.info(f'Got new {stpl} from {stpl.timeslot.isoformat()}')
            session.add(stpl)
            scrapePlaylistSpins(stpl, session)
            count += 1
    return count

