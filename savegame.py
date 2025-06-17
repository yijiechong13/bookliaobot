import os 
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from utils import is_game_expired


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

        #clean up expired games 
        self.close_expired_games() 

        games_ref = self.db.collection("game")
        query = games_ref.where("host", "==", host_id).where("status", "==", "open")
        results = query.stream()
        return [{"id": game.id, **game.to_dict()} for game in results] 
    
    def close_expired_games(self): 
        try: 
            games_ref = self.db.collection("game")
            query = games_ref.where("status", "==", "open")
            results = query.stream()

            expired_count = 0
            for game_doc in results:
                game_data = game_doc.to_dict()
                
                if self._check_game_expired(game_data):
                    
                    game_doc.reference.update({
                        "status": "closed",
                        "closed_at": firestore.SERVER_TIMESTAMP
                    })
                    expired_count += 1
                    print(f"Closed expired game: {game_data.get('sport')} on {game_data.get('date')}")
            
            return expired_count
            
        except Exception as e:
            print(f"Error closing expired games: {e}")
            return 0
        
    def _check_game_expired(self, game_data):
        try:
            date_str = game_data.get('date')
            end_time_24 = game_data.get('end_time_24')
            
            return is_game_expired(date_str, end_time_24)
        
        except Exception as e:
            print(f"Error checking game expiration: {e}")
            return False
        
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
