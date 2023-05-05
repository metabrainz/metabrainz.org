from enum import Enum

from sqlalchemy.dialects.postgresql import ENUM

from metabrainz.model import db
from metabrainz.admin import AdminModelView


class DatasetType(Enum):
    MUSICBRAINZ = 'musicbrainz'
    LISTENBRAINZ = 'listenbrainz'
    CRITIQUEBRAINZ = 'critiquebrainz'


class Dataset(db.Model):
    """ This model defines the various types of datasets MetaBrainz publishes. """
    __tablename__ = 'dataset'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    project = db.Column(ENUM('musicbrainz', 'listenbrainz', name='dataset_project_type'), nullable=False)

    def __str__(self):
        return self.name

    @classmethod
    def create(cls, **kwargs):
        new_dataset = cls(
            name=kwargs.pop('name'),
            description=kwargs.pop('description', None),
            project=kwargs.pop('project')
        )
        db.session.add(new_dataset)
        db.session.commit()
        return new_dataset

    @classmethod
    def get(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first()


class DatasetAdminView(AdminModelView):
    column_labels = dict(
        id='ID',
        name='Name',
        description='Description',
        project='Project',
    )
    column_list = ('id', 'name', 'description', 'project')
    form_columns = ('name', 'description', 'project')

    def __init__(self, session, **kwargs):
        super(DatasetAdminView, self).__init__(Dataset, session, name='Datasets', **kwargs)
