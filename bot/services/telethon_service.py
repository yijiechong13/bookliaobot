import os
from telethon import TelegramClient
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest, EditAdminRequest, LeaveChannelRequest
from telethon.tl.types import ChatAdminRights, ChatBannedRights
from telethon.tl.functions.messages import EditChatDefaultBannedRightsRequest
from dotenv import load_dotenv
import logging
from utils.constants import SPORT_EMOJIS 

load_dotenv()

class TelethonService:
    def __init__(self):
        self.api_id = int(os.getenv("TELEGRAM_API_ID"))
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
        self.bot_username = os.getenv("BOT_USERNAME", "BookaCourt_bot")
        self.bot_token = os.getenv("BOT_TOKEN")
        self.client = None
        self.initialized = False
        
    async def initialize(self):
        
        if self.initialized:
            return True
            
        try:
            self.client = TelegramClient('bot_session', self.api_id, self.api_hash)
            
            #Connects to telegeram and logs in to account: can use via phone number or bot accounts 
            #only user account can create group (bot token cannot)
            await self.client.start(phone = self.phone_number)
            self.initialized = True

        except Exception as e:
            logging.error(f"Failed to initialize Telethon client: {e}")
            return False
    
    async def create_game_group(self, game_data, host_user):

        if not self.client:
            await self.initialize()

        try:
            sport = game_data["sport"]
            sport_key = sport.lower()
            emoji = SPORT_EMOJIS.get(sport_key, "🏅")  

            venue = game_data["venue"].title()
            date = game_data["date"]

            group_name = f"{emoji} {sport.title()} @ {venue} • {date}"

            #Group description 
            description = (
                f"🏟️ Sport: {game_data['sport']}\n"
                f"🕒 Time: {game_data['time_display']}\n"
                f"📍 Venue: {game_data['venue']}\n"
                f"📊 Skill Level: {game_data['skill'].title()}\n"
                f"👤 Host: @{host_user.username or host_user.first_name}\n\n"
                f"Welcome to the game! Use this group to coordinate and discuss."
            )
            
            result = await self.client(CreateChannelRequest(
                title=group_name,
                about = description,
                megagroup = True
            ))
            
            group_entity = result.chats[0]
            group_id = group_entity.id

            # Add bot to group
            bot_entity = await self.client.get_entity(self.bot_username)
            await self.client(InviteToChannelRequest(
                channel=group_entity,
                users=[bot_entity]
            ))

            admin_rights = ChatAdminRights(
            change_info=False,           # Can't change group info
            post_messages=True,          # Can send messages 
            edit_messages=True,         # Can edit messages
            delete_messages=True,        # Can delete messages 
            ban_users=True,             # Can ban users
            invite_users=True,          # Can invite users
            pin_messages=True,           # Can pin messages 
            add_admins=False,            # Can't add other admins
            anonymous=False,             # Not anonymous
            manage_call=False,           # Can't manage voice calls
            other=False,                # No other special permissions              
        )
        
            # Make bot an admin
            await self.client(EditAdminRequest(
                channel=group_entity,
                user_id=bot_entity,
                admin_rights=admin_rights,
                rank="Bot"  
            ))

            await self.client(EditChatDefaultBannedRightsRequest(
                peer=group_entity,
                banned_rights=ChatBannedRights(
                    until_date=None,
                    view_messages=False,
                    send_messages=False,
                    send_media=False,
                    send_stickers=False,
                    send_gifs=False,
                    send_games=False,
                    send_inline=False,
                    embed_links=False,
                    send_polls=False,
                    change_info=False,
                    invite_users=False,
                    pin_messages=False, 
                )
            ))


            #Making host the admin 
            host_entity = await self.client.get_entity(host_user.id)
            await self.client(EditAdminRequest(
                channel=group_entity,
                user_id=host_entity,
                admin_rights=ChatAdminRights(
                change_info=True,
                post_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=True,
                anonymous=False,
                manage_call=True,
                other=True
            ),
                rank="Host"
            ))

            
            # Generate invite link
            invite = await self.client(ExportChatInviteRequest(group_entity))
            invite_link = invite.link

            welcome_message = (
        f"👋 **Welcome to your game session!**\n\n"
        f"📅 **Date:** {game_data['date']}\n"
        f"🕒 **Time:** {game_data['time_display']}\n"
        f"📍 **Venue:** {game_data['venue'].title()}\n"
        f"📊 **Skill Level:** {game_data['skill'].title()}\n\n"
        f"📋 **What to expect:**\n"
        f"• A poll will be sent 24 hours before the game to confirm attendance\n"
        f"• You'll receive 24-hour & 2-hour reminders before the game starts\n"
        f"• ℹ️ You can also find these details in the **group description** anytime.\n\n"
        f"⚠️ **Important for Host:** If there are changes to the **time or venue**, "
        f"please *cancel and recreate the game*. This ensures the updated info appears "
        f"correctly in the announcement channel and other listings. "
        f"Changes discussed only in this group won't be seen by others browsing for games.\n\n"
        f"Enjoy your session and have fun! 🎉"
    )


            await self.client.send_message(
                entity=group_entity,
                message=welcome_message,
                parse_mode="markdown"
            )


            #Creator leaves the group after setup
            await self.client(LeaveChannelRequest(group_entity))

            return {
                "group_link": invite_link,
                "group_id": group_id,
                "group_name": group_name,
                "bot_added": True,
                "creator_left": True
            } 
    
        except Exception as e:
            logging.error(f"Failed to create group: {e}")
            return None
    
    
    async def close(self):
        if self.client:
            await self.client.disconnect()

telethon_service = TelethonService()