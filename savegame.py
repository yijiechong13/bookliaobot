import os 
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_init import db

load_dotenv() 

FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

class GameDatabase:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
    
    def save_game(self, game_data):
        game_data["created_at"]= firestore.SERVER_TIMESTAMP 
        game_ref = self.db.collection("game").document()
        game_ref.set(game_data)
        return game_ref.id
    
    def update_game(self, game_id, update_data):
        game_ref = self.db.collection("game").document(game_id)
        game_ref.update(update_data)
