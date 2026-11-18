# TextMe v3
SIM number = ID, chat via WiFi/Data.
Deploy: Render -> New Web Service -> Build: pip install -r requirements.txt | Start: gunicorn --worker-class eventlet -w 1 app_v3:app | Env: SEMAPHORE_API_KEY
Local: pip install flask flask-socketio requests ; python app_v3.py
