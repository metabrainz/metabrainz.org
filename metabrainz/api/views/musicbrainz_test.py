from metabrainz.testing import FlaskTestCase
from metabrainz.api.views.musicbrainz import DAILY_SUBDIR, WEEKLY_SUBDIR
from metabrainz.model.token import Token
from flask import url_for, current_app
import tempfile
import shutil
import os


class MusicBrainzViewsTestCase(FlaskTestCase):

    def setUp(self):
        super(MusicBrainzViewsTestCase, self).setUp()
        current_app.config['REPLICATION_PACKETS_DIR'] = self.path = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.path, DAILY_SUBDIR))
        os.mkdir(os.path.join(self.path, WEEKLY_SUBDIR))
        self.token = Token.generate_token(owner_id=None)

    def tearDown(self):
        super(MusicBrainzViewsTestCase, self).tearDown()
        shutil.rmtree(self.path)

    def test_replication_info(self):
        self.assert400(self.client.get(url_for('api_musicbrainz.replication_info')))
        self.assert403(self.client.get(url_for('api_musicbrainz.replication_info', token='fake')))

        resp = self.client.get(url_for('api_musicbrainz.replication_info', token=self.token))
        self.assert200(resp)
        self.assertEquals(resp.json, {
            'last_packet': None,
            'last_packet_daily': None,
            'last_packet_weekly': None,
        })

        open(os.path.join(self.path, 'replication-1.tar.bz2'), 'a').close()
        open(os.path.join(self.path, DAILY_SUBDIR, 'replication-daily-1.tar.bz2'), 'a').close()
        open(os.path.join(self.path, WEEKLY_SUBDIR, 'replication-weekly-1.tar.bz2'), 'a').close()
        resp = self.client.get(url_for('api_musicbrainz.replication_info', token=self.token))
        self.assert200(resp)
        self.assertEquals(resp.json, {
            'last_packet': 'replication-1.tar.bz2',
            'last_packet_daily': 'replication-daily-1.tar.bz2',
            'last_packet_weekly': 'replication-weekly-1.tar.bz2',
        })

    def test_replication_check(self):
        resp = self.client.get('/api/musicbrainz/replication-check')
        self.assert200(resp)
        self.assertEquals(resp.data, "UNKNOWN no replication packets available")

        open(os.path.join(self.path, 'replication-1.tar.bz2'), 'a').close()
        resp = self.client.get('/api/musicbrainz/replication-check')
        self.assert200(resp)
        self.assertEquals(resp.data, "OK")

        open(os.path.join(self.path, 'replication-3.tar.bz2'), 'a').close()
        resp = self.client.get('/api/musicbrainz/replication-check')
        self.assert200(resp)
        self.assertEquals(resp.data, "CRITICAL Replication packet 2 is missing")

        open(os.path.join(self.path, 'replication-2.tar.bz2'), 'a').close()
        os.utime(os.path.join(self.path, 'replication-3.tar.bz2'), (0, 0))
        resp = self.client.get('/api/musicbrainz/replication-check')
        self.assert200(resp)
        self.assertTrue(str(resp.data).startswith("CRITICAL"))

    def test_replication_hourly(self):
        self.assert400(self.client.get(url_for('api_musicbrainz.replication_hourly', packet_number=1)))
        self.assert403(self.client.get(url_for('api_musicbrainz.replication_hourly', packet_number=1, token='fake')))
        self.assert404(self.client.get(url_for('api_musicbrainz.replication_hourly', packet_number=1, token=self.token)))

        open(os.path.join(self.path, 'replication-1.tar.bz2'), 'a').close()
        self.assert200(self.client.get(url_for('api_musicbrainz.replication_hourly', packet_number=1, token=self.token)))

    def test_replication_hourly_signature(self):
        self.assert400(self.client.get(url_for('api_musicbrainz.replication_hourly_signature', packet_number=1)))
        self.assert403(self.client.get(url_for('api_musicbrainz.replication_hourly_signature', packet_number=1, token='fake')))
        self.assert404(self.client.get(url_for('api_musicbrainz.replication_hourly_signature', packet_number=1, token=self.token)))

        open(os.path.join(self.path, 'replication-1.tar.bz2.asc'), 'a').close()
        self.assert200(self.client.get(url_for('api_musicbrainz.replication_hourly_signature', packet_number=1, token=self.token)))

    def test_replication_daily(self):
        self.assert400(self.client.get(url_for('api_musicbrainz.replication_daily', packet_number=1)))
        self.assert403(self.client.get(url_for('api_musicbrainz.replication_daily', packet_number=1, token='fake')))
        self.assert404(self.client.get(url_for('api_musicbrainz.replication_daily', packet_number=1, token=self.token)))

        open(os.path.join(self.path, DAILY_SUBDIR, 'replication-daily-1.tar.bz2'), 'a').close()
        self.assert200(self.client.get(url_for('api_musicbrainz.replication_daily', packet_number=1, token=self.token)))

    def test_replication_daily_signature(self):
        self.assert400(self.client.get(url_for('api_musicbrainz.replication_daily_signature', packet_number=1)))
        self.assert403(self.client.get(url_for('api_musicbrainz.replication_daily_signature', packet_number=1, token='fake')))
        self.assert404(self.client.get(url_for('api_musicbrainz.replication_daily_signature', packet_number=1, token=self.token)))

        open(os.path.join(self.path, DAILY_SUBDIR, 'replication-daily-1.tar.bz2.asc'), 'a').close()
        self.assert200(self.client.get(url_for('api_musicbrainz.replication_daily_signature', packet_number=1, token=self.token)))

    def test_replication_weekly(self):
        self.assert400(self.client.get(url_for('api_musicbrainz.replication_weekly', packet_number=1)))
        self.assert403(self.client.get(url_for('api_musicbrainz.replication_weekly', packet_number=1, token='fake')))
        self.assert404(self.client.get(url_for('api_musicbrainz.replication_weekly', packet_number=1, token=self.token)))

        open(os.path.join(self.path, WEEKLY_SUBDIR, 'replication-weekly-1.tar.bz2'), 'a').close()
        self.assert200(self.client.get(url_for('api_musicbrainz.replication_weekly', packet_number=1, token=self.token)))

    def test_replication_weekly_signature(self):
        self.assert400(self.client.get(url_for('api_musicbrainz.replication_weekly_signature', packet_number=1)))
        self.assert403(self.client.get(url_for('api_musicbrainz.replication_weekly_signature', packet_number=1, token='fake')))
        self.assert404(self.client.get(url_for('api_musicbrainz.replication_weekly_signature', packet_number=1, token=self.token)))

        open(os.path.join(self.path, WEEKLY_SUBDIR, 'replication-weekly-1.tar.bz2.asc'), 'a').close()
        self.assert200(self.client.get(url_for('api_musicbrainz.replication_weekly_signature', packet_number=1, token=self.token)))
