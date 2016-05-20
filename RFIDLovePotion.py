#!/usr/bin/env python

from __future__ import print_function

# System imports.
import argparse
from flask import Flask, redirect, render_template, request, session, url_for
from datetime import datetime
import Queue
import os
import signal
import sys
import threading
import time

# Local imports.
import hardware
import log_writer
import reverse_proxy_hack
import send_string
import user_db


def ParseFlags():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mock', action='store_true', help='Use mock hardware')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--open_time', type=int, default=3,
                        help='Time in seconds to keep lock open')
    parser.add_argument('--user_db', default='~/.config/lovepotion/users.db', type=str,
                        help='User database file location')
    parser.add_argument('--user_db_backup_dir', default='~/.config/lovepotion/users_backup', type=str,
                        help='User database backup directory')
    parser.add_argument('--speak_server', default='192.168.1.17', type=str,
                        help='TTS server')
    parser.add_argument('--speak_port', default=4000, type=int,
                        help='TTS server port')
    parser.add_argument('--log_file', default='~/.config/lovepotion/log.txt', type=str,
                        help='Location of the log file')
    parser.add_argument('--pin_config', default='~/.config/lovepotion/pins.cfg',
                        type=str, help='Location of the pin configuration file')

    args = parser.parse_args()
    return args


class Server(object):

    def __init__(self):
        self._args = ParseFlags()

        self._users = user_db.UserDb(
                self._args.user_db, self._args.user_db_backup_dir)
        self._hw = hardware.Instantiate(self._args.mock, self._args.open_time,
                                        os.path.expanduser(self._args.pin_config))
        self._speak_server = send_string.SendString(
                self._args.speak_server,
                self._args.speak_port)

        self._log = log_writer.LogWriter(self._args.log_file)
        # Last seen rfid tag, if it was unauthorized, otherwise, empty string.
        self._last_rfid = ''

    def _TagSeenHandler(self, rfid):
        print("Tag Read: %s" % rfid)
        authorized, name = self._users.AuthorizeRfidTag(rfid)
        self._log.Log(rfid=rfid, authorized=authorized, name=name)
        if authorized:
            msg = '%s goes there' % name
            self._speak_server.Send(msg)
            self._hw.UnlockDoor()
            self._last_rfid = ''
        else:
            self._last_rfid = rfid

    def _EditHandler(self):
        if not session.get('admin') == 'yes':
            return redirect(url_for('login'))
        message = ''
        users = self._users.GetUserDatabase()
        if request.method == 'POST' and request.form.get('save'):
            users = request.form['users']
            if users:
                try:
                    self._users.ReplaceUserDatabase(users)
                    message = 'Saved!'
                except user_db.UserDbError, e:
                    print(e)
                    message = str(e)
        return render_template('edit.html', users=users, message=message)

    def _IndexHandler(self):
        if not session.get('logged_in'):
            return redirect(url_for('login', _external=True))
        message = ''
        if session.get('admin') == 'yes':
            if request.method == 'POST' and request.form.get('add'):
                rfid = request.form.get('rfid')
                name = request.form.get('name')
                try:
                    self._users.AddUser(rfid, name, session.get('user'))
                except user_db.UserDbError, e:
                    print(e)
                    message = 'Failed to add user: %s' % str(e)
                else:
                    message = 'User added!'
                    self._last_rfid = ''
                    self._log.Log(
                            action='add_user',
                            admin=session.get('user'),
                            rfid=rfid,
                            name=name)

        return render_template(
                'index.html',
                admin=session.get('admin'),
                last_lines=self._log.GetLastLines(),
                rfid=self._last_rfid,
                message=message)

    def _QuitHandler(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
        return 'bye bye'

    def _LoginHandler(self):
        if request.method == 'POST':
            user = request.form['user']
            pwd = request.form['password']
            if user and pwd:
                authorized, admin = self._users.AuthorizeUser(user, pwd)
                self._log.Log(user=user, authorized=authorized)
                if authorized:
                    session['logged_in'] = True
                    session['admin'] = admin
                    session['user'] = user
                    return redirect(url_for('index', _external=True))
        return self._app.send_static_file('login.html')

    def _OpenHandler(self):
        if request.method == 'POST':
            if session.get('logged_in'):
                user = session.get('user')
                self._log.Log(user=user, unlock=True)
                msg = 'website user %s goes there' % user
                self._speak_server.Send(msg)
                self._hw.UnlockDoor()
        return redirect(url_for('index', _external=True))

    def _LogoutHandler(self):
        session.pop('logged_in', None)
        return redirect(url_for('index', _external=True))

    def Serve(self):
        self._hw.Initialize()
        self._hw.SetTagSeenHandler(self._TagSeenHandler)

        self._app = Flask(__name__)
        self._app.wsgi_app = reverse_proxy_hack.ReverseProxied(
                self._app.wsgi_app)
        # We generate a new session key every time the server starts. This way,
        # old sessions are invalidated on server restart and users have to log
        # in again.
        self._app.secret_key = os.urandom(24)
        self._app.add_url_rule('/', 'index', self._IndexHandler, methods=['GET', 'POST'])
        self._app.add_url_rule('/logout', 'logout', self._LogoutHandler, methods=['GET', 'POST'])
        self._app.add_url_rule('/login', 'login', self._LoginHandler, methods=['GET', 'POST'])
        self._app.add_url_rule('/open', 'open', self._OpenHandler, methods=['POST'])
        self._app.add_url_rule('/edit', 'edit', self._EditHandler, methods=['GET', 'POST'])
        self._app.add_url_rule('/quitquitquit', 'quitquitquit', self._QuitHandler)

        # Run in debug mode if --mock was given.
        # In either case, we run with the default non-threaded,
        # non-multiprocess server. If we ever want to change that, we need to
        # make the application watch the user database and re-read it.
        self._app.run(port=self._args.port, debug=self._args.mock)

        self._hw.ShutDown()
        exit(0)


def Main():
    server = Server()
    server.Serve()

if __name__ == '__main__':
    Main()
