# -*- coding: utf-8 -*-
from . import *
from ..main.errors import *
import flask
from itsdangerous import TimedJSONWebSignatureSerializer, BadSignature, SignatureExpired
import itsdangerous
from ..main.errors import Error, handle_error
from .face_models import *

AVATAR_FOLDER = "/Users/harold/"
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']


class StudentSetting(EmbeddedDocument):
    id_only_to_non_friend = BooleanField(required=True, default=True)


class User(Document):
    meta = {'allow_inheritance': True, 'abstract': True}
    token = ""
    user_id = StringField(primary_key=True)
    password = StringField(required=True)
    name = StringField(required=True)
    email = StringField()
    avatar = StringField()
    gender = BooleanField()
    role = IntField(required=True)
    tel = StringField()
    courses = ListField(ReferenceField('SubCourse'), reverse_delete_rule=4)

    def init_from_user(self, user):
        self.user_id = user.user_id
        self.password = user.password
        self.name = user.name
        self.email = user.email
        self.gender = user.gender
        self.role = user.role
        self.tel = user.tel
        return self

    def generate_token(self):
        s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=300000000)
        return s.dumps({'user_id': self.user_id, 'role': self.role})

    def to_dict_all(self):
        json_dict = dict()
        json_dict['user_id'] = self.user_id
        json_dict['name'] = self.name
        json_dict['email'] = self.email
        json_dict['gender'] = self.gender
        json_dict['role'] = self.role
        json_dict['tel'] = self.tel
        json_dict['courses'] = self.get_course_briefs_dict()
        return json_dict

    def to_dict_brief(self):
        json_dict = dict()
        json_dict['name'] = self.name
        json_dict['email'] = self.email
        json_dict['gender'] = self.gender
        json_dict['tel'] = self.tel
        return json_dict

    def get_course_briefs_dict(self):
        raise NotImplementedError

    @staticmethod
    def validate_fetched_user(user, password):
        if user:
            if user.password == password:
                return user
            else:
                return Error.WRONG_PASSWORD
        else:
            return Error.USER_NOT_FOUND

    @staticmethod
    def get_user_login(user_id, password):
        raise NotImplementedError

    @staticmethod
    def get_user_with_id(role, user_id):
        raise NotImplementedError

    @staticmethod
    def get_user_login(user_id, password):
        raise NotImplementedError

    @staticmethod
    def bad_token():
        pass

    @staticmethod
    def decrypt_token(token):
        try:
            s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=3600)
            credential = s.loads(token)
        except SignatureExpired:
            return Error.TOKEN_EXPIRED
        except BadSignature:
            return Error.BAD_TOKEN
        return credential

    def get_id(self):
        return self.user_id


class Teacher(User, Document):
    meta = {
        'collection': 'teacher',
    }

    title = StringField(required=True)
    office = StringField(required=True)

    def register_course(self, course):
        if not User.register_course(self, course):
            return False
        if self in course.teachers:
            return False
        return course.update(push__teachers=self)

    def to_dict_all(self):
        json = User.to_dict_all(self)
        json['office'] = self.office
        json['title'] = self.title

        return json

    def to_dict_brief(self):
        return {'teacher_id': self.user_id, 'name': self.name, 'gender': self.gender}

    def get_course_briefs_dict(self):
        return map(
            lambda x: {'course_name': x.name, 'course_id': x.course_id, 'sub_id': x.sub_id, 'classes': x.classes,
                       'times': x.get_times_and_rooms_dict()},
            self.courses)

    @staticmethod
    def get_user_with_id(user_id):
        return Teacher.objects(user_id=user_id).first()

    @staticmethod
    def get_user_login(user_id, password):
        user = Teacher.get_user_with_id(user_id)
        return Teacher.validate_fetched_user(user, password)


class Student(User, Document):
    meta = {
        'collection': 'student',
    }

    settings = EmbeddedDocumentField(StudentSetting)
    class_name = StringField(required=True)
    major_name = StringField(required=True)
    grade = IntField(required=True)
    faces = ReferenceField(Face)
    pending_asks = ListField(StringField())
    new_status_asks = ListField(StringField())

    def register_course(self, course):
        if not User.registerCourse(self, course):
            return False
        if self in course.students:
            return False
        return course.update(push__students=self)

    def to_dict_all(self):
        json = User.to_dict_all(self)
        json['class_name'] = self.class_name
        json['major_name'] = self.major_name
        json['courses'] = self.get_course_briefs_dict(on_login=True)
        json['new_status_asks'] = map(lambda x: x.to_dict(), self.new_status_asks)
        return json

    def to_dict_brief(self):
        json = {'role': 2, 'user_id': self.user_id, 'class_name': '', 'major_name': '', 'name': '',
                'gender': self.gender}
        if not self.settings.id_only_to_non_friend:
            json['name'] = self.name
            json['class_name'] = self.class_name
            json['major_name'] = self.major_name
        return json

    def to_dict_brief_for_teacher(self):
        return {'student_id': self.user_id, 'class_name': self.class_name, 'name': self.name,
                'gender': self.gender}

    def get_course_briefs_dict(self, on_login=False):
        return map(lambda x: x.to_dict_brief(), self.courses)

    def get_faces(self):
        try:
            faces = Face.objects.get(pk=self.user_id)
        except DoesNotExist:
            faces = Face(student_id=self.user_id)
            faces.save()
            self.update(faces=faces)
        return faces

    @staticmethod
    def get_user_with_id(user_id):
        return Student.objects(user_id=user_id).first()

    @staticmethod
    def get_user_login(user_id, password):
        user = Student.get_user_with_id(user_id)
        return Student.validate_fetched_user(user, password)


class Admin(User, Document):
    meta = {
        'collection': 'admin',
    }

    def to_dict_all(self):
        json = User.to_dict_all(self)
        return json

    @staticmethod
    def get_user_with_id(user_id):
        return Admin.objects(user_id=user_id).first()

    @staticmethod
    def get_user_login(user_id, password):
        user = Admin.get_user_with_id(user_id)
        return Admin.validate_fetched_user(user, password)


def get_user_with_role(role, user_id, password=None):
    user = None
    if password is None:
        if role == 0:
            user = Admin.get_user_with_id(user_id)
        if role == 1:
            user = Teacher.get_user_with_id(user_id)
        if role == 2:
            user = Student.get_user_with_id(user_id)
        if role == 3:
            user = Guest.get_user_with_id(user_id)
        if user is None:
            user = Error.USER_NOT_FOUND
    else:
        if role == 0:
            user = Admin.get_user_login(user_id, password)
        if role == 1:
            user = Teacher.get_user_login(user_id, password)
        if role == 2:
            user = Student.get_user_login(user_id, password)

    return user
