import os
from telegram.ext import ContextTypes
from telegram import Update, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from dotenv import load_dotenv

load_dotenv()

async def track_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for new member joins (filters.StatusUpdate.NEW_CHAT_MEMBERS)
    """
    try:
        if not update.message or not update.message.new_chat_members:
            return
            
        chat_id = update.message.chat.id
        new_members = update.message.new_chat_members
        
        # Log the actual chat_id for debugging
        print(f"🔍 New members in chat_id: {chat_id}")
        
        # Filter out bots
        real_members = [member for member in new_members if not member.is_bot]
        if not real_members:
            return
            
        # Get game data
        db = context.bot_data.get('db')
        if not db:
            return
            
        game_data = await get_game_by_group_id(db, chat_id)
        if not game_data:
            print(f"⚠️ No game found for chat_id: {chat_id}")
            return
            
        # Filter out host (already counted)
        host_id = game_data.get('host')
        new_non_host_members = [
            member for member in real_members 
            if str(member.id) != str(host_id)
        ]
        
        if new_non_host_members:
            # Update member count by the number of new members
            await update_member_count(
                context, 
                game_data, 
                len(new_non_host_members), 
                True,  # is_join
                new_non_host_members
            )
            
    except Exception as e:
        print(f"❌ Error in track_new_members: {e}")

async def track_left_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for member leaves (filters.StatusUpdate.LEFT_CHAT_MEMBER)
    """
    try:
        if not update.message or not update.message.left_chat_member:
            return
            
        chat_id = update.message.chat.id
        left_member = update.message.left_chat_member
        
        # Log the actual chat_id for debugging
        print(f"🔍 Member left chat_id: {chat_id}")
        
        # Skip bots
        if left_member.is_bot:
            return
            
        # Get game data
        db = context.bot_data.get('db')
        if not db:
            return
            
        game_data = await get_game_by_group_id(db, chat_id)
        if not game_data:
            print(f"⚠️ No game found for chat_id: {chat_id}")
            return
            
        # Skip if this is the host leaving (they should cancel the game instead)
        host_id = game_data.get('host')
        if str(left_member.id) == str(host_id):
            print(f"⚠️ Host {left_member.first_name} left the game - this might need special handling")
            return
            
        # Update member count
        await update_member_count(
            context, 
            game_data, 
            1, 
            False,  # is_join
            [left_member]
        )
        
    except Exception as e:
        print(f"❌ Error in track_left_members: {e}")

async def track_chat_member_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for ChatMemberUpdated events (admin actions like kicks/bans)
    """
    try:
        chat_member_update = update.chat_member
        if not chat_member_update:
            return
            
        chat_id = chat_member_update.chat.id
        user = chat_member_update.new_chat_member.user
        old_status = chat_member_update.old_chat_member.status
        new_status = chat_member_update.new_chat_member.status
        
        # Log the actual chat_id for debugging
        print(f"🔍 Chat member update in chat_id: {chat_id}")
        
        # Skip bots
        if user.is_bot:
            return
            
        # Get game data
        db = context.bot_data.get('db')
        if not db:
            return
            
        game_data = await get_game_by_group_id(db, chat_id)
        if not game_data:
            print(f"⚠️ No game found for chat_id: {chat_id}")
            return
            
        # Skip host
        host_id = game_data.get('host')
        if str(user.id) == str(host_id):
            return
            
        # Check for admin actions that affect member count
        is_removed = False
        is_added = False
        
        # User was kicked or banned
        if (old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and 
            new_status in [ChatMemberStatus.KICKED, ChatMemberStatus.LEFT]):
            is_removed = True
            
        # User was unbanned or promoted to member
        elif (old_status in [ChatMemberStatus.KICKED, ChatMemberStatus.LEFT] and 
              new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]):
            is_added = True
            
        if is_removed or is_added:
            await update_member_count(
                context, 
                game_data, 
                1, 
                is_added,  # is_join
                [user]
            )
            
    except Exception as e:
        print(f"❌ Error in track_chat_member_updates: {e}")

async def get_game_by_group_id(db, group_id):
    """
    Find a game by its group ID
    """
    try:
        games_ref = db.db.collection("game")
        
        # Convert supergroup ID back to stored format if needed
        search_group_id = group_id
        if isinstance(group_id, int) and group_id < -1000000000000:
            # This is a supergroup ID, convert back to stored format
            search_group_id = str(abs(group_id + 1000000000000))
            print(f"🔄 Converted supergroup ID {group_id} to stored format: {search_group_id}")
        else:
            search_group_id = str(group_id)
        
        print(f"🔍 Searching for game with group_id: {search_group_id}")
        
        query = games_ref.where(filter=db.firestore.FieldFilter("group_id", "==", search_group_id))
        results = list(query.stream())
        
        if results:
            game_doc = results[0]
            game_data = {"id": game_doc.id, **game_doc.to_dict()}
            print(f"✅ Found game: {game_data['id']} for group_id: {search_group_id}")
            return game_data
        else:
            print(f"❌ No game found for group_id: {search_group_id}")
            return None
        
    except Exception as e:
        print(f"❌ Error getting game by group ID: {e}")
        return None

async def update_member_count(context: ContextTypes.DEFAULT_TYPE, game_data, count_change, is_join, users):
    try:
        db = context.bot_data.get('db')
        if not db:
            return
            
        game_id = game_data.get('id')
        current_count = game_data.get('player_count', 1)
        
        # Calculate new count
        new_count = current_count + count_change if is_join else max(1, current_count - count_change)
        
        # Update Firestore
        update_data = {"player_count": new_count}
        db.update_game(game_id, update_data)
        
        # Force update announcement message
        announcement_msg_id = game_data.get("announcement_msg_id")
        if announcement_msg_id:
            try:
                await update_announcement_with_count(
                    context, 
                    game_data, 
                    new_count, 
                    announcement_msg_id
                )
                print(f"✅ Updated announcement for game {game_id} to {new_count} players")
            except Exception as e:
                print(f"❌ Failed to update announcement: {e}")
                # Try to get fresh game data if update failed
                fresh_data = db.get_game(game_id)
                if fresh_data:
                    await update_announcement_with_count(
                        context,
                        fresh_data,
                        new_count,
                        fresh_data.get("announcement_msg_id")
                    )
        
        # Log user actions
        user_names = [user.first_name for user in users]
        action = "joined" if is_join else "left"
        print(f"👥 {', '.join(user_names)} {action}. New count: {new_count}")
        
    except Exception as e:
        print(f"❌ Error in update_member_count: {e}")

async def update_announcement_with_count(context: ContextTypes.DEFAULT_TYPE, game_data, member_count, announcement_msg_id):
    try:
        ANNOUNCEMENT_CHANNEL = os.getenv("ANNOUNCEMENT_CHANNEL")
        if not ANNOUNCEMENT_CHANNEL:
            print("❌ No announcement channel configured")
            return False
            
        # Ensure we have required data
        required_fields = ['sport', 'date', 'time_display', 'venue', 'skill', 'group_link']
        if not all(field in game_data for field in required_fields):
            print("❌ Missing required game data fields")
            return False
            
        # Format announcement text
        announcement_text = (
            f"🎮 New {game_data['sport']} Game!\n\n"
            f"📅 Date: {game_data['date']}\n"
            f"🕒 Time: {game_data['time_display']}\n"
            f"📍 Venue: {game_data['venue']}\n"
            f"📊 Skill Level: {game_data['skill'].title()}\n"
            f"👥 Players: {member_count}\n"
            f"👤 Host: @{game_data.get('host_username', 'Anonymous')}\n\n"
            f"🔗 Join Group: {game_data['group_link']}"
        )
        
        # Create keyboard
        keyboard = [[InlineKeyboardButton("✋ Join Game", url=game_data['group_link'])]]
        
        # Edit message
        await context.bot.edit_message_text(
            chat_id=ANNOUNCEMENT_CHANNEL,
            message_id=announcement_msg_id,
            text=announcement_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return True
        
    except Exception as e:
        print(f"❌ Detailed error updating announcement: {str(e)}")
        print(f"Channel: {ANNOUNCEMENT_CHANNEL}, Message ID: {announcement_msg_id}")
        return False

async def get_actual_member_count(context: ContextTypes.DEFAULT_TYPE, group_id):
    """
    Get the actual current member count of a group (excluding bots)
    This is useful for initialization or verification
    """
    try:
        # Ensure group_id is an integer for the API call
        if isinstance(group_id, str):
            group_id = int(group_id)

       # Correct supergroup ID formatting
        if group_id > 0:  # If positive, assume it's a regular group ID
            group_id = -1000000000000 - group_id  # Correct supergroup format
        
        print(f"🔍 Getting member count for group_id: {group_id}")
        
        # Check if the chat exists and bot has access
        try:
            chat_info = await context.bot.get_chat(group_id)
            print(f"✅ Chat found: {chat_info.title} (Type: {chat_info.type})")
        except Exception as e:
            print(f"❌ Cannot access chat {group_id}: {e}")
            return 1  # Default to 1 if chat is not accessible
        
        chat_member_count = await context.bot.get_chat_member_count(group_id)
        print(f"📊 Total members in chat {group_id}: {chat_member_count}")
        
        # Subtract at least 1 for the bot, minimum 1 for host
        actual_count = max(1, chat_member_count - 1)
        print(f"📊 Calculated member count (excluding bot): {actual_count}")
        
        return actual_count
        
    except Exception as e:
        print(f"❌ Error getting actual member count for {group_id}: {e}")
        return 1

async def sync_member_count(context: ContextTypes.DEFAULT_TYPE, game_data):
    """
    Sync the stored member count with the actual group count
    Use this sparingly, only when needed (e.g., on startup or after errors)
    """
    try:
        group_id = game_data.get('group_id')
        if not group_id:
            print(f"⚠️ No group_id found for game {game_data.get('id')}")
            return
            
        print(f"🔄 Syncing member count for game {game_data.get('id')} with group_id: {group_id}")
        
        actual_count = await get_actual_member_count(context, group_id)
        stored_count = game_data.get('player_count', 1)
        
        if actual_count != stored_count:
            db = context.bot_data.get('db')
            if db:
                db.update_game(game_data.get('id'), {"player_count": actual_count})
                print(f"🔄 Synced member count for game {game_data.get('id')}: {stored_count} -> {actual_count}")
                
                # Update announcement if needed
                announcement_msg_id = game_data.get("announcement_msg_id")
                if announcement_msg_id:
                    await update_announcement_with_count(context, game_data, actual_count, announcement_msg_id)
        else:
            print(f"✅ Member count already in sync for game {game_data.get('id')}: {actual_count}")
                    
    except Exception as e:
        print(f"❌ Error syncing member count: {e}")

async def initialize_member_counts(context: ContextTypes.DEFAULT_TYPE):
    """
    Initialize member counts for existing games (run once on startup)
    """
    try:
        db = context.bot_data.get('db')
        if not db:
            return
            
        # Get all open games
        games_ref = db.db.collection("game")
        query = games_ref.where(filter=db.firestore.FieldFilter("status", "==", "open"))
        results = query.stream()
        
        for game_doc in results:
            game_data = game_doc.to_dict()
            game_id = game_doc.id
            group_id = game_data.get('group_id')
            
            print(f"🔄 Processing game {game_id} with group_id: {group_id}")
            
            if group_id:
                try:
                    # Get actual member count
                    actual_count = await get_actual_member_count(context, group_id)
                    
                    # Update the game document
                    db.update_game(game_id, {"player_count": actual_count})
                    
                    # Update the announcement message with the correct count
                    announcement_msg_id = game_data.get("announcement_msg_id")
                    if announcement_msg_id:
                        # Add the updated count to game_data for the announcement update
                        game_data['player_count'] = actual_count
                        await update_announcement_with_count(
                            context, 
                            game_data, 
                            actual_count, 
                            announcement_msg_id
                        )
                        print(f"✅ Updated announcement for game {game_id} with count: {actual_count}")
                    
                    print(f"✅ Initialized member count for game {game_id}: {actual_count}")
                except Exception as e:
                    print(f"❌ Error processing game {game_id}: {e}")
                    # Set to 1 if there's an error
                    db.update_game(game_id, {"player_count": 1})
                    print(f"⚠️ Set fallback member count for game {game_id}: 1")
            else:
                # If no group_id, set to 1 (host only)
                db.update_game(game_id, {"player_count": 1})
                print(f"✅ Set default member count for game {game_id}: 1 (host only)")
                
    except Exception as e:
        print(f"❌ Error initializing member counts: {e}")
