"""Python Flask WebApp Auth0 integration example
"""
from functools import wraps
import json
from os import environ as env
from collections import namedtuple

from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import request
from flask import flash
# Global storage, remove when games are persistently stored elsewhere?
from flask import g
from flask import render_template
from flask import session
from flask import url_for
from authlib.integrations.flask_client import OAuth
from urllib.parse import urlencode
from redis import from_url as redis_connection

import forms
import constants
import games

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

AUTH0_CALLBACK_URL = env.get(constants.AUTH0_CALLBACK_URL)
AUTH0_CLIENT_ID = env.get(constants.AUTH0_CLIENT_ID)
AUTH0_CLIENT_SECRET = env.get(constants.AUTH0_CLIENT_SECRET)
AUTH0_DOMAIN = env.get(constants.AUTH0_DOMAIN)
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = env.get(constants.AUTH0_AUDIENCE)
REDIS_URL = env.get(constants.REDIS_URL)

app = Flask(__name__, static_url_path='/public', static_folder='./public')
app.secret_key = constants.SECRET_KEY
app.debug = True

def redis_conn():
    conn = getattr(g,'_redis', None)
    if conn is None:
        conn = g._redis = redis_connection(REDIS_URL)
    return conn

@app.teardown_appcontext
def close_connection(exception):
    conn = getattr(g, '_redis', None)
    if conn is not None:
        conn.close()

@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response


oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated


# Controllers API
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/dashboard')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session[constants.PROFILE_KEY],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))


@app.route('/party/new', methods=['GET', 'POST'])
@requires_auth
def create_party():
    form = forms.NewGame(request.form)
    if request.method == 'POST' and form.validate():
        # This needs to be refactored to separate view from controller
        gamename = form.gamename.data.encode() # everything is stored in bytes in redis
        # check if that name already exists in db before going further.
        if (existing_party := redis_conn().get(b"party-%s" % gamename)) is not None:
            if games.Party.deserialize(existing_party).game_over:
                flash("Re-creating a game (named %s). Click now on the right game to join the game." % form.gamename.data)
            else:
                flash("A game named %s already exists. Redirecting you to join page...." % form.gamename.data)
                return redirect('/party/list')
        else:
            flash("Creating a game (named %s). Please join manually." % form.gamename.data)
        
        party = games.Party(gamename)
        party.add_player(session[constants.JWT_PAYLOAD]['nickname'])
        # pickle is (most likely?) safe, as we can assume github nicknames are going through validations
        redis_conn().set(b"party-%s" % gamename, party.serialize())
        return redirect('/party/list')
    return render_template('new-party.html', userinfo_pretty=session[constants.JWT_PAYLOAD], form=form)    


@app.route('/party/list', methods=['GET'])
@requires_auth
def list_parties():
    _, games_names = redis_conn().scan(match='party-*', count=constants.MAX_REDIST_RECORDS_PER_LIST)
    games_details = redis_conn().mget(games_names)
    gamelist = list(map(games.Party.deserialize, games_details))
    
    roster = []
    for game in gamelist:
        roster.append({
            "name" : bytes.decode(game.party_name),
            "players": list(game.players),
            "link": "/games/ideasthesia/%s" % game.uuid,
        })
    return render_template('list-party.html', gameroster=roster)    


@app.route('/games/ideasthesia/<uuid:gameid>')
@requires_auth
def ideasthesia_game(gameid):
    return render_template('ideasthesia-game.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=env.get('PORT', 3000))
