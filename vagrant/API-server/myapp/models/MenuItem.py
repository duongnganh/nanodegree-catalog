from myapp.models import *
from myapp.models.User import *
from myapp.models.Restaurant import *


class MenuItem(Base):
    __tablename__ = 'menu_item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    price = Column(String(8))
    course = Column(String(250))
    created_date = Column(DateTime, default=datetime.datetime.now())
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
    restaurant = relationship(Restaurant)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'price': self.price,
            'course': self.course,
            'created_date': self.created_date,
            'restaurant_id': self.restaurant_id,
            'user_id': self.user_id
        }
