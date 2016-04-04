# -*- coding: utf-8 -*-
import sys
import app

reload(sys)
sys.setdefaultencoding('utf-8')

app = app.create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
