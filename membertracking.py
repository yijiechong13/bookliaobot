import os
from telegram.ext import ContextTypes
from telegram import Update, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from dotenv import load_dotenv

load_dotenv()

async def track_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.new_chat_members:
            return
            
        chat_id = update.message.chat.id
        new_members = update.message.new_chat_members #returns a list 
        
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
        print(f"❌ Error initializing member tracking: {e}")

# Keep your existing helper functions
async def get_game_by_group_id(db, group_id):
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
            print("❌ No database connection available")
            return
            
        game_id = game_data.get('id')
        current_count = game_data.get('player_count', 1)
        
        # Calculate new count
        new_count = current_count + count_change if is_join else max(1, current_count - count_change)
        
        print(f"🔄 Updating count for game {game_id}: {current_count} -> {new_count}")
        
        # Update Firestore
        update_data = {"player_count": new_count}
        db.update_game(game_id, update_data)
        
        # Update the game_data with new count for announcement update
        game_data['player_count'] = new_count
        
        # Force update announcement message
        announcement_msg_id = game_data.get("announcement_msg_id")
        if announcement_msg_id:
            print(f"🔄 Attempting to update announcement message ID: {announcement_msg_id}")
            try:
                success = await update_announcement_with_count(
                    context, 
                    game_data, 
                    new_count, 
                    announcement_msg_id
                )
                if success:
                    print(f"✅ Updated announcement for game {game_id} to {new_count} players")
                else:
                    print(f"❌ Failed to update announcement for game {game_id}")
            except Exception as e:
                print(f"❌ Exception while updating announcement: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ No announcement_msg_id found for game {game_id}")
        
        # Log user actions
        user_names = [user.first_name for user in users]
        action = "joined" if is_join else "left"
        print(f"👥 {', '.join(user_names)} {action}. New count: {new_count}")
        
    except Exception as e:
        print(f"❌ Error in update_member_count: {e}")
        import traceback
        traceback.print_exc()

async def update_announcement_with_count(context: ContextTypes.DEFAULT_TYPE, game_data, member_count, announcement_msg_id):
    # Keep your existing announcement update logic
    try:
        ANNOUNCEMENT_CHANNEL = os.getenv("ANNOUNCEMENT_CHANNEL")
        
        if not ANNOUNCEMENT_CHANNEL:
            print("❌ No announcement channel configured")
            return False
            
        # Ensure we have required data
        required_fields = ['sport', 'date', 'time_display', 'venue', 'skill', 'group_link']
        missing_fields = [field for field in required_fields if field not in game_data]
        
        if missing_fields:
            print(f"❌ Missing required game data fields: {missing_fields}")
            print(f"Available fields: {list(game_data.keys())}")
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
        
        print(f"🔄 Editing message in channel {ANNOUNCEMENT_CHANNEL}, message ID: {announcement_msg_id}")
        
        # Edit message with better error handling
        try:
            await context.bot.edit_message_text(
                chat_id=ANNOUNCEMENT_CHANNEL,
                message_id=int(announcement_msg_id),  # Ensure it's an integer
                text=announcement_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=None  # Explicitly set parse mode
            )
            print(f"✅ Successfully updated announcement message")
            return True
            
        except Exception as edit_error:
            print(f"❌ Telegram API error while editing message: {edit_error}")
            
            # Check if it's a "message not found" error
            if "message not found" in str(edit_error).lower():
                print("⚠️ Message not found - it may have been deleted")
                # Optionally, you could create a new announcement message here
                
            elif "message is not modified" in str(edit_error).lower():
                print("ℹ️ Message content is identical, no update needed")
                return True
                
            elif "bad request" in str(edit_error).lower():
                print(f"⚠️ Bad request error - checking channel access and message ID format")
                # Verify channel access
                try:
                    chat_info = await context.bot.get_chat(ANNOUNCEMENT_CHANNEL)
                    print(f"✅ Channel accessible: {chat_info.title}")
                except Exception as channel_error:
                    print(f"❌ Cannot access channel: {channel_error}")
                    
            return False
        
    except Exception as e:
        print(f"❌ Detailed error updating announcement: {str(e)}")
        print(f"Channel: {ANNOUNCEMENT_CHANNEL}, Message ID: {announcement_msg_id}")
        print(f"Game data keys: {list(game_data.keys())}")
        import traceback
        traceback.print_exc()
        return False

async def get_actual_member_count(context: ContextTypes.DEFAULT_TYPE, group_id):
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
                    # Update game_data with new count
                    game_data['player_count'] = actual_count
                    await update_announcement_with_count(context, game_data, actual_count, announcement_msg_id)
        else:
            print(f"✅ Member count already in sync for game {game_data.get('id')}: {actual_count}")
                    
    except Exception as e:
        print(f"❌ Error syncing member count: {e}")

async def initialize_member_counts(context: ContextTypes.DEFAULT_TYPE):
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

async def track_all_chat_member_changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member_update: ChatMemberUpdated = update.chat_member
        old_status = member_update.old_chat_member.status
        new_status = member_update.new_chat_member.status
        user = member_update.new_chat_member.user
        chat = member_update.chat

        if old_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED] and new_status == ChatMemberStatus.MEMBER:
            print(f"[JOIN] {user.full_name} (id: {user.id}) joined '{chat.title}' via status change.")

        elif old_status == ChatMemberStatus.MEMBER and new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            print(f"[LEAVE] {user.full_name} (id: {user.id}) left or was removed from '{chat.title}'.")

        else:
            print(f"[INFO] {user.full_name} status changed from {old_status} to {new_status} in '{chat.title}'")

    except Exception as e:
        print(f"[ERROR] Failed to process chat member change: {e}")

async def periodic_member_sync(context):
    try:
        print("🔄 Running periodic member count sync...")
        db = context.bot_data.get('db')
        if not db:
            return
            
        # Get all open games
        games_ref = db.db.collection("game")
        query = games_ref.where(filter=db.firestore.FieldFilter("status", "==", "open"))
        results = query.stream()
        
        synced_count = 0
        for game_doc in results:
            game_data = game_doc.to_dict()
            game_id = game_doc.id
            group_id = game_data.get('group_id')
            
            if group_id:
                try:
                    # Get actual member count from Telegram
                    actual_count = await get_actual_member_count(context, group_id)
                    stored_count = game_data.get('player_count', 1)
                    
                    # Only update if there's a difference
                    if actual_count != stored_count:
                        db.update_game(game_id, {"player_count": actual_count})
                        
                        # Update announcement
                        announcement_msg_id = game_data.get("announcement_msg_id")
                        if announcement_msg_id:
                            game_data['player_count'] = actual_count
                            await update_announcement_with_count(
                                context, 
                                game_data, 
                                actual_count, 
                                announcement_msg_id
                            )
                        
                        print(f"🔄 Synced game {game_id}: {stored_count} -> {actual_count}")
                        synced_count += 1
                        
                except Exception as e:
                    print(f"❌ Error syncing game {game_id}: {e}")
                    
        if synced_count > 0:
            print(f"✅ Synced {synced_count} games")
        else:
            print("📋 All games already in sync")
            
    except Exception as e:
        print(f"❌ Error in periodic member sync: {e}")

# Also update your get_actual_member_count function with better error handling
async def get_actual_member_count(context: ContextTypes.DEFAULT_TYPE, group_id):
    try:
        # Ensure group_id is properly formatted
        if isinstance(group_id, str):
            if group_id.startswith('-'):
                group_id = int(group_id)
            else:
                # Convert stored format to supergroup format
                group_id = -1000000000000 - int(group_id)
        elif isinstance(group_id, int) and group_id > 0:
            group_id = -1000000000000 - group_id
        
        print(f"🔍 Getting member count for group_id: {group_id}")
        
        # First, verify chat access
        try:
            chat_info = await context.bot.get_chat(group_id)
            print(f"✅ Chat accessible: {chat_info.title}")
        except Exception as e:
            print(f"❌ Cannot access chat {group_id}: {e}")
            return 1
        
        # Get total member count
        total_count = await context.bot.get_chat_member_count(group_id)
        print(f"📊 Total chat members: {total_count}")
        
        # Try to get more accurate count by checking administrators
        try:
            admins = await context.bot.get_chat_administrators(group_id)
            bot_count = sum(1 for admin in admins if admin.user.is_bot)
            print(f"🤖 Bot administrators found: {bot_count}")
            
            # Subtract bots, ensure minimum of 1
            actual_count = max(1, total_count - bot_count)
            print(f"📊 Calculated member count: {actual_count}")
            
            return actual_count
            
        except Exception as admin_error:
            print(f"⚠️ Could not get admin list: {admin_error}")
            # Fallback: subtract 1 for the bot
            return max(1, total_count - 1)
            
    except Exception as e:
        print(f"❌ Error getting member count for {group_id}: {e}")
        return 1