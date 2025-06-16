import os 
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore


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

    def get_hosted_games(self, host_id):
        games_ref = self.db.collection("game")
        query = games_ref.where("host", "==", host_id).where("status", "==", "open")
        results = query.stream()
        return [{"id": game.id, **game.to_dict()} for game in results] 
    
    def cancel_game(self, game_id): 
        
        try:
            game_ref = self.db.collection("game").document(game_id)
            game_doc = game_ref.get()
            
            if game_doc.exists:
                game_data = game_doc.to_dict()
                announcement_msg_id = game_data.get("announcement_msg_id")
                
                # Update the game status to cancelled
                game_ref.update({"status": "cancelled"})
                
                return announcement_msg_id
            return None
        except Exception as e:
            print(f"Error cancelling game: {e}")
            return None
