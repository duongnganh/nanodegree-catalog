from myapp.models import *
from myapp.models.User import *


class Restaurant(Base):
    __tablename__ = 'restaurant'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'user_id': self.user_id
        }

    @staticmethod
    def validate(data):
        errors = []
        required_fields = ['name']
        if type(data) != dict:
            error = dict({"Missing required parameters":
                         " ".format(', '.join(required_fields))})
            errors.append(error)
        else:
            for value in required_fields:
                if value not in data:
                    error = dict({value: "Required"})
                    errors.append(error)
                else:
                    if not data[value]:
                        error = dict({value: "Required"})
                        errors.append(error)
        return errors
