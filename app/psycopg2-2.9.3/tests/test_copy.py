#!/usr/bin/env python

# test_copy.py - unit test for COPY support
#
# Copyright (C) 2010-2019 Daniele Varrazzo  <daniele.varrazzo@gmail.com>
# Copyright (C) 2020-2021 The Psycopg Team
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# In addition, as a special exception, the copyright holders give
# permission to link this program with the OpenSSL library (or with
# modified versions of OpenSSL that use the same license as OpenSSL),
# and distribute linked combinations including the two.
#
# You must obey the GNU Lesser General Public License in all respects for
# all of the code used other than OpenSSL.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

import io
import sys
import string
import unittest
from .testutils import ConnectingTestCase, skip_before_postgres, slow, StringIO
from .testutils import skip_if_crdb
from itertools import cycle
from subprocess import Popen, PIPE

import psycopg2
import psycopg2.extensions
from .testutils import skip_copy_if_green, TextIOBase
from .testconfig import dsn


class MinimalRead(TextIOBase):
    """A file wrapper exposing the minimal interface to copy from."""
    def __init__(self, f):
        self.f = f

    def read(self, size):
        return self.f.read(size)

    def readline(self):
        return self.f.readline()


class MinimalWrite(TextIOBase):
    """A file wrapper exposing the minimal interface to copy to."""
    def __init__(self, f):
        self.f = f

    def write(self, data):
        return self.f.write(data)


@skip_copy_if_green
class CopyTests(ConnectingTestCase):

    def setUp(self):
        ConnectingTestCase.setUp(self)
        self._create_temp_table()

    def _create_temp_table(self):
        skip_if_crdb("copy", self.conn)
        curs = self.conn.cursor()
        curs.execute('''
            CREATE TEMPORARY TABLE tcopy (
              id serial PRIMARY KEY,
              data text
            )''')

    @slow
    def test_copy_from(self):
        curs = self.conn.cursor()
        try:
            self._copy_from(curs, nrecs=1024, srec=10 * 1024, copykw={})
        finally:
            curs.close()

    @slow
    def test_copy_from_insane_size(self):
        # Trying to trigger a "would block" error
        curs = self.conn.cursor()
        try:
            self._copy_from(curs, nrecs=10 * 1024, srec=10 * 1024,
                copykw={'size': 20 * 1024 * 1024})
        finally:
            curs.close()

    def test_copy_from_cols(self):
        curs = self.conn.cursor()
        f = StringIO()
        for i in range(10):
            f.write(f"{i}\n")

        f.seek(0)
        curs.copy_from(MinimalRead(f), "tcopy", columns=['id'])

        curs.execute("select * from tcopy order by id")
        self.assertEqual([(i, None) for i in range(10)], curs.fetchall())

    def test_copy_from_cols_err(self):
        curs = self.conn.cursor()
        f = StringIO()
        for i in range(10):
            f.write(f"{i}\n")

        f.seek(0)

        def cols():
            raise ZeroDivisionError()
            yield 'id'

        self.assertRaises(ZeroDivisionError,
            curs.copy_from, MinimalRead(f), "tcopy", columns=cols())

    @slow
    def test_copy_to(self):
        curs = self.conn.cursor()
        try:
            self._copy_from(curs, nrecs=1024, srec=10 * 1024, copykw={})
            self._copy_to(curs, srec=10 * 1024)
        finally:
            curs.close()

    def test_copy_text(self):
        self.conn.set_client_encoding('latin1')
        self._create_temp_table()  # the above call closed the xn

        abin = bytes(list(range(32, 127))
            + list(range(160, 256))).decode('latin1')
        about = abin.replace('\\', '\\\\')

        curs = self.conn.cursor()
        curs.execute('insert into tcopy values (%s, %s)',
            (42, abin))

        f = io.StringIO()
        curs.copy_to(f, 'tcopy', columns=('data',))
        f.seek(0)
        self.assertEqual(f.readline().rstrip(), about)

    def test_copy_bytes(self):
        self.conn.set_client_encoding('latin1')
        self._create_temp_table()  # the above call closed the xn

        abin = bytes(list(range(32, 127))
            + list(range(160, 255))).decode('latin1')
        about = abin.replace('\\', '\\\\').encode('latin1')

        curs = self.conn.cursor()
        curs.execute('insert into tcopy values (%s, %s)',
            (42, abin))

        f = io.BytesIO()
        curs.copy_to(f, 'tcopy', columns=('data',))
        f.seek(0)
        self.assertEqual(f.readline().rstrip(), about)

    def test_copy_expert_textiobase(self):
        self.conn.set_client_encoding('latin1')
        self._create_temp_table()  # the above call closed the xn

        abin = bytes(list(range(32, 127))
            + list(range(160, 256))).decode('latin1')
        about = abin.replace('\\', '\\\\')

        f = io.StringIO()
        f.write(about)
        f.seek(0)

        curs = self.conn.cursor()
        psycopg2.extensions.register_type(
            psycopg2.extensions.UNICODE, curs)

        curs.copy_expert('COPY tcopy (data) FROM STDIN', f)
        curs.execute("select data from tcopy;")
        self.assertEqual(curs.fetchone()[0], abin)

        f = io.StringIO()
        curs.copy_expert('COPY tcopy (data) TO STDOUT', f)
        f.seek(0)
        self.assertEqual(f.readline().rstrip(), about)

        # same tests with setting size
        f = io.StringIO()
        f.write(about)
        f.seek(0)
        exp_size = 123
        # hack here to leave file as is, only check size when reading
        real_read = f.read

        def read(_size, f=f, exp_size=exp_size):
            self.assertEqual(_size, exp_size)
            return real_read(_size)

        f.read = read
        curs.copy_expert('COPY tcopy (data) FROM STDIN', f, size=exp_size)
        curs.execute("select data from tcopy;")
        self.assertEqual(curs.fetchone()[0], abin)

    def _copy_from(self, curs, nrecs, srec, copykw):
        f = StringIO()
        for i, c in zip(range(nrecs), cycle(string.ascii_letters)):
            l = c * srec
            f.write(f"{i}\t{l}\n")

        f.seek(0)
        curs.copy_from(MinimalRead(f), "tcopy", **copykw)

        curs.execute("select count(*) from tcopy")
        self.assertEqual(nrecs, curs.fetchone()[0])

        curs.execute("select data from tcopy where id < %s order by id",
                (len(string.ascii_letters),))
        for i, (l,) in enumerate(curs):
            self.assertEqual(l, string.ascii_letters[i] * srec)

    def _copy_to(self, curs, srec):
        f = StringIO()
        curs.copy_to(MinimalWrite(f), "tcopy")

        f.seek(0)
        ntests = 0
        for line in f:
            n, s = line.split()
            if int(n) < len(string.ascii_letters):
                self.assertEqual(s, string.ascii_letters[int(n)] * srec)
                ntests += 1

        self.assertEqual(ntests, len(string.ascii_letters))

    def test_copy_expert_file_refcount(self):
        class Whatever:
            pass

        f = Whatever()
        curs = self.conn.cursor()
        self.assertRaises(TypeError,
            curs.copy_expert, 'COPY tcopy (data) FROM STDIN', f)

    def test_copy_no_column_limit(self):
        cols = [f"c{i:050}" for i in range(200)]

        curs = self.conn.cursor()
        curs.execute('CREATE TEMPORARY TABLE manycols (%s)' % ',\n'.join(
            ["%s int" % c for c in cols]))
        curs.execute("INSERT INTO manycols DEFAULT VALUES")

        f = StringIO()
        curs.copy_to(f, "manycols", columns=cols)
        f.seek(0)
        self.assertEqual(f.read().split(), ['\\N'] * len(cols))

        f.seek(0)
        curs.copy_from(f, "manycols", columns=cols)
        curs.execute("select count(*) from manycols;")
        self.assertEqual(curs.fetchone()[0], 2)

    def test_copy_funny_names(self):
        cols = ["select", "insert", "group"]

        curs = self.conn.cursor()
        curs.execute('CREATE TEMPORARY TABLE "select" (%s)' % ',\n'.join(
            ['"%s" int' % c for c in cols]))
        curs.execute('INSERT INTO "select" DEFAULT VALUES')

        f = StringIO()
        curs.copy_to(f, "select", columns=cols)
        f.seek(0)
        self.assertEqual(f.read().split(), ['\\N'] * len(cols))

        f.seek(0)
        curs.copy_from(f, "select", columns=cols)
        curs.execute('select count(*) from "select";')
        self.assertEqual(curs.fetchone()[0], 2)

    @skip_before_postgres(8, 2)     # they don't send the count
    def test_copy_rowcount(self):
        curs = self.conn.cursor()

        curs.copy_from(StringIO('aaa\nbbb\nccc\n'), 'tcopy', columns=['data'])
        self.assertEqual(curs.rowcount, 3)

        curs.copy_expert(
            "copy tcopy (data) from stdin",
            StringIO('ddd\neee\n'))
        self.assertEqual(curs.rowcount, 2)

        curs.copy_to(StringIO(), "tcopy")
        self.assertEqual(curs.rowcount, 5)

        curs.execute("insert into tcopy (data) values ('fff')")
        curs.copy_expert("copy tcopy to stdout", StringIO())
        self.assertEqual(curs.rowcount, 6)

    def test_copy_rowcount_error(self):
        curs = self.conn.cursor()

        curs.execute("insert into tcopy (data) values ('fff')")
        self.assertEqual(curs.rowcount, 1)

        self.assertRaises(psycopg2.DataError,
            curs.copy_from, StringIO('aaa\nbbb\nccc\n'), 'tcopy')
        self.assertEqual(curs.rowcount, -1)

    def test_copy_query(self):
        curs = self.conn.cursor()

        curs.copy_from(StringIO('aaa\nbbb\nccc\n'), 'tcopy', columns=['data'])
        self.assert_(b"copy " in curs.query.lower())
        self.assert_(b" from stdin" in curs.query.lower())

        curs.copy_expert(
            "copy tcopy (data) from stdin",
            StringIO('ddd\neee\n'))
        self.assert_(b"copy " in curs.query.lower())
        self.assert_(b" from stdin" in curs.query.lower())

        curs.copy_to(StringIO(), "tcopy")
        self.assert_(b"copy " in curs.query.lower())
        self.assert_(b" to stdout" in curs.query.lower())

        curs.execute("insert into tcopy (data) values ('fff')")
        curs.copy_expert("copy tcopy to stdout", StringIO())
        self.assert_(b"copy " in curs.query.lower())
        self.assert_(b" to stdout" in curs.query.lower())

    @slow
    def test_copy_from_segfault(self):
        # issue #219
        script = f"""import psycopg2
conn = psycopg2.connect({dsn!r})
curs = conn.cursor()
curs.execute("create table copy_segf (id int)")
try:
    curs.execute("copy copy_segf from stdin")
except psycopg2.ProgrammingError:
    pass
conn.close()
"""

        proc = Popen([sys.executable, '-c', script])
        proc.communicate()
        self.assertEqual(0, proc.returncode)

    @slow
    def test_copy_to_segfault(self):
        # issue #219
        script = f"""import psycopg2
conn = psycopg2.connect({dsn!r})
curs = conn.cursor()
curs.execute("create table copy_segf (id int)")
try:
    curs.execute("copy copy_segf to stdout")
except psycopg2.ProgrammingError:
    pass
conn.close()
"""

        proc = Popen([sys.executable, '-c', script], stdout=PIPE)
        proc.communicate()
        self.assertEqual(0, proc.returncode)

    def test_copy_from_propagate_error(self):
        class BrokenRead(TextIOBase):
            def read(self, size):
                return 1 / 0

            def readline(self):
                return 1 / 0

        curs = self.conn.cursor()
        # It seems we cannot do this, but now at least we propagate the error
        # self.assertRaises(ZeroDivisionError,
        #     curs.copy_from, BrokenRead(), "tcopy")
        try:
            curs.copy_from(BrokenRead(), "tcopy")
        except Exception as e:
            self.assert_('ZeroDivisionError' in str(e))

    def test_copy_to_propagate_error(self):
        class BrokenWrite(TextIOBase):
            def write(self, data):
                return 1 / 0

        curs = self.conn.cursor()
        curs.execute("insert into tcopy values (10, 'hi')")
        self.assertRaises(ZeroDivisionError,
            curs.copy_to, BrokenWrite(), "tcopy")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == "__main__":
    unittest.main()
