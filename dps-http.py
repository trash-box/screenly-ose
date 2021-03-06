# -*- coding: utf-8 -*-

import json
from os import getenv, makedirs, mkdir, path, remove, rename, statvfs, stat
from datetime import timedelta

from flask import Flask, make_response, render_template, request, send_from_directory, url_for
from flask_cors import CORS
from flask_restful_swagger_2 import Api, Resource, Schema, swagger
from flask_swagger_ui import get_swaggerui_blueprint

import paho.mqtt.client as mqtt
import threading, datetime

from lib import db, queries, diagnostics, utils

from gunicorn.app.base import Application
from werkzeug.wrappers import Request
from hurry.filesize import size
from subprocess import check_output
from settings import auth_basic, settings, LISTEN, PORT, get_mqtt_namespace

HOME = getenv('HOME', '/home/pi')
DISABLE_MANAGE_NETWORK = '.screenly/disable_manage_network'

app = Flask(__name__)
CORS(app)

################################
# Views
################################


def is_up_to_date():
    """
    Determine if there is any update available.
    Used in conjunction with check_update() in viewer.py.
    """

    sha_file = path.join(settings.get_configdir(), 'latest_screenly_sha')

    # Until this has been created by viewer.py,
    # let's just assume we're up to date.
    if not path.exists(sha_file):
        return True

    try:
        with open(sha_file, 'r') as f:
            latest_sha = f.read().strip()
    except:
        latest_sha = None

    if latest_sha:
        branch_sha = git('rev-parse', 'HEAD')
        return branch_sha.stdout.strip() == latest_sha

    # If we weren't able to verify with remote side,
    # we'll set up_to_date to true in order to hide
    # the 'update available' message
    else:
        return True

def template(template_name, **context):
    """Screenly template response generator. Shares the
    same function signature as Flask's render_template() method
    but also injects some global context."""

    # Add global contexts
    context['up_to_date'] = is_up_to_date()
    context['default_duration'] = settings['default_duration']
    context['default_streaming_duration'] = settings['default_streaming_duration']
    context['use_24_hour_clock'] = settings['use_24_hour_clock']
    context['template_settings'] = {
        'imports': ['from lib.utils import template_handle_unicode'],
        'default_filters': ['template_handle_unicode'],
    }
    context['version'] = utils.get_version()

    return render_template(template_name, context=context)

@app.route('/')
def viewDps():
    player_id = utils.get_serial() + ' '  + utils.get_version()
    player_ip = utils.get_node_ip()

    return template('dps.html', ip_lookup=True, msg=player_id, ip=player_ip, mqtt_namespace=get_mqtt_namespace())


@app.route('/info')
#@auth_basic
def system_info():
    viewlog = None
    try:
        viewlog = None
        #viewlog = check_output(['sudo', 'systemctl', 'status', 'screenly-viewer.service', '-n', '20']).decode('utf-8').split('\n')
    except:
        pass

    loadavg = diagnostics.get_load_avg()['15 min']

    display_info = diagnostics.get_monitor_status()

    display_power = diagnostics.get_display_power()

    temperature = diagnostics.get_temperature()

    # Calculate disk space
    slash = statvfs("/")
    free_space = size(slash.f_bavail * slash.f_frsize)

    # Get uptime
    uptime_in_seconds = diagnostics.get_uptime()
    system_uptime = timedelta(seconds=uptime_in_seconds)

    # PlayerID for title
    player_id = utils.get_serial()

    return template(
        'system_info.html',
        player_id=player_id,
        viewlog=viewlog,
        loadavg=loadavg,
        free_space=free_space,
        uptime=system_uptime,
        display_info=display_info,
        display_power=display_power,
        temperature=temperature
    )

@app.errorhandler(403)
def mistake403(code):
    return 'The parameter you passed has the wrong format!'


@app.errorhandler(404)
def mistake404(code):
    return 'Sorry, this page does not exist!'


if __name__ == "__main__":
    # Make sure the asset folder exist. If not, create it
    if not path.isdir(settings['assetdir']):
        mkdir(settings['assetdir'])
    # Create config dir if it doesn't exist
    if not path.isdir(settings.get_configdir()):
        makedirs(settings.get_configdir())

    with db.conn(settings['database']) as conn:
        with db.cursor(conn) as cursor:
            cursor.execute(queries.exists_table)
            if cursor.fetchone() is None:
                cursor.execute(assets_helper.create_assets_table)

    config = {
        'bind': '{}:{}'.format(LISTEN, PORT),
        'threads': 2,
        'timeout': 20
    }

    class GunicornApplication(Application):
        def init(self, parser, opts, args):
            return config

        def load(self):
            return app

    GunicornApplication().run()
