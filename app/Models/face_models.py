# -*- coding: utf-8 -*-
from . import *
from facepp import API, APIError, File
from ..main.errors import *
import os

api = API(key='1d1ae053ef9d53ce1cd319fbfd25d069', secret='38hnSxLJDZQCflH84VmOvexSvM87sd29')


class Face(Document):
    student_id = StringField(primary_key=True)
    faces = DictField()
    person_id = StringField()
    last_session = StringField()

    def create_person(self):
        person = api.person.create(person_name=self.student_id)
        person_id = person['person_id']
        self.update(person_id=person_id)

    def get_face_ids(self):
        face_ids = []
        try:
            faces = api.person.get_info(person_id=self.person_id)['face']
            for face in faces:
                face_ids.append(face['face_id'])
            return face_ids
        except APIError, e:
            if e.error_code == 1005:
                self.update(faces={})
                return []
            else:
                return Error.FACE_API_ERROR

    def add_face(self, img_path, retry_count=0):
        img_path = str(img_path)
        if retry_count >= 2:
            return Error.FACE_API_ERROR
        try:
            result = api.detection.detect(img=File(img_path))
            print result
            face_id = result['face'][0]['face_id']

            api.person.add_face(face_id=face_id, person_name=self.student_id)
            self.update(**{'faces__' + face_id: img_path})
            self.train_verify()
            return face_id
        except APIError, e:
            if e.error_code == 1005:
                try:
                    self.create_person()
                except APIError, e:
                    return Error.FACE_API_ERROR
                return self.add_face(img_path, retry_count=retry_count + 1)
            elif e.error_code == 1402:
                return
            print e
            return Error.FACE_API_ERROR
        except IndexError:
            return Error.IMAGE_CONTAINS_NO_FACE

    def delete_face(self, face_id):
        if face_id not in self.faces:
            return
        try:
            success = api.person.remove_face(person_id=self.person_id, face_id=face_id)['success']
            if success:
                path = self.faces[face_id]
                try:
                    os.remove(path)
                except Exception, e:
                    print e.message
                del self.faces[face_id]
            self.save()
        except APIError:
            return Error.FACE_API_ERROR

    def train_verify(self):
        if self.student_id == "":
            return
        try:
            session_id = api.train.verify(person_name=self.student_id)['session_id']
            self.update(last_session=session_id)
        except APIError, e:
            print e
            return Error.FACE_API_ERROR

    def recognize_verify(self, img_path):
        img_path = str(img_path)
        if not self.check_if_session_finished():
            return Error.FACE_TRAINING_NOT_DONE
        img = File(img_path)
        if self.student_id == "":
            return
        try:
            face_id = api.detection.detect(img=img)['face'][0]['face_id']
            return api.recognition.verify(face_id=face_id, person_name=self.student_id)['is_same_person']
        except APIError, e:
            print e.message
            return Error.FACE_API_ERROR
        except IndexError:
            return Error.IMAGE_CONTAINS_NO_FACE

    def delete_person(self):
        if self.person_id is None or self.person_id == "":
            return
        try:
            api.person.delete(person_id=self.person_id)
            self.update(person_id="")
        except APIError, e:
            print e
            return Error.FACE_API_ERROR

    def check_if_session_finished(self):
        if self.last_session == "" or self.last_session is None:
            return True
        try:
            result = api.info.get_session(session_id=self.last_session)
            if result.get('status') == 'SUCC':
                self.update(last_session="")
                return True
            else:
                return False
        except APIError, e:
            print e
            return Error.FACE_API_ERROR
