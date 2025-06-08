__all__ = [
    'Session',
]

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mondojazz.spotify import SpotifyClient


engine_url = os.getenv('ENGINE_URL', 'sqlite:///mondojazz.db')
logging.getLogger(__name__).info(f'Using engine url: "{engine_url}"')

engine = create_engine(engine_url)
Session = sessionmaker(engine)
spotify = SpotifyClient()
