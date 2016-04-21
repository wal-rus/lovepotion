#!/usr/bin/env python

import os
import shutil
import tempfile
import unittest

# Local imports.
import user_db


class TestUserDb(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.user_db = os.path.join(self.temp_dir, 'users.db')

    def tearDown(self):
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def testStuff(self):
        users = user_db.UserDb(self.user_db, self.temp_dir)

        def _TestValid(rfid, expected_name):
            valid, name = users.AuthorizeRfidTag(rfid)
            self.assertTrue(valid)
            self.assertEqual(expected_name, name)

        def _TestNotValid(rfid):
            valid, _ = users.AuthorizeRfidTag(rfid)
            self.assertFalse(valid)

        _TestNotValid('abcd')

        users.AddUser('abcd', 'johnny', 'admin')
        _TestValid('abcd', 'johnny')

        # Rfid already exists.
        self.assertRaises(user_db.UserDbError, users.AddUser, 'abcd', 'bobby', 'qwe')

        # Add another user, test both.
        users.AddUser('1111', 'bobby', 'magical_superpowers')
        _TestValid('abcd', 'johnny')
        _TestValid('1111', 'bobby')

        # Test that the file was written.
        with open(self.user_db) as fh:
            contents = fh.read()
            self.assertIn('bobby', contents)
            self.assertIn(' by admin', contents)
            self.assertIn(' by magical_superpowers', contents)

        # Try to replace with empty or broken values.
        self.assertRaises(user_db.UserDbError, users.ReplaceUserDatabase, '# foo')
        self.assertRaises(user_db.UserDbError, users.ReplaceUserDatabase, 'gah:')
        self.assertRaises(user_db.UserDbError, users.ReplaceUserDatabase, ':zz')
        self.assertRaises(user_db.UserDbError, users.ReplaceUserDatabase, 'a:b:invalid=field')

        # Replace with a good database. Also test user/password handling.
        users.ReplaceUserDatabase(
                ' f00 :   bar :user=foo: ' +
                'password = 26c4202eb475d02864b40827dfff11a14657aa41:admin=yes')

        _TestNotValid('abcd')
        _TestValid('f00', 'bar')
        valid, admin = users.AuthorizeUser('foo', 'meh')
        self.assertTrue(valid)
        self.assertEqual('yes', admin)
        self.assertFalse(users.AuthorizeUser('foo', 'meh2')[0])
        self.assertFalse(users.AuthorizeUser('zing', 'meh')[0])

        # Test that the file was written.
        with open(self.user_db) as fh:
            contents = fh.read()
            self.assertIn('f00', contents)

        # Test recreating the object. The file should be read in.
        users2 = user_db.UserDb(self.user_db, self.temp_dir)
        _TestNotValid('abcd')
        _TestValid('f00', 'bar')

        # TODO: add a test for backups.


if __name__ == '__main__':
    unittest.main()
