from datetime import timedelta
from telegram.ext import ContextTypes
from utils import DateTimeHelper, GroupIdHelper

class ReminderService: 
    def __init__(self, db):
        self.db = db 
        self.sg_tz = DateTimeHelper.get_singapore_timezone()

    async def schedule_game_reminders(self, context: ContextTypes.DEFAULT_TYPE, game_data, game_id): 
        try:
            game_datetime = self._get_game_start_datetime(game_data)
            if not game_datetime:
                print(f"❌ Could not parse game datetime for game {game_id}")
                return

            now = DateTimeHelper.get_current_singapore_time()
            
            # Calculate exact reminder times
            reminder_times = {
                '24h': game_datetime - timedelta(hours=24),
                '2h': game_datetime - timedelta(hours=2)
            }
            
            # Schedule reminders
            for period, reminder_time in reminder_times.items():
                await self._schedule_single_reminder(
                    context, game_id, game_data, period, reminder_time, now
                )
                
        except Exception as e:
            print(f"❌ Error scheduling reminders for game {game_id}: {e}")

    async def _schedule_single_reminder(self, context, game_id, game_data, period, reminder_time, now):
        if reminder_time > now:
            job_name = f"reminder_{period}_{game_id}"
            callback_method = getattr(self, f"send_{period}_reminder_job")
            
            # Remove existing job if it exists
            self._remove_existing_jobs(context, job_name)
            
            context.job_queue.run_once(
                callback=callback_method,
                when=reminder_time,
                data={'game_id': game_id, 'game_data': game_data},
                name=job_name
            )
            print(f"✅ Scheduled {period} reminder for game {game_id} at {reminder_time}")
        else:
            print(f"⚠️ {period} reminder time has passed for game {game_id}")

    def _remove_existing_jobs(self, context, job_name):
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()

    async def send_24h_reminder_job(self, context: ContextTypes.DEFAULT_TYPE):
        await self._send_reminder_job(context, '24h', self.send_24h_reminder)

    async def send_2h_reminder_job(self, context: ContextTypes.DEFAULT_TYPE):
        await self._send_reminder_job(context, '2h', self.send_2h_reminder)

    async def _send_reminder_job(self, context, period, reminder_method):
        try:
            job_data = context.job.data
            game_id = job_data['game_id']
            
            # Get fresh game data
            current_game_data = self._get_current_game_data(game_id)
            if not current_game_data:
                return
                
            # Check if reminder should be sent
            if not self._should_send_reminder(current_game_data, game_id, period):
                return
            
            await reminder_method(context, current_game_data, game_id)
            
        except Exception as e:
            print(f"❌ Error in {period} reminder job: {e}")

    def _get_current_game_data(self, game_id):
        try:
            game_ref = self.db.db.collection("game").document(game_id)
            game_doc = game_ref.get()
            
            if not game_doc.exists:
                print(f"⚠️ Game {game_id} no longer exists")
                return None
                
            return game_doc.to_dict()
        except Exception as e:
            print(f"❌ Error fetching game data for {game_id}: {e}")
            return None

    def _should_send_reminder(self, game_data, game_id, period):
        if game_data.get('status') != 'open':
            print(f"⚠️ Game {game_id} is no longer open")
            return False
            
        reminder_field = f'reminder_{period}_sent'
        if game_data.get(reminder_field, False):
            print(f"⚠️ {period} reminder already sent for game {game_id}")
            return False
            
        return True

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
                if self._needs_reminder_scheduling(game_data):
                    await self.schedule_game_reminders(context, game_data, game_id)
                    scheduled_count += 1
            
            self._log_scheduling_result(scheduled_count)
                
        except Exception as e:
            print(f"❌ Error scheduling existing reminders: {e}")

    def _needs_reminder_scheduling(self, game_data):
        return (not game_data.get('reminder_24h_sent', False) or 
                not game_data.get('reminder_2h_sent', False))

    def _log_scheduling_result(self, scheduled_count):
        if scheduled_count > 0:
            print(f"✅ Scheduled reminders for {scheduled_count} existing games")
        else:
            print("📋 No existing games need reminder scheduling")

    async def cancel_game_reminders(self, context: ContextTypes.DEFAULT_TYPE, game_id):
        try:
            reminder_periods = ['24h', '2h']
            jobs_cancelled = False
            
            for period in reminder_periods:
                job_name = f"reminder_{period}_{game_id}"
                jobs = context.job_queue.get_jobs_by_name(job_name)
                if jobs:
                    for job in jobs:
                        job.schedule_removal()
                    jobs_cancelled = True
                
            if jobs_cancelled:
                print(f"✅ Cancelled reminders for game {game_id}")
            
        except Exception as e:
            print(f"❌ Error cancelling reminders for game {game_id}: {e}")

    def _get_game_start_datetime(self, game_data):
        return DateTimeHelper.parse_game_datetime(
            game_data.get("date"), 
            game_data.get("start_time_24")
        )

    async def _send_reminder_message(self, context, game_data, game_id, reminder_config):
        try:
            chat_id = self._get_validated_chat_id(game_data)
            if not chat_id:
                return False

            # Send reminder text
            await context.bot.send_message(
                chat_id=chat_id,  
                text=reminder_config['text'],
                parse_mode='Markdown'
            )

            # Send poll if configured
            if reminder_config.get('send_poll', False):
                await self._send_attendance_poll(context, chat_id, game_data)

            # Mark reminder as sent
            self.db.update_game(game_id, {reminder_config['db_field']: True})
            print(f"✅ Sent {reminder_config['period']} reminder for game {game_id} to group {chat_id}")
            return True
        
        except Exception as e:
            print(f"🚨 Unexpected error sending {reminder_config['period']} reminder: {e}")
            return False

    def _get_validated_chat_id(self, game_data):
        group_id = game_data.get('group_id')
        if not group_id:
            print("❌ No group_id in game data")
            return None

        try:
            telegram_id = GroupIdHelper.to_telegram_format(group_id)
            chat_id = str(telegram_id)
            return chat_id
        except (ValueError, TypeError) as e:
            print(f"❌ Invalid group_id format: {group_id} - {e}")
            return None

    async def _send_attendance_poll(self, context, chat_id, game_data):
        poll_question = f"Can you make it for tomorrow's {game_data['sport']} game?"
        poll_options = ["✅ Yes, I can make it!", "❌ No, I cannot make it"]

        poll_message = await context.bot.send_poll(
            chat_id=chat_id,
            question=poll_question,
            options=poll_options,
            is_anonymous=False,
            allows_multiple_answers=False,
            close_date=None
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

    def _create_reminder_text(self, game_data, reminder_type):
        common_info = (
            f"📅 **{'Today' if reminder_type == '2h' else 'Date'}:** {game_data['date']}\n"
            f"🕒 **Time:** {game_data['time_display']}\n"
            f"📍 **Venue:** {game_data['venue']}\n"
            f"📊 **Skill Level:** {game_data['skill'].title()}\n\n"
        )
        
        if reminder_type == '24h':
            header = (
                f"⏰ **24-Hour Game Reminder!** ⏰\n\n"
                f"**{game_data['sport']}** game is **tomorrow**!\n\n"
            )
            footer = "See you tomorrow! 🎉"
        else:  
            header = (
                f"🚨 **2-Hour Game Alert!** 🚨\n\n"
                f"**{game_data['sport']}** game starts in **2 hours**!\n\n"
            )
            footer = "Time to get ready! 🏃‍♂️💨"
        
        return header + common_info + footer

    async def send_24h_reminder(self, context: ContextTypes.DEFAULT_TYPE, game_data, game_id):
        reminder_config = {
            'text': self._create_reminder_text(game_data, '24h'),
            'send_poll': True,
            'db_field': 'reminder_24h_sent',
            'period': '24h'
        }
        await self._send_reminder_message(context, game_data, game_id, reminder_config)

    async def send_2h_reminder(self, context: ContextTypes.DEFAULT_TYPE, game_data, game_id):
        reminder_config = {
            'text': self._create_reminder_text(game_data, '2h'),
            'send_poll': False,
            'db_field': 'reminder_2h_sent',
            'period': '2h'
        }
        await self._send_reminder_message(context, game_data, game_id, reminder_config)

    async def send_game_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        await self.schedule_all_existing_reminders(context)