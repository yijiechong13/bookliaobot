import os
from telegram import Update, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from dotenv import load_dotenv

load_dotenv()

async def handle_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get the chat member update
        chat_member = update.chat_member
        chat_id = str(chat_member.chat.id)
        
        if chat_member.new_chat_member.user.id == context.bot.id:
            return
            
        db = context.bot_data['db']
        
        game = await db.get_game_by_group_id(chat_id)
        if not game:
            return  
            
        # Skip if game is not open
        if game.get('status') != 'open':
            return
            
        # Get current member count
        try:
            member_count = await context.bot.get_chat_member_count(chat_id)
            # Subtract 1 for the bot itself
            player_count = member_count - 1
        except Exception as e:
            print(f"❌ Error getting member count for chat {chat_id}: {e}")
            return
            
        # Update the database with new player count
        await db.update_game(game['id'], {"player_count": player_count})
        
        # Update the announcement message
        await update_announcement_with_count(context, game, player_count)
        
        # Log the update
        user = chat_member.new_chat_member.user
        old_status = chat_member.old_chat_member.status
        new_status = chat_member.new_chat_member.status
        
        if old_status in [ChatMember.LEFT, ChatMember.KICKED] and new_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            print(f"👥 Player joined {game['sport']} game: {user.first_name} (Count: {player_count})")
        elif old_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR] and new_status in [ChatMember.LEFT, ChatMember.KICKED]:
            print(f"👋 Player left {game['sport']} game: {user.first_name} (Count: {player_count})")
            
    except Exception as e:
        print(f"❌ Error in handle_member_update: {e}")

async def update_announcement_with_count(context: ContextTypes.DEFAULT_TYPE, game, player_count):
    try:
        ANNOUNCEMENT_CHANNEL = os.getenv("ANNOUNCEMENT_CHANNEL")
        announcement_msg_id = game.get("announcement_msg_id")
        
        if not ANNOUNCEMENT_CHANNEL or not announcement_msg_id:
            return
            
        # Create updated announcement text
        announcement_text = (
            f"🎮 {game['sport']} Game!\n\n"
            f"📅 Date: {game['date']}\n"
            f"🕒 Time: {game['time_display']}\n"
            f"📍 Venue: {game['venue']}\n"
            f"📊 Skill Level: {game['skill'].title()}\n"
            f"👥 Players: {player_count}\n"
            f"👤 Host: @{game.get('host_username', 'Anonymous')}\n\n"
            f"🔗 Join Group: {game['group_link']}"
        )
        
        await context.bot.edit_message_text(
            chat_id=ANNOUNCEMENT_CHANNEL,
            message_id=announcement_msg_id,
            text=announcement_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✋ Join Game", url=game["group_link"])]
            ])
        )
        
        print(f"✅ Updated announcement for {game['sport']} game with {player_count} players")
        
    except Exception as e:
        print(f"❌ Error updating announcement: {e}")

async def get_initial_player_count(context: ContextTypes.DEFAULT_TYPE, group_id):
    try:
        chat_id = f"-100{abs(int(group_id))}"
        member_count = await context.bot.get_chat_member_count(chat_id)
        # Subtract 1 for the bot itself
        return member_count - 1
    except Exception as e:
        print(f"❌ Error getting initial player count: {e}")
        return 1  # Default to 1 (just the host)