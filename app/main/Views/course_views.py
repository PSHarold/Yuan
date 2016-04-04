# -*- coding: utf-8 -*-
from . import *

ALLOWED_IN_ADVANCE_SECONDS = 100000


def check_if_able_to_check_in(course, period):
    allow_late = course.settings.allow_late
    remaining_seconds_before_beginning = period.get_remaining_seconds_before_beginning()
    if remaining_seconds_before_beginning > ALLOWED_IN_ADVANCE_SECONDS:
        return -1, remaining_seconds_before_beginning - ALLOWED_IN_ADVANCE_SECONDS  # 还未开始
    elif remaining_seconds_before_beginning > 0:
        return 0, 0
    if remaining_seconds_before_beginning == -1:
        return Error.COURSE_ALREADY_OVER, 0
    if remaining_seconds_before_beginning == 0:
        past_seconds = period.get_past_seconds()
        if past_seconds > allow_late:
            return Error.YOU_ARE_TOO_LATE, past_seconds
        return 1, past_seconds


@main.route('/course/test')
@require_having_course
def my_test():
    course = g.sub_course
    today = TeachDay.get_now_teach_day()
    period = TeachDay.is_course_on_day_and_get_period(course, today)
    if not period:
        handle_error(Error.COURSE_IS_NOT_ON_TODAY)
    access_type, remaining_or_past_secs = check_if_able_to_check_in(course=course, period=period)
    if isinstance(access_type, Error):
        handle_error(access_type, late_secs=remaining_or_past_secs)
    if access_type == -1:
        handle_error(Error.CHECKING_IN_NOT_AVAILABLE,
                     remaining_secs=remaining_or_past_secs)

    # able to check in
    course.check_in(teach_day=today, period=period, student_id=g.user.user_id)
    return success_response(room_id=period.room_id, late_secs=remaining_or_past_secs)

@main.route('/course/getSubCourseDetails', methods=['POST'])
@require_token
def get_sub_course():
    course = get_course_pre()
    role = g.user.role
    return success_response(sub_course=course.to_dict_all(from_preview=True, for_teacher=False))