from flask import Flask, redirect, request, session, url_for
from dotenv import load_dotenv
import os
import requests
import base64

load_dotenv(dotenv_path='sec.env')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
CURRENT_TRACK_URL = 'https://api.spotify.com/v1/me/player/currently-playing'

SCOPE = 'user-read-playback-state'

@app.route('/')
def index():
    return '<a href="/login">Connect to Spotify</a>'

@app.route('/login')
def login():
    auth_query = {
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
        'client_id': CLIENT_ID
    }
    url_args = '&'.join([f"{key}={val}" for key, val in auth_query.items()])
    return redirect(f"{AUTH_URL}?{url_args}")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()

    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    token_headers = {
        'Authorization': f"Basic {b64_auth_str}"
    }

    r = requests.post(TOKEN_URL, data=token_data, headers=token_headers)
    token_response_data = r.json()

    session['access_token'] = token_response_data['access_token']

    return redirect(url_for('current_track'))

@app.route('/current_track')
def current_track():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    r = requests.get(CURRENT_TRACK_URL, headers=headers)

    if r.status_code != 200:
        return 'No track currently playing.'

    data = r.json()
    track_name = data['item']['name']
    artist_name = data['item']['artists'][0]['name']

    return f"You're listening to: {track_name} by {artist_name}"

if __name__ == '__main__':
    app.run(debug=True)
