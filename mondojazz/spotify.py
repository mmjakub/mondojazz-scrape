from base64 import b64encode
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import urllib.parse
import urllib.request
import webbrowser

def get_handler(callback):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            callback(self.path)
            self.send_response_only(200)
            self.end_headers()
    return Handler

def api(endpoint):
    if endpoint[0] == '/':
        endpoint = endpoint[1:]
    return f'https://api.spotify.com/v1/{endpoint}'

class AuthHandler(urllib.request.BaseHandler):

    TOKEN_ENDPOINT = 'https://accounts.spotify.com/api/token'

    def __init__(self, client_id, client_secret, access_token, refresh_token):
        self.basic_auth_header = 'Basic ' + b64encode(f'{client_id}:{client_secret}'.encode()).decode()
        self.bearer_auth_header = 'Bearer ' + access_token
        self.refresh_token = refresh_token

    def https_request(self, req):
        if not req.has_header('Authorization'):
            req.add_header('Authorization', self.bearer_auth_header)
        return req

    def http_error_401(self, req, fp, code, msg, hdrs):
        self._refresh_token()
        req.remove_header('Authorization')
        return self.parent.open(req)

    def _refresh_token(self):
        req = urllib.request.Request(
                self.TOKEN_ENDPOINT,
                data=urllib.parse.urlencode({
                        'grant_type': 'refresh_token',
                        'refresh_token': self.refresh_token
                    }).encode(),
                headers={'Authorization': self.basic_auth_header},
                method='POST')
        with urllib.request.urlopen(req) as f:
            res = json.load(f)
        self.bearer_auth_header = 'Bearer ' + res['access_token']
        if 'refresh_token' in res:
            self.refresh_token = res['refresh_token']

class SpotifyClient:

    ENV_CLIENT_ID = 'SPOTIFY_CLIENT_ID'
    ENV_CLIENT_SECRET = 'SPOTIFY_CLIENT_SECRET'
    ENV_ACCESS_TOKEN = 'SPOTIFY_ACCESS_TOKEN'
    ENV_REFRESH_TOKEN = 'SPOTIFY_REFRESH_TOKEN'

    def __init__(self):
        self.client_id = os.getenv(self.ENV_CLIENT_ID)
        self.client_secret = os.getenv(self.ENV_CLIENT_SECRET)
        self.access_token = os.getenv(self.ENV_ACCESS_TOKEN, 'foo')
        self.refresh_token = os.getenv(self.ENV_REFRESH_TOKEN)
        self.redirect_uri = 'http://127.0.0.1:3000/callback'
        self.scope = 'playlist-modify-public playlist-read-private'
        if not self.refresh_token:
            self._authorize()
        self.handler = AuthHandler(self.client_id, self.client_secret, self.access_token, self.refresh_token)
        self.opener = urllib.request.build_opener(self.handler)
        self.user_id = self.call('/me')['id']

    def call(self, endpoint, data=None, method='GET'):
        if data:
            data=urllib.parse.urlencode(data)
            if method == 'GET':
                endpoint = endpoint + '?' + data
                print(endpoint)
                data = None
            else:
                data = data.encode()
        req = urllib.request.Request(api(endpoint),
                                     data=data,
                                     method=method)
        with self.opener.open(req) as f:
            return json.load(f)

    def search_track(self, hints):
        if '' in hints:
            q = hints['']
            del hints['']
        else:
            q = ''
        if hints:
            q += ' ' + ' '.join(f'{k}:{v}' for k, v in hints.items())

        endpoint = '/search?' + urllib.parse.urlencode({'q': q, 'type': 'track'})
        
        with self.opener.open(api(endpoint)) as f:
            body = json.load(f)
        return [
            {
                'id': e['id'],
                'track': e['name'],
                'album': e['album']['name'],
                'date': e['album']['release_date'],
                'artist': ', '.join(a['name'] for a in e['artists'])
            } for e in body['tracks']['items']]

    def create_playlist(self, name, description):
        req = urllib.request.Request(
                api(f'/users/{self.user_id}/playlists'), 
                data=json.dumps({'name': name, 'description': description}).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST')
        with self.opener.open(req) as f:
            body = json.load(f)
        return body['id']
    
    def add_items_to_playlist(self, playlist_id, items):
        uris = [f'spotify:track:{e}' for e in items]
        req = urllib.request.Request(
                api(f'/playlists/{playlist_id}/tracks'), 
                data=json.dumps({'uris': uris}).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST')
        with self.opener.open(req) as f:
            body = json.load(f)
        return body['snapshot_id']
                
    def _authorize(self):
        webbrowser.open(f'https://accounts.spotify.com/authorize'\
            f'?client_id={self.client_id}'\
            f'&response_type=code'\
            f'&redirect_uri={self.redirect_uri}'\
            f'&scope={self.scope}')
        
        with HTTPServer(('', 3000), get_handler(self._callback)) as srv:
            srv.handle_request()
            srv.server_close()

        req = urllib.request.Request(
                url='https://accounts.spotify.com/api/token',
                data=urllib.parse.urlencode({
                    'grant_type': 'authorization_code',
                    'code': self.callback['code'],
                    'redirect_uri': self.redirect_uri
                }).encode(),
                headers={
                    'Authorization':
                    'Basic ' + b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()
                },
                method='POST')
        #req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        with urllib.request.urlopen(req) as f:
            res = json.load(f)
        self.access_token = res['access_token']
        self.refresh_token = res['refresh_token']

    def _callback(self, path):
        self.path = path
        self.callback = dict(part.split('=') for part in path[len('/callback?'):].split('&'))
        


