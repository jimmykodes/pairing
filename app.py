import json
import math
import os
import random
from datetime import datetime, timedelta
from logging.config import dictConfig

from dateutil.parser import parse
from flask import Flask, jsonify, request

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)


SCHEDULE_FILE = os.environ.get("SCHEDULE_FILE", "schedule.json")
SCHEDULE_DURATION = int(os.environ.get("SCHEDULE_DURATION", "7"))
TEAM = os.environ.get("TEAM")
if TEAM:
    TEAM = TEAM.split(",")
ADMIN_AUTH = os.environ.get("ADMIN_AUTH")
USER_AUTH = os.environ.get("USER_AUTH")


def get_schedule_data():
    try:
        with open(SCHEDULE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def is_authenticated(must_be_admin=False):
    auth = request.headers.get("Authorization")
    if not auth:
        return False, "no credentials provided"
    auth = auth.split()
    if auth[0].lower() != "token":
        return False, "invalid auth type"
    valid_passwords = [ADMIN_AUTH]
    if not must_be_admin:
        valid_passwords.append(USER_AUTH)
    if auth[1] not in valid_passwords:
        return False, "invalid auth token"
    return True, None


@app.route('/')
def home():
    authenticated, message = is_authenticated()
    if not authenticated:
        return jsonify({"error": message}), 401

    schedule = get_schedule_data()
    timestamp = schedule.get("timestamp")

    if not timestamp or parse(timestamp) < datetime.utcnow() - timedelta(days=SCHEDULE_DURATION):
        # we don't have a timestamp or it has expired, make a new schedule
        app.logger.info("making new schedule")
        schedule = make_new_schedule(schedule)
    else:
        app.logger.info("using old schedule")

    return jsonify(schedule)


def make_new_schedule(schedule):
    old = []
    pairs = schedule.get("pairs")
    if pairs:
        for pair in pairs:
            old.append(pair[0])
            if pair[1]:
                # make sure we dont keep a blank string
                old.append(pair[1])
        new = old[1:] + old[:1]
    else:
        new = TEAM
    schedule = {
        "pairs": [[new[i], new[i + 1] if i + 1 < len(new) else ""] for i in range(0, len(new), 2)],
        "timestamp": datetime.utcnow().isoformat()
    }
    with open(SCHEDULE_FILE, 'w+') as f:
        json.dump(schedule, f)
    return schedule


@app.route('/force_reset', methods=('POST',))
def force_reset():
    authenticated, message = is_authenticated(must_be_admin=True)
    if not authenticated:
        return jsonify({"error": message}), 401
    schedule = get_schedule_data()
    schedule = make_new_schedule(schedule)
    return jsonify(schedule), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port="8000", debug=True)
