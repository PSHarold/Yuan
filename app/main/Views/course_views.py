# -*- coding: utf-8 -*-
from . import *
from PIL import Image
import os

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


@main.route('/course/check_if_can_check_in')
@require_having_course
def my_test():
    course = g.course
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

    attendance_list = course.get_attendance_list(period=period, teach_day=today)
    if g.user.user_id in attendance_list.present_students:
        handle_error(Error.ALREADY_CHECKED_IN)
    return success_response(room_id=period.room_id, late_secs=remaining_or_past_secs)


@main.route('/course/check_in', methods=['POST'])
@require_having_course
def check_in():
    course = g.course
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

    faces = g.user.get_faces()
    if not faces:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    if not faces.check_if_session_finished():
        handle_error(Error.FACE_TRAINING_NOT_DONE)
    file = request.files.get('file')
    if file:
        img_path = AVATAR_FOLDER + g.user.user_id + "temp.jpg"
        file.save(img_path)
        img = Image.open(file)
        width, height = img.size
        max_length = max(width, height)
        if max_length > 600:
            ratio = max_length / 600
            height /= ratio
            width /= ratio
        img = img.resize((width, height), Image.ANTIALIAS)
        img.save(img_path, optimize=True, quality=95)
    else:
        handle_error(Error.BAD_IMAGE)
    r = faces.recognize_verify(img_path=img_path)
    os.remove(img_path)
    if isinstance(r, Error):
        handle_error(r)

    attendance_list = course.get_attendance_list(teach_day=today, period=period)
    r = attendance_list.check_in(g.user.user_id)
    if isinstance(r, Error):
        handle_error(r)
    return success_response()


@main.route('/course/ask_for_leave', methods=['POST'])
@require_is_student
@require_having_course
def ask_for_leave():
    get = get_json()
    period_no = get('period_no')
    week_no = get('week_no')
    day_no = get('day_no')
    if not (isinstance(period_no, int) and isinstance(week_no, int) and isinstance(day_no, int)):
        handle_error(Error.WRONG_FIELD_TYPE)
    if not g.course.is_on(week_no=week_no, day_no=day_no, period_no=period_no):
        handle_error(Error.COURSE_IS_NOT_ON_THE_GIVEN_TIME)

    attendance_list = g.course.get_attendance_list(period_no=period_no, day_no=day_no, week_no=week_no)
    for ask in attendance_list.asks:
        if ask.student_id == g.user.user_id:
            if ask.is_approved():
                handle_error(Error.ASK_FOR_LEAVE_HAS_BEEN_APPROVED)
            if ask.is_pending():
                handle_error(Error.ASK_FOR_LEAVE_STILL_PENDING)

    reason = get('reason')
    try:

        attendance_list = g.course.get_attendance_list(period_no=period_no, day_no=day_no, week_no=week_no)
        ask = AskForLeave(period_no=period_no, week_no=week_no, day_no=day_no, reason=reason,
                          student_id=g.user.user_id, course_id=g.course.course_id).save()
        g.user.update(add_to_set__pending_asks=str(ask.ask_id))
        g.course.update(add_to_set__pending_asks=ask)
        attendance_list.update(add_to_set__asks=ask, pull__absent_students=g.user.user_id,
                               add_to_set__asked_students=g.user.user_id)
    except Exception, e:
        print e.message
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    return success_response(ask_id=str(ask.ask_id), created_at=ask.created_at.strftime("%Y-%m-%d %H:%M:%S"))


@main.route('/course/delete_ask_for_leave')
@require_is_student
@require_having_course
def delete_ask_for_leave():
    ask_id = get_arg_or_error('ask_id')
    try:
        ask = AskForLeave.objects.get(pk=ask_id)
    except DoesNotExist:
        handle_error(Error.ASK_FOR_LEAVE_NOT_FOUND)
    if g.user.role == 2:
        if ask.student_id != g.user.user_id:
            handle_error(Error.FORBIDDEN)

    try:
        if ask.is_approved():
            handle_error(Error.ASK_FOR_LEAVE_HAS_BEEN_APPROVED)
        attendance_list = g.course.get_attendance_list(period_no=ask.period_no, day_no=ask.day_no, week_no=ask.week_no)
        if ask.is_pending():
            g.course.update(pull__pending_asks=ask)
            g.user.update(pull__pending_asks=ask)
            attendance_list.update(pull__asks=ask, add_to_set__absent_students=g.user.user_id,
                                   pull__asked_students=g.user.user_id)
        else:
            attendance_list.update(pull__asks=ask)
        ask.delete()
        ask.save()
    except Exception, e:
        print e.message
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    return success_response()


@main.route('/course/approve_ask_for_leave')
@require_is_teacher
@require_having_course
def approve_ask_for_leave():
    ask_id = get_arg_or_error('ask_id')
    try:
        ask = AskForLeave.objects.get(pk=ask_id)
    except DoesNotExist:
        handle_error(Error.ASK_FOR_LEAVE_NOT_FOUND)
    if ask.is_pending() or ask.is_disapproved():
        ask.modify({'status': AskForLeaveStatus.PENDING._value_}, status=AskForLeaveStatus.APPROVED._value_,
                   viewed_at=datetime.now())
        g.user.update(add_to_set__new_status_asks=ask, pull__pending_asks=ask)
        g.course.update(pull__pending_asks=ask)
        # attendance_list = g.course.get_attendance_list(period_no=ask.period_no, day_no=ask.day_no, week_no=ask.week_no)
        # attendance_list.update(pull__absent_students=ask.student_id)
    else:
        handle_error(Error.ASK_FOR_LEAVE_HAS_BEEN_APPROVED)
    return success_response(viewed_at=ask.viewed_at.strftime("%Y-%m-%d %H:%M:%S"))


@main.route('/course/disapprove_ask_for_leave')
@require_having_course
def disapprove_ask_for_leave():
    ask_id = get_arg_or_error('ask_id')
    try:
        ask = AskForLeave.objects.get(pk=ask_id)
    except DoesNotExist:
        handle_error(Error.ASK_FOR_LEAVE_NOT_FOUND)
    if ask.is_pending() or ask.is_approved():
        ask.modify({'status': AskForLeaveStatus.PENDING._value_}, status=AskForLeaveStatus.DISAPPROVED._value_,
                   viewed_at=datetime.now())
        g.user.update(add_to_set__new_status_asks=ask, pull__pending_asks=ask)
        g.course.update(pull__pending_asks=ask)
        attendance_list = g.course.get_attendance_list(period_no=ask.period_no, day_no=ask.day_no, week_no=ask.week_no)
        attendance_list.update(add_to_set__absent_students=ask.student_id, pull__asked_students=ask.student_id,
                               pull__asks=ask)
    else:
        handle_error(Error.ASK_FOR_LEAVE_HAS_BEEN_DISAPPROVED)
    return success_response(viewed_at=ask.viewed_at.strftime("%Y-%m-%d %H:%M:%S"))


@main.route('/course/get_attendance_list_auto')
@require_having_course
def get_attendance_list_auto():
    course = g.course
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

    attendance_list = course.get_attendance_list(teach_day=today, period=period)
    return success_response(students=attendance_list.to_dict(course))


@main.route('/course/get_attendance_list')
@require_having_course
def get_attendance_list():
    course = g.course
    period_no = get_arg_or_error('period_no')
    week_no = get_arg_or_error('week_no')
    day_no = get_arg_or_error('day_no')
    if not (isinstance(period_no, int) and isinstance(week_no, int) and isinstance(day_no, int)):
        handle_error(Error.WRONG_FIELD_TYPE)
    if not g.course.is_on(week_no=week_no, day_no=day_no, period_no=period_no):
        handle_error(Error.COURSE_IS_NOT_ON_THE_GIVEN_TIME)
    attendance_list = course.get_attendance_list(week_no=week_no, day_no=day_no, period_no=period_no)
    return success_response(students=attendance_list.to_dict(course))


@main.route('/course/my_asks_for_leave')
@require_having_course
def my_asks_for_leave():
    course = g.course
    pending_asks = map(lambda x: x.to_dict(), g.user.pending_asks)
    approved_asks = AskForLeave.objects(course_id=course.course_id, student_id=g.user.user_id,
                                        status=AskForLeaveStatus.APPROVED._value_)
    disapproved_asks = AskForLeave.objects(course_id=course.course_id, student_id=g.user.user_id,
                                           status=AskForLeaveStatus.DISAPPROVED._value_)

    approved_asks = map(lambda x: x.to_dict(), approved_asks)
    disapproved_asks = map(lambda x: x.to_dict(), disapproved_asks)

    return success_response(pending_asks=pending_asks, approved_asks=approved_asks, disapproved_asks=disapproved_asks)


@main.route('/course/viewed_asks_for_leave')
@require_having_course
def all_asks_for_leave():
    course = g.course
    all = AskForLeave.objects(course_id=course.course_id)
    approved_asks = []
    disapproved_asks = []
    for ask in all:
        if ask.is_approved():
            approved_asks.append(ask)
        elif ask.is_disapproved():
            disapproved_asks.append(ask)

    approved_asks = map(lambda x: x.to_dict(), approved_asks)
    disapproved_asks = map(lambda x: x.to_dict(), disapproved_asks)

    return success_response(approved_asks=approved_asks, disapproved_asks=disapproved_asks)


# @main.route('/course/pending_asks_for_leave')
# @require_having_course
# def all_asks_for_leave():
#     course = g.course
#     pending_asks = AskForLeave.objects(course_id=course.course_id, status=AskForLeaveStatus.PENDING._value_)
#     pending_asks = map(lambda x: x.to_dict(), pending_asks)
#     return success_response(pending_asks=pending_asks)


@main.route('/course/read_new_status_ask')
@require_token
def read_new_status_ask():
    # ask_id = get_arg_or_error('ask_id')
    # try:
    #     ask = AskForLeave.objects.get(pk=ask_id)
    # except DoesNotExist:
    #     handle_error(Error.ASK_FOR_LEAVE_NOT_FOUND)

    g.user.update(new_status_asks=[])
    return success_response()


@main.route('/course/get_student_attendance_in_period')
@require_having_course
def get_my_attendance_in_period():
    course = g.course
    try:
        period_no = int(get_arg_or_error('period_no'))
        week_no = int(get_arg_or_error('week_no'))
        day_no = int(get_arg_or_error('day_no'))
    except:
        handle_error(Error.WRONG_FIELD_TYPE)
    if g.user.role == 1:
        student_id = get_arg_or_error('student_id')
    else:
        student_id = g.user.user_id
    if not g.course.is_on(week_no=week_no, day_no=day_no, period_no=period_no):
        handle_error(Error.COURSE_IS_NOT_ON_THE_GIVEN_TIME)
    attendance_list = course.get_attendance_list(week_no=week_no, day_no=day_no, period_no=period_no)
    r = attendance_list.get_attendance_status(student_id=student_id)
    if isinstance(r, int):
        return success_response(status=r)
    else:
        return success_response(status=2, ask=r)


@main.route('/course/get_absence_list')
@require_having_course
def get_absence_list():
    course = g.course
    attendance_lists = AttendanceList.objects(course_id=course.course_id)
    today = TeachDay.get_now_teach_day()
    period = int(Period.get_current_period_num())
    absence = []
    for attendance_list in attendance_lists:
        if g.user.user_id in attendance_list.absent_students and attendance_list.week_no <= today.week:
            if (attendance_list.week_no == today.week and attendance_list.period_no <= period) or attendance_list.week_no < today.week:
                absence.append({'week_no': attendance_list.week_no, 'day_no': attendance_list.day_no,
                            'period_no': attendance_list.period_no})
    return success_response(absence=absence)
