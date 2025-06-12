from unittest import mock
from datetime import datetime,timezone
import requests_mock

from metabrainz.testing import FlaskTestCase
from metabrainz.model.notification import NotificationProjectType
from metabrainz.notifications.views import DEFAULT_NOTIFICATION_FETCH_COUNT, MAX_ITEMS_PER_GET

class NotificationViewsTest(FlaskTestCase):
    
    @requests_mock.Mocker()
    @mock.patch('metabrainz.notifications.views.fetch_notifications')
    def test_get_notifications(self, mock_requests, mock_fetch):
        user_id = 1
        projects =  tuple(i.value for i in NotificationProjectType )
        until_ts = datetime.now(timezone.utc)
        expected_value=[{'t_id':1}, {'t_id':2}]
        self.app.config["OAUTH2_WHITELISTED_CCG_CLIENTS"] = ['abc', 'def']
        mock_fetch.return_value=expected_value
        mock_requests.post(self.app.config["OAUTH_INTROSPECTION_URL"], json={
            "active": True,
            "client_id": "abc",
            "scope": ["notification"],
        })
        url = f'notification/{user_id}/fetch'

        # With no optional parameters.
        response = self.client.get(url, query_string={'token':'good_token'})
        self.assert200(response)
        mock_fetch.assert_called_with(
            user_id,
            projects,
            DEFAULT_NOTIFICATION_FETCH_COUNT,
            0,
            mock.ANY, # Unfortunately time flies away in between the call.
            False
        )
        self.assertListEqual(response.json, expected_value)
        # With all optional paramters.
        response = self.client.get(url, query_string={
            'token': 'good_token',
            'project': 'listenbrainz,metabrainz',
            'count': 3,
            'offset': 1,
            'until_ts': until_ts.timestamp(),
            'unread_only': 't'
        })
        self.assert200(response)
        mock_fetch.assert_called_with(
            user_id,
            ('listenbrainz','metabrainz'),
            3,
            1,
            until_ts,
            True
        )
        self.assertListEqual(response.json, expected_value)
        # Bad requests.
        bad_params=[('count',MAX_ITEMS_PER_GET+1,'Invalid count'), ('offset',-1,'Invalid offset'),
                    ('until_ts','asdf','Invalid Until_Timestamp'), ('project','tidal,spotify','Invalid project name'),
                    ('unread_only','true','Invalid unread_only option')]
        for param in bad_params:
            res = self.client.get(url, query_string={
                'token': 'good_token',
                param[0]:param[1]
            })
            self.assert400(res)
            self.assertEqual(res.json['error'],param[2])

    @requests_mock.Mocker()
    @mock.patch('metabrainz.notifications.views.mark_read_unread', return_value=None)
    def test_mark_notifications(self, mock_requests, mock_mark):
        user_id=1
        read=[1,2,3]
        unread=[4,5,6]
        mock_requests.post(self.app.config["OAUTH_INTROSPECTION_URL"], json={
            "active": True,
            "client_id": "abc",
            "scope": ["notification"],
        })
        url = f'notification/{user_id}/mark-read?token=good_token'
        # Both read and unread arrays.
        res = self.client.post(
            url,
            json={"read": read, "unread": unread}
            )
        self.assert200(res)
        mock_mark.assert_called_with(
            user_id,
            tuple(read),
            tuple(unread)
        )
        self.assertEqual(res.json['status'],'ok')
        # Only read array.
        res = self.client.post(
            url,
            json={"read": read}
            )
        self.assert200(res)
        mock_mark.assert_called_with(
            user_id,
            tuple(read),
            tuple([])
        )
        self.assertEqual(res.json['status'],'ok')
        # Bad requests.
        res = self.client.post(
            url,
            json={}
            )
        self.assert400(res)
        bad_data=[([],[],'Missing Read and Unread IDs'),
                  (1,[2],"'read' must be an Array" ),
                  ([4],['1st','b'],'Unread values must be Integers')
                ]
        for d in bad_data:
            res = self.client.post(
                url,
                json={"read": d[0], "unread":d[1]}
            )
            self.assert400(res)
            self.assertEqual(res.json['error'],d[2])
        # Database error.
        mock_mark.side_effect= Exception()
        res = self.client.post(
            url,
            json={"read": read, "unread": unread}
            )
        self.assert503(res)
        self.assertEqual(res.json['error'], 'Cannot update read values right now.')
    
    @requests_mock.Mocker()
    @mock.patch('metabrainz.notifications.views.delete_notifications', return_value=None)
    def test_remove_notifications(self, mock_requests, mock_delete):
        user_id=1
        delete=[6,7,8]
        mock_requests.post(self.app.config["OAUTH_INTROSPECTION_URL"], json={
            "active": True,
            "client_id": "abc",
            "scope": ["notification"],
        })
        url = f'notification/{user_id}/delete?token=good_token'
        res = self.client.post(
            url,
            json=[i for i in delete]
        )
        self.assert200(res)
        mock_delete.assert_called_with(
            user_id,
            tuple(delete),
        )
        self.assertEqual(res.json['status'],'ok')
        # Bad requests.
        bad_data = [(1,"ID's must be in an Array"),(['1'],'ID values must be Integers'),
                    ([],'Missing notification IDs for deletion')]
        for d in bad_data:
            res = self.client.post(
                url,
                json=d[0]
            )
            self.assert400(res)
            self.assertEqual(res.json['error'],d[1])
        # Database error.
        mock_delete.side_effect= Exception()
        res = self.client.post(
            url,
            json=[i for i in delete]
        )
        self.assert503(res)
        self.assertEqual(res.json['error'], 'Cannot delete notifications right now.')

    @requests_mock.Mocker()
    def test_invalid_tokens(self, mock_requests):
        endpoints = [
            {
                "url": "notification/1/fetch",
                "method": self.client.get
            },
            {
                "url": "notification/1/mark-read",
                "method": self.client.post,
                "data": {"json": {"read": [1,2]}}
            },
            {
                "url": "notification/1/delete",
                "method": self.client.post,
                "data": {"json": [1]}
            }
        ]
        for e in endpoints:
            url = e["url"]
            json = e.get("data")
            method = e["method"]
            introspect_url = self.app.config["OAUTH_INTROSPECTION_URL"]

            res = method(url, **(json or {}))
            self.assert400(res)
            self.assertEqual(res.json['error'], 'Missing access token.')

            mock_requests.post(introspect_url, json={"active": False})
            res = method(url+'?token=bad_token', **(json or {}))
            self.assert401(res)
            self.assertEqual(res.json['error'], 'Invalid or Expired access token.')

            mock_requests.post(introspect_url, json={"active": True, "scope": ["view", "profile"]})
            res = method(url+'?token=missing_scope_token', **(json or {}))
            self.assert403(res)
            self.assertEqual(res.json['error'], 'Missing notification scope.')

            mock_requests.post(introspect_url, json={"active": True, "scope": ["notification"], "client_id": "xyz"})
            res = method(url+'?token=invalid_clientid_token', **(json or {}))
            self.assert403(res)
            self.assertEqual(res.json['error'], 'Client is not an official MeB project.')