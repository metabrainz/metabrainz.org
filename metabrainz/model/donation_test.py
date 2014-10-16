from metabrainz.model.testing import ModelTestCase
from donation import Donation
from metabrainz.model import db


class DonationModelTestCase(ModelTestCase):

    def test_addition(self):
        import logging

        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

        new = Donation()
        new.first_name = 'Tester'
        new.last_name = 'Testing'
        new.email = 'testing@testers.org'
        new.transaction_id = 'TEST'
        new.amount = 42.50
        db.session.add(new)
        db.session.commit()

        donations = Donation.query.all()
        self.assertEqual(len(donations), 1)
