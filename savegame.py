import os 
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from utils import is_game_expired
from telegram.ext import ContextTypes


load_dotenv() 

FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

class GameDatabase:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.firestore = firestore  # Add this for the FieldFilter
    
    def save_game(self, game_data):
        game_data["created_at"] = firestore.SERVER_TIMESTAMP 
        game_ref = self.db.collection("game").document()
        game_ref.set(game_data)
        return game_ref.id
    
    def update_game(self, game_id, update_data):
        try:
            game_ref = self.db.collection("game").document(game_id)
            game_ref.update(update_data)
            print(f"✅ Updated game {game_id}")
        except Exception as e:
            print(f"❌ Error updating game {game_id}: {e}")

    async def get_hosted_games(self, context, host_id):
        # Clean up expired games 
        await self.close_expired_games(context)

        games_ref = self.db.collection("game")
        # Use new filter syntax
        query = (games_ref
                .where(filter=firestore.FieldFilter("host", "==", host_id))
                .where(filter=firestore.FieldFilter("status", "==", "open")))
        results = query.stream()
        return [{"id": game.id, **game.to_dict()} for game in results] 

    async def get_all_open_games(self):
        """Get all open games for member count initialization"""
        try:
            games_ref = self.db.collection("game")
            query = games_ref.where(filter=firestore.FieldFilter("status", "==", "open"))
            results = query.stream()
            return [{"id": game.id, **game.to_dict()} for game in results]
        except Exception as e:
            print(f"❌ Error getting all open games: {e}")
            return []
    
    async def close_expired_games(self, context: ContextTypes.DEFAULT_TYPE): 
        try: 
            games_ref = self.db.collection("game")
            # Use new filter syntax
            query = games_ref.where(filter=firestore.FieldFilter("status", "==", "open"))
            results = query.stream()

            expired_count = 0
            processed_count = 0
            
            for game_doc in results:
                processed_count += 1
                game_data = game_doc.to_dict()
                game_id = game_doc.id
                
                # Validate game data before checking expiration
                if not self._validate_game_data(game_data, game_id):
                    continue
                
                if self.check_game_expired(game_data):
                    try:
                        game_doc.reference.update({
                            "status": "closed",
                            "closed_at": firestore.SERVER_TIMESTAMP,
                            "closure_reason": "expired"
                        })

                        # Update announcement if exists
                        announcement_msg_id = game_data.get("announcement_msg_id")
                        if announcement_msg_id and context:
                            await self._update_expired_announcement(context, game_data, announcement_msg_id)

                        expired_count += 1
                        print(f"🔒 Closed expired game: {game_data.get('sport', 'Unknown')} on {game_data.get('date', 'Unknown')}")
                    
                    except Exception as e:
                        print(f"❌ Error closing game {game_id}: {e}")
                        continue
            
            if processed_count > 0:
                print(f"📊 Processed {processed_count} games, closed {expired_count} expired games")
            
            return expired_count
            
        except Exception as e:
            print(f"❌ Error in close_expired_games: {e}")
            return 0

    def _validate_game_data(self, game_data, game_id):
        required_fields = ['date', 'end_time_24']
        
        for field in required_fields:
            if not game_data.get(field):
                print(f"⚠️ Game {game_id} missing required field for expiration check: {field}")
                return False
        
        return True

    async def _update_expired_announcement(self, context, game_data, announcement_msg_id):
        try:
            ANNOUNCEMENT_CHANNEL = os.getenv("ANNOUNCEMENT_CHANNEL")
            if not ANNOUNCEMENT_CHANNEL:
                print("⚠️ No announcement channel configured")
                return
                
            await context.bot.edit_message_text(
                chat_id=ANNOUNCEMENT_CHANNEL,
                message_id=announcement_msg_id,
                text=f"❌ EXPIRED: {game_data.get('sport', 'Unknown')} Game at {game_data.get('venue', 'Unknown')} on {game_data.get('time_display', 'Unknown')}",
                reply_markup=None  # Remove join button
            )
            print(f"✅ Updated expired announcement for message {announcement_msg_id}")
            
        except Exception as e:
            print(f"⚠️ Couldn't update announcement {announcement_msg_id}: {e}")

    def check_game_expired(self, game_data):
        try:
            date_str = game_data.get('date')
            end_time_24 = game_data.get('end_time_24')
            
            # Validate required fields
            if not date_str or not end_time_24:
                print(f"⚠️ Missing expiration data: date={date_str}, end_time={end_time_24}")
                return False
            
            return is_game_expired(date_str, end_time_24)
        
        except Exception as e:
            print(f"❌ Error checking game expiration: {e}")
            return False

    # To update status 
    # Returns announcement msg id    
    def cancel_game(self, game_id): 
        try:
            game_ref = self.db.collection("game").document(game_id)
            game_doc = game_ref.get()
            
            if game_doc.exists:
                game_data = game_doc.to_dict()
                announcement_msg_id = game_data.get("announcement_msg_id")
                
                # Update the game status to cancelled
                game_ref.update({
                    "status": "cancelled",
                    "cancelled_at": firestore.SERVER_TIMESTAMP
                })
                
                print(f"✅ Cancelled game {game_id}")
                return announcement_msg_id 
            else:
                print(f"⚠️ Game {game_id} not found")
                return None
            
        except Exception as e:
            print(f"❌ Error cancelling game {game_id}: {e}")
            return None
    
    def cleanup_invalid_games(self):
        try:
            games_ref = self.db.collection("game")
            results = games_ref.stream()
            
            cleanup_count = 0
            for game_doc in results:
                game_data = game_doc.to_dict()
                game_id = game_doc.id
                
                # Check if game is missing critical fields
                missing_fields = []
                critical_fields = ['date', 'sport', 'venue', 'skill']
                
                for field in critical_fields:
                    if not game_data.get(field):
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"🗑️ Found invalid game {game_id} missing: {missing_fields}")
                    
                    # Mark as invalid instead of deleting
                    game_doc.reference.update({
                        "status": "invalid",
                        "invalid_reason": f"Missing fields: {', '.join(missing_fields)}",
                        "marked_invalid_at": firestore.SERVER_TIMESTAMP
                    })
                    cleanup_count += 1
            
            if cleanup_count > 0:
                print(f"🧹 Marked {cleanup_count} invalid games")
            else:
                print("✅ No invalid games found")
                
            return cleanup_count
            
        except Exception as e:
            print(f"❌ Error in cleanup_invalid_games: {e}")
            return 0