from unittest import mock
from datetime import datetime,timezone

from metabrainz.testing import FlaskTestCase
from metabrainz.model.notification import NotificationProjectType
from metabrainz.notifications.views import DEFAULT_NOTIFICATION_FETCH_COUNT, MAX_ITEMS_PER_GET

class NotificationViewsTest(FlaskTestCase):
    
    @mock.patch('metabrainz.notifications.views.fetch_notifications', return_value=None)
    def test_get_notifications(self, mock_fetch):
        user_id = 1
        projects =  tuple(i.value for i in NotificationProjectType )
        until_ts = datetime.now(timezone.utc)
        # With no optional parameters.
        response = self.client.get(f'notification/{user_id}/fetch')
        self.assert200(response)
        mock_fetch.assert_called_with(
            user_id,
            projects,
            DEFAULT_NOTIFICATION_FETCH_COUNT,
            0,
            mock.ANY, # Unfortunately time flies away in between the call.
            False
        )
        # With all optional paramters.
        url = f'notification/{user_id}/fetch?project=listenbrainz,metabrainz&count=3&offset=1&until_ts={until_ts.timestamp()}&unread_only=t'
        response = self.client.get(url)
        self.assert200(response)
        mock_fetch.assert_called_with(
            user_id,
            ('listenbrainz','metabrainz'),
            3,
            1,
            until_ts,
            True
        )
        # Bad requests.
        bad_params=[('count',MAX_ITEMS_PER_GET+1), ('offset',-1),('until_ts','asdf'),('project','tidal,spotify'),
                    ('unread_only','true')]
        for param in bad_params:
            res = self.client.get(f'notification/{user_id}/fetch?{param[0]}={param[1]}')
            self.assert400(res)
    
    @mock.patch('metabrainz.notifications.views.mark_read_unread', return_value=None)
    def test_mark_notifications(self, mock_mark):
        user_id=1
        read=[1,2,3]
        unread=[4,5,6]
        # Both read and unread arrays.
        res = self.client.post(
            f'notification/{user_id}/mark-read',
            json={"read": read, "unread": unread}
            )
        self.assert200(res)
        mock_mark.assert_called_with(
            user_id,
            tuple(read),
            tuple(unread)
        )
        # Only read array.
        res = self.client.post(
            f'notification/{user_id}/mark-read',
            json={"read": read}
            )
        self.assert200(res)
        mock_mark.assert_called_with(
            user_id,
            tuple(read),
            tuple([])
        )
        # Bad requests.
        res = self.client.post(
            f'notification/{user_id}/mark-read',
            json={}
            )
        self.assert400(res)
        bad_data=[([],[]),(1,[2]),([4],['1st','b'])]
        for d in bad_data:
            res = self.client.post(
            f'notification/{user_id}/mark-read',
            json={"read": d[0], "unread":d[1]}
            )
            self.assert400(res)
        # Database error.
        mock_mark.side_effect= Exception()
        res = self.client.post(
            f'notification/{user_id}/mark-read',
            json={"read": read, "unread": unread}
            )
        self.assert503(res)
    
    @mock.patch('metabrainz.notifications.views.delete_notifications', return_value=None)
    def test_remove_notifications(self, mock_delete):
        user_id=1
        delete=[6,7,8]
        res = self.client.post(
            f'notification/{user_id}/delete',
            json=[i for i in delete]
        )
        self.assert200(res)
        mock_delete.assert_called_with(
            user_id,
            tuple(delete),
        )
        # Bad requests.
        bad_data = [1,['1'], []]
        for d in bad_data:
            res = self.client.post(
            f'notification/{user_id}/delete',
            json=d
            )
            self.assert400(res)


