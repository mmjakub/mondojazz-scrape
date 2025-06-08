from collections import defaultdict
import logging
from urllib.error import HTTPError

from sqlalchemy import func, select

from mondojazz import Session, spotify
from mondojazz.models import Spin, SpinitronPlaylist
from mondojazz.models import Song, Episode
from mondojazz.models import SpotifyPlaylist, PlaylistItem

logger = logging.getLogger(__name__)


def initEpisodes(ep_no):
    with Session() as session, session.begin():
        results = session.execute(
                select(SpinitronPlaylist, func.group_concat(Spin.song_id))
                .join(SpinitronPlaylist.spins)
                .group_by(SpinitronPlaylist)
                .order_by(SpinitronPlaylist.timeslot.desc())
            ).all()
        episodes = defaultdict(list)
        for stpl, key in results:
            episodes[key].append(stpl)

        for stpls in episodes.values():
            ep = Episode(number=ep_no)
            ep_no -= 1
            for stpl in stpls:
                stpl.episode = ep


def mapEpToSpotify(ep, session):
    pl = session.scalars(select(SpotifyPlaylist).where(SpotifyPlaylist.episode == ep)).first()
    if pl:
        logger.warning(f'Episode {ep.number} already has a playlist: {pl.spotify_id}')
        return
    name = ep.getName()
    aired = ', '.join(ep.getAirDates())
    desc = f'{aired} on Radio Free Brooklyn with Ludovico Granvassu'
    spotify_id = spotify.create_playlist(name, desc)
    pl = SpotifyPlaylist(
            spotify_id=spotify_id,
            name=name,
            desc=desc,
        )
    ep.playlist = pl
    for i, spin in enumerate(ep.spinitron_playlists[0].spins[1:]):
        item = PlaylistItem(index=i)
        item.song = spin.song
        item.playlist = pl
        session.add(item)
    spotify.add_items_to_playlist(pl.spotify_id, [item.song.spotify_id for item in pl.items])
        

def mapSpins():
    logger.info(f'Querying unmaped spins')
    with Session() as session, session.begin():
        try:
            spins = session.scalars(select(Spin).where(Spin.song == None)).all()
            for spin in spins:
                logger.info(f'Mapping {spin}')
                findOrCreateSong(spin, session)
        except KeyboardInterrupt:
            logger.info(f'Stopping')


def findOrCreateSong(spin, session):
    song = session.scalars(
        select(Song)
        .where(Song.title == spin.title and Song.artist == spin.artist)
    ).first()
    if song:
        logger.info(f'Found {song} in database')
    if song is None:
        try:
            song = matchSpinToSpotify(spin)
        except Exception as e:
            logger.error(f'Spotify error while querying {spin}\n{e}')
            return
        dup = session.scalars(select(Song).where(Song.spotify_id == song.spotify_id)).first()
        if dup:
            logger.info(f'{song} seems to be a duplicate of {dup}')
            song = dup
        else:
            session.add(song)
    song.spins.append(spin)


def matchSpinToSpotify(spin):
    spotify_id = None
    album = spin.album
    year = spin.year

    try:
        for qf in [spin.toFilterQuery, spin.toSimpleQuery, spin.toQuery]:
            q = qf()
            logger.info(f'Querying spotify q="{q}"')
            results = spotify.search_track(q)
            if results:
                break
    except HTTPError as e:
        if e.code == 400:
            logger.error(f'Got 400 with {q}')
            results = spotify.search_track(spin.toSimpleQuery())

    if not results:
        logger.warning(f'Nothing matches {spin}')
    else:
        result = results[0]
        logger.info(f'Best match for {spin}:\n\t{result}')
        spotify_id = results[0]['id']

        album = album or result['album']
        year = year or int(result['date'] if len(result['date']) == 4 else result['date'][:4])

    return Song(
        spotify_id=spotify_id,
        title=spin.title,
        artist=spin.artist,
        album=album,
        year=year
    )
