
from datetime import datetime, timedelta
import pytz
from telegram.ext import ContextTypes
from firebase_admin import firestore

class ReminderService: 
    def __init__(self, db):
        self.db = db 
        self.sg_tz = pytz.timezone("Asia/Singapore")

    async def schedule_game_reminders(self, context: ContextTypes.DEFAULT_TYPE, game_data, game_id): 
        try:
            game_datetime = await self.game_start_datetime(game_data)
            if not game_datetime:
                print(f"❌ Could not parse game datetime for game {game_id}")
                return

            now = datetime.now(self.sg_tz)
            
            # Calculate exact reminder times
            reminder_24h_time = game_datetime - timedelta(hours=24)
            reminder_2h_time = game_datetime - timedelta(hours=2)
            
            # Schedule 24-hour reminder if it's in the future
            if reminder_24h_time > now:
                job_name = f"reminder_24h_{game_id}"
                
                # Remove existing job if it exists
                current_jobs = context.job_queue.get_jobs_by_name(job_name)
                for job in current_jobs:
                    job.schedule_removal()
                
                context.job_queue.run_once(
                    callback=self.send_24h_reminder_job,
                    when=reminder_24h_time,
                    data={'game_id': game_id, 'game_data': game_data},
                    name=job_name
                )
                print(f"✅ Scheduled 24h reminder for game {game_id} at {reminder_24h_time}")
            else:
                print(f"⚠️ 24h reminder time has passed for game {game_id}")

            # Schedule 2-hour reminder if it's in the future
            if reminder_2h_time > now:
                job_name = f"reminder_2h_{game_id}"
                
                # Remove existing job if it exists
                current_jobs = context.job_queue.get_jobs_by_name(job_name)
                for job in current_jobs:
                    job.schedule_removal()
                
                context.job_queue.run_once(
                    callback=self.send_2h_reminder_job,
                    when=reminder_2h_time,
                    data={'game_id': game_id, 'game_data': game_data},
                    name=job_name
                )
                print(f"✅ Scheduled 2h reminder for game {game_id} at {reminder_2h_time}")
            else:
                print(f"⚠️ 2h reminder time has passed for game {game_id}")
                
        except Exception as e:
            print(f"❌ Error scheduling reminders for game {game_id}: {e}")

    async def send_24h_reminder_job(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            job_data = context.job.data
            game_id = job_data['game_id']
            game_data = job_data['game_data']
            
            # Get fresh game data to check if game is still active
            game_ref = self.db.db.collection("game").document(game_id)
            game_doc = game_ref.get()
            
            if not game_doc.exists:
                print(f"⚠️ Game {game_id} no longer exists")
                return
                
            current_game_data = game_doc.to_dict()
            
            # Check if game is still open and reminder hasn't been sent
            if current_game_data.get('status') != 'open':
                print(f"⚠️ Game {game_id} is no longer open")
                return
                
            if current_game_data.get('reminder_24h_sent', False):
                print(f"⚠️ 24h reminder already sent for game {game_id}")
                return
            
            await self.send_24h_reminder(context, current_game_data, game_id)
            
        except Exception as e:
            print(f"❌ Error in 24h reminder job: {e}")

    async def send_2h_reminder_job(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            job_data = context.job.data
            game_id = job_data['game_id']
            game_data = job_data['game_data']
            
            # Get fresh game data to check if game is still active
            game_ref = self.db.db.collection("game").document(game_id)
            game_doc = game_ref.get()
            
            if not game_doc.exists:
                print(f"⚠️ Game {game_id} no longer exists")
                return
                
            current_game_data = game_doc.to_dict()
            
            # Check if game is still open and reminder hasn't been sent
            if current_game_data.get('status') != 'open':
                print(f"⚠️ Game {game_id} is no longer open")
                return
                
            if current_game_data.get('reminder_2h_sent', False):
                print(f"⚠️ 2h reminder already sent for game {game_id}")
                return
            
            await self.send_2h_reminder(context, current_game_data, game_id)
            
        except Exception as e:
            print(f"❌ Error in 2h reminder job: {e}")

    async def schedule_all_existing_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            games_ref = self.db.db.collection("game")
            query = games_ref.where("status", "==", "open")
            results = query.stream()

            scheduled_count = 0
            
            for game_doc in results:
                game_data = game_doc.to_dict()
                game_id = game_doc.id
                
                # Only schedule if reminders haven't been sent yet
                if not game_data.get('reminder_24h_sent', False) or not game_data.get('reminder_2h_sent', False):
                    await self.schedule_game_reminders(context, game_data, game_id)
                    scheduled_count += 1
            
            if scheduled_count > 0:
                print(f"✅ Scheduled reminders for {scheduled_count} existing games")
            else:
                print("📋 No existing games need reminder scheduling")
                
        except Exception as e:
            print(f"❌ Error scheduling existing reminders: {e}")

    async def cancel_game_reminders(self, context: ContextTypes.DEFAULT_TYPE, game_id):
        try:
            # Cancel 24h reminder
            job_name_24h = f"reminder_24h_{game_id}"
            jobs_24h = context.job_queue.get_jobs_by_name(job_name_24h)
            for job in jobs_24h:
                job.schedule_removal()
            
            # Cancel 2h reminder
            job_name_2h = f"reminder_2h_{game_id}"
            jobs_2h = context.job_queue.get_jobs_by_name(job_name_2h)
            for job in jobs_2h:
                job.schedule_removal()
                
            if jobs_24h or jobs_2h:
                print(f"✅ Cancelled reminders for game {game_id}")
            
        except Exception as e:
            print(f"❌ Error cancelling reminders for game {game_id}: {e}")

    async def game_start_datetime(self, game_data):  
        try:
            date_str = game_data.get("date")
            start_time_24 = game_data.get("start_time_24")

            if not date_str or not start_time_24:
                print(f"❌ Missing date or start_time_24 in game data")
                return None

            day, month, year = map(int, date_str.split("/"))
            start_hour, start_min = map(int, start_time_24.split(":"))

            game_datetime = datetime(year, month, day, start_hour, start_min)
            game_datetime = self.sg_tz.localize(game_datetime)

            return game_datetime
        
        except Exception as e: 
            print(f"❌ Error parsing game datetime: {e}")
            return None

    async def send_24h_reminder(self, context: ContextTypes.DEFAULT_TYPE, game_data, game_id):
        try:
            group_id = game_data.get('group_id')
            if not group_id:
                print("❌ No group_id in game data")
                return

            try:
                # Supergroup starts with -100 
                chat_id = f"-100{abs(int(group_id))}"
            except (ValueError, TypeError) as e:
                print(f"❌ Invalid group_id format: {group_id} - {e}")
                return

            # Create reminder message
            reminder_text = (
                f"⏰ **24-Hour Game Reminder!** ⏰\n\n"
                f"**{game_data['sport']}** game is **tomorrow**!\n\n"
                f"📅 **Date:** {game_data['date']}\n"
                f"🕒 **Time:** {game_data['time_display']}\n"
                f"📍 **Venue:** {game_data['venue']}\n"
                f"📊 **Skill Level:** {game_data['skill'].title()}\n\n"
                f"See you tomorrow! 🎉"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,  
                text=reminder_text,
                parse_mode='Markdown'
            )

            # Send attendance poll 
            poll_question = f"Can you make it for tomorrow's {game_data['sport']} game?"
            poll_options = ["✅ Yes, I can make it!", "❌ No, I cannot make it"]

            poll_message = await context.bot.send_poll(
                chat_id=chat_id,
                question=poll_question,
                options=poll_options,
                is_anonymous=False,  # Show who voted for what
                allows_multiple_answers=False,  # Only one answer per person
                close_date=None  # Poll stays open indefinitely
            ) 

            # Pin the message 
            try: 
                await context.bot.pin_chat_message(
                    chat_id=chat_id,
                    message_id=poll_message.message_id,
                    disable_notification=True
                )
                print(f"✅ Poll pinned in group {chat_id}")

            except Exception as pin_error:
                print(f"⚠️ Could not pin poll: {pin_error}")

            # Mark reminder as sent in database
            self.db.update_game(game_id, {"reminder_24h_sent": True})
            print(f"✅ Sent 24h reminder for game {game_id} to group {chat_id}")
        
        except Exception as e:
            print(f"🚨 Unexpected error sending 24h reminder: {e}")

    async def send_2h_reminder(self, context: ContextTypes.DEFAULT_TYPE, game_data, game_id):
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

            reminder_text = (
                f"🚨 **2-Hour Game Alert!** 🚨\n\n"
                f"**{game_data['sport']}** game starts in **2 hours**!\n\n"
                f"📅 **Today:** {game_data['date']}\n"
                f"🕒 **Time:** {game_data['time_display']}\n"
                f"📍 **Venue:** {game_data['venue']}\n"
                f"📊 **Skill Level:** {game_data['skill'].title()}\n\n"
                f"Time to get ready! 🏃‍♂️💨"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,  
                text=reminder_text,
                parse_mode='Markdown'
            )

            # Mark reminder as sent in database
            self.db.update_game(game_id, {"reminder_2h_sent": True})
            print(f"✅ Sent 2h reminder for game {game_id} to group {chat_id}")
        
        except Exception as e:
            print(f"🚨 Unexpected error sending 2h reminder: {e}")

    # Legacy method for backward compatibility - now just calls the new scheduling method
    async def send_game_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        await self.schedule_all_existing_reminders(context)