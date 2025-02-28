#!/usr/bin/python3
from wsgiref.handlers import CGIHandler
import sys
import os

# FlaskアプリケーションのパスをPYTHONPATHに追加
sys.path.insert(0, os.path.dirname(__file__))

from app import app

if __name__ == '__main__':
    CGIHandler().run(app)
