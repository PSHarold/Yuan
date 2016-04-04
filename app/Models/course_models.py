# -*- coding: utf-8 -*-
from . import *
import random
from ..main.errors import *
from .user_models import Student

TESTS_PER_PAGE = 6
NOTIFICATIONS_PER_PAGE = 10


class TimeAndRoom(EmbeddedDocument):
    room_name = StringField(required=True)
    room_id = StringField(required=True)
    days = ListField(IntField(), required=True)
    period = IntField(required=True)
    weeks = ListField(IntField(), required=True)

    def to_dict(self):
        return {'room_name': self.room_name, 'room_id': self.room_id, 'days': self.days, 'period':
            self.period, 'weeks': self.weeks}


class SubCourseSetting(EmbeddedDocument):
    allow_late = IntField()


class SubCourse(Document):
    name = StringField(required=True)
    combined_id = StringField(primary_key=True)
    course_id = StringField(required=True)
    sub_id = StringField(required=True)
    teachers = ListField(ReferenceField('Teacher'), required=True)
    students = ListField(ReferenceField('Student'), required=True)
    times = EmbeddedDocumentListField(TimeAndRoom)

    settings = EmbeddedDocumentField(SubCourseSetting, required=True, default=SubCourseSetting())
    classes = ListField(StringField())

    def to_dict_brief(self):
        teachers = []
        map(lambda x: teachers.append(x.name), self.teachers)
        return {'course_id': self.course_id, 'teachers': teachers, 'course_name': self.name,
                'times': self.get_times_and_rooms_dict()}

    def get_students_dict(self):
        return map(lambda x: x.to_dict_brief_for_teacher(), self.students)

    def get_teachers_dict(self):
        teachers = []
        map(lambda x: teachers.append(x.to_dict_brief()), self.teachers)
        return teachers

    def get_times_and_rooms_dict(self):
        times = []
        map(lambda x: times.append(x.to_dict()), self.times)
        return times

    def check_in(self, teach_day, period, student_id):
        try:
            AttendanceList.objects(combined_id=self.combined_id, week_no=teach_day.week, day_no=teach_day.day,
                                   period_no=period.num).update_one(upsert=True,
                                                                    add_to_set__present_students=student_id)
        except:
            pass

    def get_attendance_list(self, teach_day, period):
        pass


class AskForLeaveStatus(Enum):
    PENDING = 0
    APPROVED = 1
    DISAPPROVED = 2


class AskForLeave(EmbeddedDocument):
    student_id = StringField()
    reason = StringField()
    status = IntField()

    def get_status(self):
        if self.status is None:
            return None
        return AskForLeave(self.status)

    def set_status(self, status):
        self.status = status._value_


class AttendanceList(Document):
    present_students = ListField(StringField())
    absent_students = ListField(StringField())
    combined_id = StringField(primary_key=True)
    asks_for_leave = MapField(EmbeddedDocumentField(AskForLeave))
    week_no = IntField()
    day_no = IntField()
    period_no = IntField()
    processed = BooleanField(default=False)

    def process(self):
        pass
