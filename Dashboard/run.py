# yoyoyo
from myapp import app, socketio
# app.run(host='0.0.0.0', port=12344, debug=True, ssl_context = sSLContext, use_reloader=False)

# app.run(host='0.0.0.0')
socketio.run(app, host='0.0.0.0')
