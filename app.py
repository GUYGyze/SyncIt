from flask import Flask, redirect, request, session, url_for, render_template, jsonify
from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
import requests
import base64

last_track_id = None
last_youtube_url = None

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

def search_youtube(query):
    from googleapiclient.errors import HttpError

    youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

    try:
        request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            maxResults=1
        )
        response = request.execute()

        if response['items']:
            video_id = response['items'][0]['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            return video_url
        else:
            return None

    except HttpError as e:
        # Si quota dépassé ou autre erreur
        print(f"YouTube API Error: {e}")
        return "YOUTUBE_QUOTA_EXCEEDED"


@app.route('/api/current_track')
def api_current_track():
    global last_track_id, last_youtube_url

    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'Not logged in'})

    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    r = requests.get(CURRENT_TRACK_URL, headers=headers)

    if r.status_code != 200:
        return jsonify({'error': 'No track playing'})

    data = r.json()
    track_name = data['item']['name']
    artist_name = data['item']['artists'][0]['name']
    track_id = data['item']['id']

    if track_id != last_track_id:
        query = f"{track_name} {artist_name}"
        youtube_url = search_youtube(query)

        if youtube_url == "YOUTUBE_QUOTA_EXCEEDED":
            video_id = None
            quota_exceeded = True
        else:
            video_id = youtube_url.split("v=")[-1] if youtube_url else None
            quota_exceeded = False

        last_track_id = track_id
        last_youtube_url = {
            'track_name': track_name,
            'artist_name': artist_name,
            'video_id': video_id,
            'spotify_id': track_id,
            'quota_exceeded': quota_exceeded
        }

    return jsonify(last_youtube_url)

@app.route('/')
def index():
    return render_template('index.html')

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
        return render_template('current_track.html', track=None)

    data = r.json()
    track_name = data['item']['name']
    artist_name = data['item']['artists'][0]['name']

    # Recherche sur YouTube (si implémentée)
    query = f"{track_name} {artist_name}"
    youtube_url = search_youtube(query)

    return render_template('current_track.html', track={'name': track_name, 'artist': artist_name, 'youtube': youtube_url})

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

if __name__ == '__main__':
    app.run(debug=True)
