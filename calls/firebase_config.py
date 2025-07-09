import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("soulmate/voicyuser-firebase-adminsdk-fbsvc-64693b6329.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
