# TextMe v3
SIM number = ID, chat via WiFi/Data.

Deploy on Render:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --worker-class gevent -w 1 app_v3:app`
- Environment Variable: `SEMAPHORE_API_KEY`

Local:
