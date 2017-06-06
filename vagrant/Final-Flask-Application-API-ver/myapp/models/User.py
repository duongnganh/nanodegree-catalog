from myapp.models import *

secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
                     for x in xrange(32))


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), index=True)
    picture = Column(String(250))
    password_hash = Column(String(64))

    # Use passlibs.apps.custom_app_context and SHA5 algorithm to hash passwords
    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    # Use itsdangerous lib to generate cryptographically signed messages
    # dump and load jsonObject
    def generate_auth_token(self, expiration=600):
        s = Serializer(secret_key, expires_in=expiration)
        return s.dumps({'id': self.id})

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'email': self.email,
            'picture': self.picture
        }

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            # Valid Token, but expired
            return None
        except BadSignature:
            # Invalid Token
            return None
        user_id = data['id']
        return user_id

    @staticmethod
    def validate(data):
        errors = []
        required_fields = ['name', 'password']
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
