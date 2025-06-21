from datetime import datetime, timedelta
import pytz
from telegram.ext import ContextTypes
from firebase_admin import firestore

class ReminderService: 
    def __init__(self,db):
        self.db = db 
        self.sg_tz = pytz.timezone("Asia/Singapore")

    async def send_game_reminders(self, context = ContextTypes.DEFAULT_TYPE): 
        try:
            now = datetime.now(self.sg_tz)

            #Get all open games 
            games_ref = self.db.db.collection("game")
            query = games_ref.where("status", "==", "open")
            results = query.stream()

            reminder_count = 0 

            for game_doc in results: 
                game_data = game_doc.to_dict()
                game_id = game_doc.id

                game_datetime = await self.game_start_datetime(game_data)
                
                #Calculate time difference 
                time_until_game = game_datetime - now 

                #Check if need send reminders
                if await self._should_send_24h_reminder(game_data, time_until_game, game_id):
                    await self.send_24h_reminder(context, game_data, game_id)
                    reminder_count += 1

            if reminder_count > 0:
                print(f"✅ Sent {reminder_count} game reminders")
            else:
                print("No reminders needed at this time")
                
        except Exception as e:
            print(f"Error in send_game_reminders: {e}")


    async def game_start_datetime(self, game_data):  

        try:

            date_str = game_data.get("date")
            start_time_24 = game_data.get("start_time_24")

            day, month, year = map(int, date_str.split("/"))

            end_hour, end_min = map(int, start_time_24.split(":"))

            game_datetime= datetime(year, month, day, end_hour, end_min)

            game_datetime = self.sg_tz.localize(game_datetime)

            return game_datetime
        
        except Exception as e: 
            print(f"Error parsing game datetime: {e}")
            return None

    async def _should_send_24h_reminder(self, game_data, time_until_game, game_id):
        
        try:
            # Check if we're within 24-25 hours before the game
            if timedelta(hours=23) <= time_until_game <= timedelta(hours=26):
                # Check if reminder hasn't been sent yet
                reminder_sent = game_data.get('reminder_24h_sent', False)
                return not reminder_sent
            return False
        except Exception:
            return False
        
    async def send_24h_reminder(self, context: ContextTypes.DEFAULT_TYPE, game_data, game_id):
        try:
            
            group_id = game_data.get('group_id')
            if not group_id:
                print("❌ No group_id in game data")
                return

            try:
                chat_id = f"-100{abs(int(group_id))}"
            except (ValueError, TypeError) as e:
                print(f"❌ Invalid group_id format: {group_id} - {e}")
                return


            # First verify bot has access
            try:
                chat = await context.bot.get_chat(chat_id)
                print(f"✅ Chat verified: {chat.title} (ID: {chat.id})")
                
                # Additional check - get chat member status
                try:
                    me = await context.bot.get_me()
                    member = await context.bot.get_chat_member(chat_id, me.id)
                    print(f"🤖 Bot status in group: {member.status}")
                    if member.status not in ['administrator', 'member']:
                        print("❌ Bot doesn't have send permissions")
                        return
                except Exception as e:
                    print(f"❌ Couldn't verify bot membership: {e}")
                    return
                    
            except Exception as e:
                print(f"❌ Failed to access chat: {e}")
                
                # Special handling for different error types
                if "Chat not found" in str(e):
                    print("💡 Solution: The group might be deleted or bot was removed")
                elif "not enough rights" in str(e).lower():
                    print("💡 Solution: Bot needs admin privileges in the group")
                return
            
            # Create reminder message
            reminder_text = (
                f"⏰ **24-Hour Game Reminder!** ⏰\n\n"
                f"🏀 **{game_data['sport']}** game is **tomorrow**!\n\n"
                f"📅 **Date:** {game_data['date']}\n"
                f"🕒 **Time:** {game_data['time_display']}\n"
                f"📍 **Venue:** {game_data['venue']}\n"
                f"📊 **Skill Level:** {game_data['skill'].title()}\n\n"
                f"See you tomorrow! 🎉"
            )
            
            # Send message to group
            await context.bot.send_message(
                chat_id=chat_id,  
                text=reminder_text,
                parse_mode='Markdown'
            )

            # Mark reminder as sent in database
            self.db.update_game(game_id, {"reminder_24h_sent": True})
            print(f"✅ Sent reminder for game {game_id} to group {chat_id}")
        
        except Exception as e:
            print(f"🚨 Unexpected error sending 24h reminder: {e}")