import nest_asyncio
nest_asyncio.apply()

import json
import os
import re
import asyncio
import logging
from threading import Thread
from flask import Flask

# Use pyTelegramBotAPI for Render compatibility
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "YOUR_ADMIN_ID_HERE"))

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Global data structures
user_demo_status = {"type_1": [], "type_2": []}
allowed_users = set()
blocked_users = set()
pending_plan_selection = {}

# Indian states list
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu & Kashmir"
]

def load_json_file(filename, default_value):
    """Load JSON file with error handling"""
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return default_value
    return default_value

def save_json_file(filename, data):
    """Save data to JSON file with error handling"""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Failed to save {filename}: {e}")
        return False

# Load data from files
user_demo_status = load_json_file("demo_status.json", {"type_1": [], "type_2": []})
if not isinstance(user_demo_status, dict) or "type_1" not in user_demo_status:
    user_demo_status = {"type_1": [], "type_2": []}

allowed_users = set(load_json_file("allowed_users.json", []))
blocked_users = set(load_json_file("blocked_users.json", []))

def show_state_selection(chat_id, message_id, plan_info):
    """Show Indian state selection keyboard"""
    keyboard = InlineKeyboardMarkup()
    
    # Add states in rows of 2
    for i in range(0, len(INDIAN_STATES), 2):
        row = []
        row.append(InlineKeyboardButton(INDIAN_STATES[i], callback_data=f"state_{INDIAN_STATES[i]}"))
        if i + 1 < len(INDIAN_STATES):
            row.append(InlineKeyboardButton(INDIAN_STATES[i + 1], callback_data=f"state_{INDIAN_STATES[i + 1]}"))
        keyboard.add(*row)
    
    bot.edit_message_text(
        "📍 <b>Select Your State</b>\n\nPlease choose your state from the list below:",
        chat_id, message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.message_handler(commands=['start'])
def start_command(message):
    """Start command handler - show main menu directly"""
    user_id = message.from_user.id
    
    # Check if user is already blocked
    if user_id in blocked_users:
        bot.reply_to(message, 
            "❌ Access denied. You are not eligible to use this service.")
        return
    
    # Show main menu directly
    show_main_menu(message.chat.id)

def show_main_menu(chat_id):
    """Show the main menu with type selection"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔸 𝐓𝐲𝐩𝐞 𝟏", callback_data="type_1"))
    keyboard.add(InlineKeyboardButton("🔹 𝐓𝐲𝐩𝐞 𝟐", callback_data="type_2"))
    
    message = """📲 𝐍𝐌𝐌𝐒 𝐌𝐎𝐃 —
Choose one

🔸 𝐓𝐲𝐩𝐞 𝟏:
   𝐖𝐨𝐫𝐤𝐞𝐫𝐬 𝐜𝐨𝐮𝐧𝐭 𝐫𝐞𝐦𝐨𝐯𝐞
   𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 𝐨𝐩𝐭𝐢𝐨𝐧𝐬 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐅𝐚𝐜𝐤 𝐥𝐨𝐜𝐚𝐭𝐢𝐨𝐧 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐓𝐢𝐦𝐞 𝐜𝐡𝐚𝐧𝐠𝐞 𝐞𝐧𝐚𝐛𝐥𝐞

🔹 𝐓𝐲𝐩𝐞 𝟐:
   𝐆𝐚𝐥𝐥𝐞𝐫𝐲 𝐩𝐡𝐨𝐭𝐨 𝐮𝐩𝐥𝐨𝐚𝐝
   𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 𝐨𝐩𝐭𝐢𝐨𝐧 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐅𝐚𝐜𝐤 𝐥𝐨𝐜𝐚𝐭𝐢𝐨𝐧 𝐛𝐲𝐩𝐚𝐬𝐬
   𝐓𝐢𝐦𝐞 𝐜𝐡𝐚𝐧𝐠𝐞"""
    
    bot.send_message(chat_id, message, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Handle button clicks for plan selection"""
    user_id = call.from_user.id
    user = call.from_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "NoUsername"
    data = call.data

    # Check if user is blocked
    if user_id in blocked_users:
        bot.edit_message_text("❌ Access denied. You are not eligible to use this service.",
                             call.message.chat.id, call.message.message_id)
        return

    if data in ["type_1", "type_2"]:
        price_text = "Half Month: ₹1000\nFull Month: ₹2000\nDemo: Free" if data == "type_1" else "Half Month: ₹1500\nFull Month: ₹2500\nDemo: Free"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Half Month", callback_data=f"half_{data}"))
        keyboard.add(InlineKeyboardButton("Full Month", callback_data=f"full_{data}"))
        keyboard.add(InlineKeyboardButton("Demo", callback_data=f"demo_{data}"))
        
        bot.edit_message_text(
            f"Choose plan for {data.replace('_', ' ').title()}:\n{price_text}",
            call.message.chat.id, call.message.message_id,
            reply_markup=keyboard
        )

    elif data.startswith("demo"):
        demo_type = data.split("_", 1)[1]
        demo_name = "Type 1" if demo_type == "type_1" else "Type 2"

        if user_id in user_demo_status[demo_type]:
            bot.edit_message_text(f"❌ {demo_name} Demo already taken.",
                                 call.message.chat.id, call.message.message_id)
        else:
            # Store plan selection and ask for state
            pending_plan_selection[user_id] = {
                "type": "demo",
                "plan": demo_name,
                "demo_type": demo_type
            }
            show_state_selection(call.message.chat.id, call.message.message_id, pending_plan_selection[user_id])

    elif data.startswith("half") or data.startswith("full"):
        plan = "Half Month" if data.startswith("half") else "Full Month"
        mod_type = "Type 1" if "type_1" in data else "Type 2"

        # Store plan selection and ask for state
        pending_plan_selection[user_id] = {
            "type": "plan",
            "plan": plan,
            "mod_type": mod_type,
            "plan_data": data
        }
        show_state_selection(call.message.chat.id, call.message.message_id, pending_plan_selection[user_id])

    elif data.startswith("state_"):
        selected_state = data.replace("state_", "")
        
        # Check if user has pending plan selection
        if user_id not in pending_plan_selection:
            bot.edit_message_text("❌ Session expired. Please start again with /start",
                                 call.message.chat.id, call.message.message_id)
            return
        
        plan_info = pending_plan_selection[user_id]
        
        # Check if selected state is Jammu & Kashmir
        if selected_state == "Jammu & Kashmir":
            # Block the user permanently
            blocked_users.add(user_id)
            save_json_file("blocked_users.json", list(blocked_users))
            
            bot.edit_message_text(
                "❌ <b>Access Denied</b>\n\n"
                "माफ़ करें, यह सेवा जम्मू और कश्मीर में उपलब्ध नहीं है।\n"
                "आपकी समझ के लिए धन्यवाद।",
                call.message.chat.id, call.message.message_id,
                parse_mode="HTML"
            )
            
            # Notify admin about blocked user
            try:
                bot.send_message(ADMIN_ID,
                    f"🚫 <b>User Blocked (J&K State Selection)</b>\n\n"
                    f"👤 Name: {full_name}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"📍 Selected State: {selected_state}\n"
                    f"👤 Username: {username}\n"
                    f"📋 Was requesting: {plan_info['plan']}",
                    parse_mode="HTML"
                )
            except:
                pass
            
            # Remove from pending
            del pending_plan_selection[user_id]
            logging.info(f"Blocked user {user_id} for selecting J&K state")
            return
        
        # User selected valid state, process their request
        if plan_info["type"] == "demo":
            # Add to demo status
            user_demo_status[plan_info["demo_type"]].append(user_id)
            save_json_file("demo_status.json", user_demo_status)

            bot.edit_message_text(f"⏳ Please wait while we set up your {plan_info['plan']} demo...",
                                 call.message.chat.id, call.message.message_id)
            
            # Send admin notification
            try:
                keyboard = types.ForceReply()
                bot.send_message(ADMIN_ID,
                    f"👤 <b>{full_name}</b> ({username})\n"
                    f"🆔 {user_id}\n"
                    f"🎁 Requested: <b>{plan_info['plan']} Demo</b>\n"
                    f"📍 State: <b>{selected_state}</b>\n"
                    f"✅ <b>Location Verified</b>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Failed to send admin notification: {e}")
        
        elif plan_info["type"] == "plan":
            bot.edit_message_text(f"✅ You selected {plan_info['plan']} for {plan_info['mod_type']}. Please wait...",
                                 call.message.chat.id, call.message.message_id)
            
            # Send admin notification
            try:
                keyboard = types.ForceReply()
                bot.send_message(ADMIN_ID,
                    f"👤 <b>{full_name}</b> ({username})\n"
                    f"🆔 {user_id}\n"
                    f"💰 Order: <b>{plan_info['plan']} for {plan_info['mod_type']}</b>\n"
                    f"📍 State: <b>{selected_state}</b>\n"
                    f"✅ <b>Location Verified</b>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Failed to send admin notification: {e}")
        
        # Remove from pending
        del pending_plan_selection[user_id]

@bot.message_handler(func=lambda message: message.reply_to_message is not None and message.from_user.id == ADMIN_ID)
def admin_reply_handler(message):
    """Handle admin replies to user requests with full media support"""
    if message.reply_to_message:
        original = message.reply_to_message.text or message.reply_to_message.caption or ""
        
        # Method 1: Extract ID from order messages (👤 Name, 🆔 ID: format)
        match = re.search(r"🆔 (\d+)", original)
        if not match:
            # Method 2: Try alternative formats
            match = re.search(r"ID: (\d+)", original)
        
        if match:
            user_id = int(match.group(1))
        else:
            bot.reply_to(message, "❌ Could not extract user ID from this message.")
            return
        
        # Don't allow messaging blocked users
        if user_id in blocked_users:
            bot.reply_to(message, "❌ Cannot send message to blocked user.")
            return
        
        # Add user to allowed list
        allowed_users.add(user_id)
        save_json_file("allowed_users.json", list(allowed_users))

        try:
            # Handle text message
            if message.text:
                bot.send_message(user_id, f"📩 Admin: {message.text}")
            
            # Handle different media types
            if message.photo:
                if message.caption:
                    bot.send_photo(user_id, message.photo[-1].file_id, 
                                 caption=f"📩 Admin: {message.caption}")
                else:
                    bot.send_photo(user_id, message.photo[-1].file_id, 
                                 caption="📩 Photo from Admin")
            
            elif message.document:
                if message.caption:
                    bot.send_document(user_id, message.document.file_id, 
                                    caption=f"📩 Admin: {message.caption}")
                else:
                    bot.send_document(user_id, message.document.file_id, 
                                    caption="📩 File from Admin")
            
            elif message.video:
                if message.caption:
                    bot.send_video(user_id, message.video.file_id, 
                                 caption=f"📩 Admin: {message.caption}")
                else:
                    bot.send_video(user_id, message.video.file_id, 
                                 caption="📩 Video from Admin")
            
            elif message.audio:
                bot.send_audio(user_id, message.audio.file_id)
                if message.caption:
                    bot.send_message(user_id, f"📩 Admin: {message.caption}")
            
            elif message.voice:
                bot.send_voice(user_id, message.voice.file_id)
                bot.send_message(user_id, "📩 Voice message from Admin")
            
            elif message.sticker:
                bot.send_sticker(user_id, message.sticker.file_id)
                bot.send_message(user_id, "📩 Sticker from Admin")
            
            elif message.video_note:
                bot.send_video_note(user_id, message.video_note.file_id)
                bot.send_message(user_id, "📩 Video note from Admin")
            
            bot.reply_to(message, f"✅ Message sent successfully to user {user_id}")
            
        except Exception as e:
            bot.reply_to(message, f"❌ Failed to send: {e}")

@bot.message_handler(func=lambda message: message.from_user.id != ADMIN_ID, 
                    content_types=['text', 'photo', 'document', 'video', 'audio', 'voice', 'sticker', 'video_note'])
def user_message_handler(message):
    """Handle user messages and media with full support"""
    user_id = message.from_user.id
    user = message.from_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if not full_name.strip():
        full_name = "Unknown User"
    username = f"@{user.username}" if user.username else "NoUsername"
    
    # Check if user is blocked
    if user_id in blocked_users:
        bot.reply_to(message, "❌ Access denied. You are not eligible to use this service.")
        return
    
    # Handle regular user messages
    if user_id not in allowed_users:
        bot.reply_to(message, "❌ You cannot message first. Please wait for admin reply.")
        return

    try:
        # Create reply markup for admin to easily reply
        reply_markup = types.ForceReply()
        
        # Forward text message
        if message.text:
            bot.send_message(ADMIN_ID,
                f"📨 Message from <b>{full_name}</b> ({username})\n"
                f"🆔 {user_id}\n\n{message.text}",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        # Forward media with details
        elif message.photo:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                         caption=f"📷 Photo from <b>{full_name}</b> ({username})\n"
                                f"🆔 {user_id}\n\n"
                                f"{message.caption or 'No caption'}",
                         parse_mode="HTML",
                         reply_markup=reply_markup)
        
        elif message.document:
            file_info = ""
            if message.document.file_name:
                file_info += f"📄 File: {message.document.file_name}\n"
            if message.document.file_size:
                file_size_mb = round(message.document.file_size / (1024 * 1024), 2)
                file_info += f"📊 Size: {file_size_mb} MB\n"
            
            bot.send_document(ADMIN_ID, message.document.file_id,
                            caption=f"📎 Document from <b>{full_name}</b> ({username})\n"
                                   f"🆔 {user_id}\n"
                                   f"{file_info}"
                                   f"\n{message.caption or 'No caption'}",
                            parse_mode="HTML",
                            reply_markup=reply_markup)
        
        elif message.video:
            bot.send_video(ADMIN_ID, message.video.file_id,
                         caption=f"🎥 Video from <b>{full_name}</b> ({username})\n"
                                f"🆔 {user_id}\n\n"
                                f"{message.caption or 'No caption'}",
                         parse_mode="HTML",
                         reply_markup=reply_markup)
        
        elif message.audio:
            bot.send_audio(ADMIN_ID, message.audio.file_id,
                         caption=f"🎵 Audio from <b>{full_name}</b> ({username})\n"
                                f"🆔 {user_id}\n\n"
                                f"{message.caption or 'No caption'}",
                         parse_mode="HTML",
                         reply_markup=reply_markup)
        
        elif message.voice:
            bot.send_voice(ADMIN_ID, message.voice.file_id,
                         reply_markup=reply_markup)
            bot.send_message(ADMIN_ID,
                f"🎤 Voice message from <b>{full_name}</b> ({username})\n"
                f"🆔 {user_id}",
                parse_mode="HTML")
        
        elif message.sticker:
            bot.send_sticker(ADMIN_ID, message.sticker.file_id,
                           reply_markup=reply_markup)
            bot.send_message(ADMIN_ID,
                f"😀 Sticker from <b>{full_name}</b> ({username})\n"
                f"🆔 {user_id}",
                parse_mode="HTML")
        
        elif message.video_note:
            bot.send_video_note(ADMIN_ID, message.video_note.file_id,
                              reply_markup=reply_markup)
            bot.send_message(ADMIN_ID,
                f"📹 Video note from <b>{full_name}</b> ({username})\n"
                f"🆔 {user_id}",
                parse_mode="HTML")
        
        # Send confirmation to user
        bot.reply_to(message, "✅ Your message/media has been sent to admin.")
        
    except Exception as e:
        logging.error(f"Failed to forward user message/media: {e}")
        bot.reply_to(message, "❌ Failed to send your message. Please try again.")

@bot.message_handler(commands=['reply'])
def admin_quick_reply(message):
    """Quick reply command for admin: /reply user_id message"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Extract user_id and message from command
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, 
                "📝 Usage: /reply <user_id> <message>\n"
                "Example: /reply 123456789 Hello user!")
            return
        
        user_id = int(parts[1])
        reply_text = parts[2]
        
        if user_id in blocked_users:
            bot.reply_to(message, "❌ Cannot reply to blocked user.")
            return
        
        # Send message to user
        bot.send_message(user_id, f"📩 Admin: {reply_text}")
        bot.reply_to(message, f"✅ Reply sent to user {user_id}")
        
        # Add to allowed users
        allowed_users.add(user_id)
        save_json_file("allowed_users.json", list(allowed_users))
        
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID format.")
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to send reply: {e}")

@bot.message_handler(commands=['send'])
def admin_send_media(message):
    """Admin command to send media to specific user"""
    if message.from_user.id != ADMIN_ID:
        return
    
    command_parts = message.text.split(' ', 2)
    if len(command_parts) < 2:
        bot.reply_to(message, 
            "📝 <b>Admin Send Commands:</b>\n\n"
            "📤 <code>/send user_id message</code> - Send text\n"
            "📎 Reply to any media with <code>/send user_id</code>\n"
            "📊 <code>/send broadcast message</code> - Send to all users\n\n"
            "Example: <code>/send 123456789 Hello user!</code>",
            parse_mode="HTML")
        return
    
    try:
        # Handle broadcast
        if command_parts[1].lower() == "broadcast" and len(command_parts) >= 3:
            broadcast_message = command_parts[2]
            success_count = 0
            
            for user_id in allowed_users:
                if user_id not in blocked_users:
                    try:
                        bot.send_message(user_id, f"📢 Broadcast: {broadcast_message}")
                        success_count += 1
                    except:
                        pass
            
            bot.reply_to(message, f"✅ Broadcast sent to {success_count} users.")
            return
        
        target_user_id = int(command_parts[1])
        
        if target_user_id in blocked_users:
            bot.reply_to(message, "❌ Cannot send to blocked user.")
            return
        
        if len(command_parts) >= 3:
            text_message = command_parts[2]
            bot.send_message(target_user_id, f"📩 Admin: {text_message}")
            bot.reply_to(message, f"✅ Message sent to user {target_user_id}")
        else:
            bot.reply_to(message, "❌ Please provide a message to send.")
            
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to send: {e}")

@bot.message_handler(commands=['admin'])
def admin_commands(message):
    """Admin commands for managing users"""
    if message.from_user.id != ADMIN_ID:
        return
    
    command = message.text.split()
    
    if len(command) < 2:
        bot.reply_to(message,
            "🔧 <b>Admin Commands:</b>\n\n"
            "📊 <code>/admin stats</code> - View statistics\n"
            "🔓 <code>/admin unblock user_id</code> - Unblock user\n"
            "🚫 <code>/admin block user_id</code> - Block user\n"
            "📋 <code>/admin blocked</code> - List blocked users\n"
            "👥 <code>/admin users</code> - List allowed users\n"
            "🧹 <code>/admin clear</code> - Clear demo status\n\n"
            "📝 <b>Quick Commands:</b>\n"
            "💬 <code>/reply user_id message</code> - Quick reply\n"
            "📤 <code>/send user_id message</code> - Send message\n"
            "📢 <code>/send broadcast message</code> - Broadcast",
            parse_mode="HTML"
        )
        return
    
    action = command[1].lower()
    
    if action == "stats":
        total_blocked = len(blocked_users)
        total_allowed = len(allowed_users)
        type1_demos = len(user_demo_status["type_1"])
        type2_demos = len(user_demo_status["type_2"])
        
        stats_text = (
            f"📊 <b>Bot Statistics</b>\n\n"
            f"🚫 Blocked Users: {total_blocked}\n"
            f"✅ Allowed Users: {total_allowed}\n"
            f"🔸 Type 1 Demos: {type1_demos}\n"
            f"🔹 Type 2 Demos: {type2_demos}\n"
            f"⏳ Pending State Selection: {len(pending_plan_selection)}"
        )
        bot.reply_to(message, stats_text, parse_mode="HTML")
    
    elif action == "unblock" and len(command) == 3:
        try:
            user_id = int(command[2])
            if user_id in blocked_users:
                blocked_users.remove(user_id)
                save_json_file("blocked_users.json", list(blocked_users))
                bot.reply_to(message, f"✅ User {user_id} unblocked.")
            else:
                bot.reply_to(message, f"❌ User {user_id} is not blocked.")
        except ValueError:
            bot.reply_to(message, "❌ Invalid user ID.")
    
    elif action == "block" and len(command) == 3:
        try:
            user_id = int(command[2])
            blocked_users.add(user_id)
            save_json_file("blocked_users.json", list(blocked_users))
            bot.reply_to(message, f"✅ User {user_id} blocked.")
        except ValueError:
            bot.reply_to(message, "❌ Invalid user ID.")
    
    elif action == "blocked":
        if blocked_users:
            blocked_list = "\n".join([f"• <code>{uid}</code>" for uid in list(blocked_users)[:20]])
            if len(blocked_users) > 20:
                blocked_list += f"\n... and {len(blocked_users) - 20} more"
            bot.reply_to(message, f"🚫 <b>Blocked Users:</b>\n{blocked_list}", parse_mode="HTML")
        else:
            bot.reply_to(message, "✅ No blocked users.")
    
    elif action == "users":
        if allowed_users:
            users_list = "\n".join([f"• <code>{uid}</code>" for uid in list(allowed_users)[:20]])
            if len(allowed_users) > 20:
                users_list += f"\n... and {len(allowed_users) - 20} more"
            bot.reply_to(message, f"👥 <b>Allowed Users:</b>\n{users_list}", parse_mode="HTML")
        else:
            bot.reply_to(message, "❌ No allowed users.")
    
    elif action == "clear":
        user_demo_status["type_1"].clear()
        user_demo_status["type_2"].clear()
        save_json_file("demo_status.json", user_demo_status)
        bot.reply_to(message, "🧹 Demo status cleared for all users.")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask App for health check and Render compatibility
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return {
        "status": "alive",
        "bot": "NMMS MOD Bot",
        "blocked_users": len(blocked_users),
        "allowed_users": len(allowed_users),
        "media_support": "enabled",
        "features": ["admin_reply", "media_files", "broadcast", "quick_commands"]
    }

@web_app.route('/health')
def health():
    return {"status": "healthy", "timestamp": str(asyncio.get_event_loop().time())}

def run_flask():
    """Run Flask app in separate thread"""
    port = int(os.environ.get('PORT', 5000))
    web_app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    """Keep Flask server alive"""
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

def main():
    """Main bot function"""
    try:
        logger.info("🚀 Starting NMMS Bot with full media & reply support...")
        logger.info(f"📊 Loaded {len(blocked_users)} blocked users, {len(allowed_users)} allowed users")
        
        # Start Flask health check server
        keep_alive()
        
        # Start bot
        bot.infinity_polling(none_stop=True, interval=0, timeout=60)
        
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        import time
        time.sleep(10)
        main()

# Entry point
if __name__ == "__main__":
    while True:
        try:
            main()
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"🔄 Restarting due to error: {e}")
            import time
            time.sleep(10)
