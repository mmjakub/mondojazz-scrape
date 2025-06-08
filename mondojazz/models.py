from datetime import datetime, time

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from . import engine

class Base(DeclarativeBase):

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    id: Mapped[int] = mapped_column(primary_key=True)
    
    
class HasSpotifyID:
    spotify_id: Mapped[str | None] = mapped_column(unique=True)


class SpotifyPlaylist(HasSpotifyID, Base):
    episode_id: Mapped[int] = mapped_column(ForeignKey('episode.id'))
    name: Mapped[str]
    desc: Mapped[str]
    
    episode: Mapped['Episode'] = relationship(back_populates='playlist')
    items: Mapped[list['PlaylistItem']] = relationship(back_populates='playlist')
    

class PlaylistItem(Base):
    index: Mapped[int]
    song_id: Mapped[int] = mapped_column(ForeignKey('song.id'))
    playlist_id: Mapped[int] = mapped_column(ForeignKey('spotifyplaylist.id'))
    
    song: Mapped['Song'] = relationship(back_populates='tracks')
    playlist: Mapped[SpotifyPlaylist] = relationship(back_populates='items')


class Episode(Base):
    number: Mapped[int] = mapped_column(unique=True)

    playlist: Mapped[SpotifyPlaylist] = relationship(back_populates='episode')
    spinitron_playlists: Mapped[list['SpinitronPlaylist']] = relationship(back_populates='episode')

    def getName(self):
        s = f'Mondo Jazz {self.number}'
        title = ''
        for stpl in self.spinitron_playlists:
            title = title or stpl.title
        if title:
            s += f': {title}'
        return s

    def getAirDates(self):
        return list(map(SpinitronPlaylist.getAirDate, self.spinitron_playlists))


class Song(HasSpotifyID, Base):
    artist: Mapped[str]
    title: Mapped[str]
    album: Mapped[str]
    year: Mapped[int]

    spins: Mapped[list['Spin']] = relationship(back_populates='song')
    tracks: Mapped[list[PlaylistItem]] = relationship(back_populates='song')

    def __repr__(self):
        return f'<Song: "{self.title}" - "{self.artist}" ({self.album}) {self.year}'

class Spin(Base):
    spinitron_id: Mapped[int] = mapped_column(unique=True)
    artist: Mapped[str]
    title: Mapped[str]
    album: Mapped[str]
    year: Mapped[int]
    start_time: Mapped[time]
    number: Mapped[int]
    playlist_id: Mapped[int | None] = mapped_column(ForeignKey('spinitronplaylist.id'))
    song_id: Mapped[int | None] = mapped_column(ForeignKey('song.id'))

    playlist: Mapped['SpinitronPlaylist'] = relationship(back_populates='spins')
    song: Mapped[Song] = relationship(back_populates='spins')

    def toFilterQuery(self):
        q = {
            '': self.title,
            'artist': self.artist,
        }
        if self.album:
            q['album'] = self.album
        if self.year:
            q['year'] = self.year
        return q

    def toQuery(self):
        return {'': ' '.join([self.title, self.artist, self.album, str(self.year)])}

    def toSimpleQuery(self):
        return {'': f'{self.title} {self.artist}'}

    def __repr__(self):
        return f'<Spin: "{self.title}" - "{self.artist}" ({self.album}) {self.year}'


class SpinitronPlaylist(Base):
    spinitron_id: Mapped[int] = mapped_column(unique=True)
    episode_id: Mapped[int | None] = mapped_column(ForeignKey('episode.id'))
    timeslot: Mapped[datetime] = mapped_column(unique=True)
    title: Mapped[str]
    desc: Mapped[str | None]
    
    episode: Mapped[Episode] = relationship(back_populates='spinitron_playlists')
    spins: Mapped[list[Spin]] = relationship(back_populates='playlist', cascade='all, delete')

    def getAirDate(self):
        return self.timeslot.strftime('%a %b %d %Y at %I:%M %p')
    
 
Base.metadata.create_all(engine)
