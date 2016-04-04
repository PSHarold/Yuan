from flask import Blueprint
main = Blueprint('main',__name__)
import errors
from Views import user_views, course_views
