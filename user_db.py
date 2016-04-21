#!/usr/bin/env python
#
# Module that takes care of users and authentication.
#
# The user database is stored in a plain text file. A line
# can contain comments prefixed by a '#' symbol. A non-blank
# line is colon-delimited and in its basic form looks like this:
#
#   <rfid serial number>:<name of the person>
#
# It can also contain more key=value pairs, by using additional colon-delimited
# fields. For example, to allow logging in to the web server (and thus open the
# door remotely), you specify "user" and "password" fields like this:
#
#   <rfid>:<name>:user=<user>:password=<password>
#
# The format was chosen over JSON (or similar formats) to make it easier to
# read and edit by hand.
#
# Currently supported key names:
#
#    "user": username for logging in
#    "password": sha1 hash of the password (echo -n 'pwd' | sha1sum)
#    "admin=yes": allow editing user database/adding new keys
#
# When new users are added by the system, they are appended to the
# end of the file. To maintain comments and formatting, new users
# are added as text to the end of the file and the file gets reparsed.
#
# Future ideas
# ============
#
# Implement time-based access control. E.g., have a section in the file
# that defines times, and then define allowed time periods per-user. This
# would allow most users access during work nights, for example. Possible
# format:
#
# [times]
# workday:wed 1830-2300
#
# [users]
# aee34141234:jimmy test:time=workday

from __future__ import print_function

import collections
import hashlib
import os
import re
import shutil
import time


User = collections.namedtuple('User', 'rfid name user password admin')


class UserDbError(Exception):
    """Failed to parse user file."""
    pass


def _ReadFileOrDefault(filename, default):
    """Returns file contents if file exists, empty string otherwise."""
    if os.path.exists(filename):
        with open(filename) as fh:
            return fh.read()
    else:
        return default


def _NormalizeRfid(rfid):
    """Normalizes and checks whether given RFID value is valid."""
    clean = rfid.strip().lower()
    if re.match('^[a-f0-9]+$', clean):
        return rfid
    if not rfid:
        raise UserDbError('RFID empty!')
    raise UserDbError('Invalid RFID: %s' % rfid)


def _ParseUserLine(line, orig_line):
    """Parses a single user database line."""
    items = re.split('\s*:\s*', line)
    if len(items) < 2:
        raise UserDbError('Failed to parse line: %s' % orig_line)
    fields = dict((key, None) for key in User._fields)
    fields['rfid'] = _NormalizeRfid(items[0])
    fields['name'] = items[1]

    if not fields['rfid'] or not fields['name']:
        raise UserDbError('RFID or name empty in line: %s' % orig_line)

    # Parse the rest of fields.
    for item in items[2:]:
        if '=' not in item:
            raise UserDbError('Failed to parse line: %s' % orig_line)
        key, value = re.split('\s*=\s*', item, 1)
        # Make sure the field name is valid.
        if key not in fields:
            raise UserDbError('Invalid key "%s" in line: %s' % (key, orig_line))
        fields[key] = value

    return User(**fields)


def _ParseUsers(blob):
    """Parses a blob of text into User instances.

    Resulting dict maps lowercase RFID serial numbers to User instances.
    """
    users = {}
    for orig_line in blob.splitlines():
        line = orig_line.strip()
        # Strip off comments.
        line = re.sub('\s*#.*$', '', line)
        if not line:
            # Empty line or comment only.
            continue
        parsed = _ParseUserLine(line, orig_line)
        users[parsed.rfid] = parsed
    return users


class UserDb(object):
    """Class keeping track of users."""

    def __init__(self, user_file, backup_dir):
        # Expand '~/'.
        self._user_file = os.path.expanduser(user_file)
        # Expand '~/'.
        self._backup_dir = os.path.expanduser(backup_dir)

        if not os.path.isdir(self._backup_dir):
            raise ValueError('Backup directory "%s" does not exist!' % self._backup_dir)

        # Raw user database. Note: we append new users to the file (and the raw version) so
        # that we can keep the formatting and comments.
        self._users_raw = _ReadFileOrDefault(self._user_file, '# User database.\n')
        # Parsed user database, mapping from lowercase RFID serial numbers to User objects.
        self._users = _ParseUsers(self._users_raw)

    def AuthorizeUser(self, user, password):
        """Checks whether given user/password combo is valid.

        Args:
            user: str, user name
            password: str, raw password (before sha1-ing)

        Returns:
            (authorized, admin), where:
                authorized: bool, whether the user is authorized
                admin: str or None. If str, contents of 'admin' value
        """
        if not user or not password:
            return (False, None)
        sha1 = hashlib.sha1()
        sha1.update(password)
        digest = sha1.hexdigest().lower()
        for u in self._users.itervalues():
            if not u.user or not u.password:
                continue

            if u.user.lower() == user.lower() and u.password == digest:
                return (True, u.admin)
        return (False, None)

    def AuthorizeRfidTag(self, rfid):
        """Checks whether given RFID tag is authorized.

        Args:
            rfid: string, RFID serial number.

        Returns:
           (authorized, name) tuple, where:
             authorized: bool, whether the user is authorized
             name: str or None. If str, name associated with RFID tag.
        """
        rfid = rfid.lower()
        if rfid not in self._users:
            return (False, None)
        # TODO: we could add the time based logic here.
        return (True, self._users[rfid].name)

    def _SaveAndBackupUserDatabase(self):
        """Saves self._users_raw and backs it up."""
        # Write to a temp file and then move it in place to make the operation atomic.
        tmp = self._user_file + '.tmp'
        with open(tmp, 'w') as fh:
            fh.write(self._users_raw)

        # First, copy to a backup.
        backup_name = time.strftime('%Y%m%d_%H%M%S.db')
        backup_file = os.path.join(self._backup_dir, backup_name)
        shutil.copy(tmp, backup_file)

        # Then, move it in place.
        os.rename(tmp, self._user_file)

        # Reparse the user list.
        self._users = _ParseUsers(self._users_raw)

    def AddUser(self, rfid, name, admin_user):
        """Adds a new user to the database."""
        rfid = _NormalizeRfid(rfid)
        name = name.replace(':', '')  # strip out colons.

        if not rfid or not name:
            raise UserDbError('RFID or name not provided')

        if rfid in self._users:
            raise UserDbError('RFID tag already exists in database')

        if not self._users_raw.endswith('\n'):
            self._users_raw += '\n'

        self._users_raw += '# Added on %s by %s\n' % (
                time.strftime('%Y-%m-%d %H:%M:%S'), admin_user)
        self._users_raw += '%s:%s\n' % (rfid, name)

        self._SaveAndBackupUserDatabase()

    def GetUserDatabase(self):
        """Returns the raw user database."""
        return self._users_raw

    def ReplaceUserDatabase(self, new_users_raw):
        """Replaces the user database with a new one."""
        # First, make sure we can parse the new database. If we can't, this will raise.
        parsed = _ParseUsers(new_users_raw)
        # As a sanity check, make sure there is at least one user in the new parsed data.
        if not parsed:
            raise UserDbError('New user database should include at least one record')
        self._users_raw = new_users_raw

        self._SaveAndBackupUserDatabase()
