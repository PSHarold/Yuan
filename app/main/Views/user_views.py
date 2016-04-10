# -*- coding: utf-8 -*-
from . import *
from flask import send_file
import os
from PIL import Image


@main.route('/user/login', methods=['POST'])
def user_login(token_only=False):
    get = get_json()
    user_id = get('user_id')
    password = get('password')
    role = get('role')
    user = get_user_with_role(role, user_id, password)
    if isinstance(user, Error):
        handle_error(user)
    if token_only:
        return success_response(token=user.generate_token())
    json_dict = user.to_dict_all()

    return success_response(user=json_dict, token=user.generate_token())



@main.route('/user/get_face_img')
@require_token
def get_face():
    faces = g.user.get_faces()
    face_id = get_arg_or_error('face_id')
    img_path = faces.faces.get(face_id)
    if img_path:
        return send_file(img_path)
    else:
        abort(404)


@main.route('/user/get_faces')
@require_token
def get_face_ids():
    faces = g.user.get_faces()
    l = []
    for face_id in faces.faces.keys():
        l.append(face_id)
    return success_response(faces=l)


@main.route('/user/add_face', methods=['POST'])
@require_token
def add_face():
    faces = g.user.get_faces()
    if not faces:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    if not faces.check_if_session_finished():
        handle_error(Error.FACE_TRAINING_NOT_DONE)
    face_count = len(faces.faces)
    file = request.files.get('file')
    if file:
        img_path = AVATAR_FOLDER + g.user.user_id + str(face_count + 1) + ".jpg"
        file.save(img_path)
        img = Image.open(img_path)
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
    r = faces.add_face(img_path=img_path)
    if isinstance(r, Error):
        handle_error(r)
    return success_response(face_id=r)


@main.route('/user/test_face', methods=['POST'])
@require_token
def test_face():
    faces = g.user.get_faces()
    if not faces:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    if not faces.check_if_session_finished():
        handle_error(Error.FACE_TRAINING_NOT_DONE)
    face_count = len(faces.faces)
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
    return success_response(is_same_person=r)


@main.route('/user/delete_face')
@require_token
def delete_face():
    faces = g.user.get_faces()
    face_id = get_arg_or_error('face_id')
    r = faces.delete_face(face_id=face_id)
    if isinstance(r, Error):
        handle_error(r)
    return success_response()


@main.route('/user/delete_all_faces')
@require_token
def delete_all_faces():
    faces = g.user.get_faces()
    r = faces.delete_person()
    if isinstance(r, Error):
        handle_error(r)
    return success_response()
