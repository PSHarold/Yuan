# -*- coding: utf-8 -*-
from app.main.errors import *
from app.Models.user_models import *
from app.Models.gerenal_models import *
from app.Models.course_models import *
from flask import g, request, abort, make_response, jsonify, Response
from functools import wraps
from mongoengine import ReferenceField, Q
from mongoengine.errors import ValidationError, DoesNotExist, NotUniqueError
from itsdangerous import TimedJSONWebSignatureSerializer, BadSignature, SignatureExpired
from app.Models import no_dereference_id_only_list

PER_PAGE = 5


# 获取POST参数中的课程编号和讲台编号,获取课程并返回,找不到则404
def get_course_pre():
    course_id = get_arg_or_error('course_id')
    return get_by_id_or_error(SubCourse, course_id, error=Error.SUB_COURSE_NOT_FOUND)


def get_arg_or_error(arg_name, allow_none=False):
    if arg_name in request.args:
        return request.args.get(arg_name)
    elif allow_none:
        return
    else:
        handle_error(Error.ARGUMENT_MISSING, arg_name=arg_name)


def get_user_pre():
    if hasattr(g, 'user'):
        return
    token = get_arg_or_error('token')
    credential = User.decrypt_token(token)
    if isinstance(credential, Error):
        handle_error(credential)
    user = get_user_with_role(credential['role'], credential['user_id'])
    if isinstance(user, Error):
        handle_error(user)
    g.user = user


def require_token(func):
    @wraps(func)
    def require_func(*args, **kwargs):
        get_user_pre()
        return func(*args, **kwargs)

    return require_func


def get_json():
    json = request.get_json()
    if not json:
        abort(406)

    def get_field(field, allow_none=False):
        value = json.get(field)
        if value is None and not allow_none:
            handle_error(Error.FIELD_MISSING, field=field)
        return value

    return get_field


def instantiate_from_request_or_422(cls, *exceptions, **extra_attrs):
    get = get_json()
    instance = cls()
    fields = dict(cls._fields)

    def get_and_field(field):
        attr = getattr(cls, field)
        if (field not in exceptions) and (field not in extra_attrs) and (
                    attr.required and not attr.primary_key) and (attr.default is None):
            value = get(field)
            setattr(instance, field, value)

    def set_field((key, value)):
        setattr(instance, key, value)

    map(get_and_field, fields)
    map(set_field, extra_attrs.items())
    return instance


def require_is_teacher(func):
    @wraps(func)
    def require(*args, **kwargs):
        get_user_pre()
        if not g.user.role == 1:
            abort(403)
        return func(*args, **kwargs)

    return require


def require_is_student(func):
    @wraps(func)
    def require(*args, **kwargs):
        get_user_pre()
        if not g.user.role == 2:
            abort(403)
        return func(*args, **kwargs)

    return require


def require_having_course(func):
    @wraps(func)
    def require(*args, **kwargs):
        get_user_pre()
        course = get_course_pre()
        g.course = course
        if g.user.role == 1:
            if g.user.user_id not in course.teachers:
                handle_error(Error.YOU_DO_NOT_HAVE_THIS_COURSE)
        elif g.user.role == 2:
            if g.user.user_id not in course.students:
                handle_error(Error.YOU_DO_NOT_HAVE_THIS_COURSE)
        return func(*args, **kwargs)

    return require


def get_by_id_or_error(cls, o_id, error=None):
    try:
        return cls.objects.get(pk=o_id)
    except (DoesNotExist, ValidationError):
        if error is None:
            handle_error(Error.RESOURCE_NOT_FOUND)
        handle_error(error)


# OK的Response,接受键值对作为附加信息
def success_response(*args, **kwargs):
    msg = {'msg': 'Success'}
    for arg in args:
        msg.update(arg)
    for key in kwargs:
        msg[key] = kwargs[key]

    return make_response(jsonify(msg), 200)
