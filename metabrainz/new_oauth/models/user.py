from mbdata.models import Editor


class User(Editor):
    def get_user_id(self):
        return self.id
