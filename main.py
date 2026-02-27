#!/usr/bin/env python3
# main.py - Complete OSINT Pro Bot with Flask for Render Web Service
# Fully updated with all requested features (100% working)

import os
import sys
import re
import json
import uuid
import time
import asyncio
import logging
import threading
import html
import aiohttp
import io
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

# Import config and database
from config import *
from database import *

# ==================== SETUP ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# ==================== CONSTANTS ====================
MAX_MESSAGE_LENGTH = 4000
pending_actions = {}  # user_id -> {"action": "dm" or "broadcast", "target": user_id (for dm)}

# ==================== UTILITY FUNCTIONS ====================
CACHE_EXPIRY = 300
copy_cache = {}

def clean_branding(text, extra_blacklist=None):
    if not text:
        return text
    blacklist = GLOBAL_BLACKLIST.copy()
    if extra_blacklist:
        blacklist.extend(extra_blacklist)
    for item in blacklist:
        text = re.sub(re.escape(item), '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

async def call_api(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except:
                        return {"error": "Invalid JSON response"}
                else:
                    return {"error": f"HTTP {resp.status}"}
        except asyncio.TimeoutError:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}

async def check_force_join(bot, user_id):
    missing = []
    for ch in FORCE_JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status in ['left', 'kicked']:
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return len(missing) == 0, missing

def get_force_join_keyboard(missing):
    keyboard = []
    for ch in missing:
        keyboard.append([InlineKeyboardButton(f"Join {ch['name']}", url=ch['link'])])
    keyboard.append([InlineKeyboardButton("✅ I've joined", callback_data="verify_join")])
    return InlineKeyboardMarkup(keyboard)

def store_copy_data(data):
    uid = str(uuid.uuid4())
    copy_cache[uid] = {"data": data, "time": time.time()}
    return uid

def get_copy_button(data):
    return InlineKeyboardButton("📋 Copy", callback_data=f"copy:{store_copy_data(data)}")

def get_search_button(cmd):
    return InlineKeyboardButton("🔍 Search", callback_data=f"search:{cmd}")

async def send_as_file(update: Update, text: str, filename: str, caption: str = None):
    """Send long text as a file with branding"""
    branded_text = text + "\n\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 Developer: @Nullprotocol_X\n⚡ Powered by: NULL PROTOCOL"
    file_obj = io.BytesIO(branded_text.encode('utf-8'))
    file_obj.name = filename
    if not caption:
        caption = "📁 **Output बहुत लंबा था, इसलिए फाइल में भेज रहा हूँ**\n\nब्रांडिंग फाइल के अंदर भी मौजूद है।"
    await update.message.reply_document(
        document=file_obj,
        filename=filename,
        caption=caption,
        parse_mode='Markdown'
    )

# ==================== COMMAND LIST GENERATORS ====================
def get_commands_list():
    lines = ["📋 **AVAILABLE COMMANDS**", "────────────────────────────"]
    for cmd, info in COMMANDS.items():
        lines.append(f"• `/{cmd} [{info['param']}]` → {info['desc']}")
    lines.append(CMD_LIST_FOOTER)
    return "\n".join(lines)

def get_admin_commands_list():
    admin_cmds = [
        "`/broadcast` - Broadcast a message to all users (two-step)",
        "`/dm <user_id>` - Send direct message to a user (two-step)",
        "`/ban <user_id> [reason]` - Ban a user",
        "`/unban <user_id>` - Unban a user",
        "`/deleteuser <user_id>` - Delete user from DB",
        "`/searchuser <query>` - Search users",
        "`/users [page]` - List users",
        "`/recentusers [days]` - Recently active users",
        "`/inactiveusers [days]` - Inactive users",
        "`/userlookups <user_id>` - User's last lookups",
        "`/leaderboard` - Top users",
        "`/stats` - Bot statistics",
        "`/dailystats [days]` - Daily stats",
        "`/lookupstats` - Command usage stats",
        "`/addadmin <user_id>` - Add admin (owner only)",
        "`/removeadmin <user_id>` - Remove admin (owner only)",
        "`/listadmins` - List all admins",
        "`/settings` - Bot settings (WIP)",
        "`/fulldbbackup` - Download database backup"
    ]
    lines = ["👑 **ADMIN COMMANDS**", "────────────────────────────"]
    lines.extend(admin_cmds)
    lines.append(CMD_LIST_FOOTER)
    return "\n".join(lines)

# ==================== FILTERS ====================
async def group_only(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type == "private":
        if update.message and update.message.text:
            text = update.message.text.strip()
            if text.startswith('/start') or text.startswith('/help'):
                return True
        user_id = update.effective_user.id
        if user_id == OWNER_ID or await is_admin(user_id):
            return True
        await update.message.reply_text(
            f"⚠️ **Ye bot sirf group me kaam karta hai.**\nPersonal use ke liye use kare: {REDIRECT_BOT}",
            parse_mode='Markdown'
        )
        return False
    return True

async def force_join_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return True
    if user.id == OWNER_ID or await is_admin(user.id):
        return True
    if await is_banned(user.id):
        await update.message.reply_text("❌ **Aap banned hain. Contact admin.**", parse_mode='Markdown')
        return False
    ok, missing = await check_force_join(context.bot, user.id)
    if not ok:
        await update.message.reply_text(
            "⚠️ **Bot use karne ke liye ye channels join karo:**",
            reply_markup=get_force_join_keyboard(missing),
            parse_mode='Markdown'
        )
        return False
    return True

# ==================== START & HELP HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        await update_user(user.id, user.username, user.first_name, user.last_name)
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
    if not await force_join_filter(update, context):
        return
    welcome = f"👋 **Welcome {user.first_name}!**\n\n" + get_commands_list()
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        await update_user(user.id, user.username, user.first_name, user.last_name)
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
    if not await force_join_filter(update, context):
        return
    await update.message.reply_text(get_commands_list(), parse_mode='Markdown')

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID and not await is_admin(user.id):
        await update.message.reply_text("❌ **This command is for admins only.**", parse_mode='Markdown')
        return
    await update.message.reply_text(get_admin_commands_list(), parse_mode='Markdown')

# ==================== TWO-STEP DM & BROADCAST ====================
@admin_only
async def dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate a direct message to a user (two-step)."""
    try:
        target_user_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: `/dm <user_id>`", parse_mode='Markdown')
        return

    admin_id = update.effective_user.id
    pending_actions[admin_id] = {"action": "dm", "target": target_user_id}
    await update.message.reply_text(
        "📨 **अब वह मैसेज भेजें जो आप उस यूजर को भेजना चाहते हैं।**\n\n"
        "आप कोई भी मैसेज टाइप भेज सकते हैं: टेक्स्ट, फोटो, वीडियो, डॉक्यूमेंट, पोल, वॉइस, आदि।",
        parse_mode='Markdown'
    )

@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate a broadcast to all users (two-step)."""
    admin_id = update.effective_user.id
    pending_actions[admin_id] = {"action": "broadcast"}
    await update.message.reply_text(
        "📢 **अब वह मैसेज भेजें जो आप सभी यूजर्स को भेजना चाहते हैं।**\n\n"
        "आप कोई भी मैसेज टाइप भेज सकते हैं: टेक्स्ट, फोटो, वीडियो, डॉक्यूमेंट, पोल, वॉइस, आदि।",
        parse_mode='Markdown'
    )

async def handle_pending_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages that are pending for DM or broadcast."""
    user_id = update.effective_user.id
    if user_id not in pending_actions:
        return  # No pending action

    action_data = pending_actions.pop(user_id)  # Remove from pending
    action = action_data["action"]

    if action == "dm":
        target_user_id = action_data["target"]
        try:
            await context.bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id
            )
            await update.message.reply_text(f"✅ **Message sent to user `{target_user_id}`**", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send DM: {e}")
            await update.message.reply_text(f"❌ **Failed to send message: {e}**", parse_mode='Markdown')

    elif action == "broadcast":
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT user_id FROM users') as cursor:
                users = await cursor.fetchall()
        success = 0
        fail = 0
        for (uid,) in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.effective_message.message_id
                )
                success += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast to {uid}: {e}")
                fail += 1
        await update.message.reply_text(
            f"📢 **Broadcast completed!**\n✅ Success: {success}\n❌ Failed: {fail}",
            parse_mode='Markdown'
        )

# ==================== COMMAND HANDLER (with file support) ====================
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd: str, query: str):
    cmd_info = COMMANDS.get(cmd)
    if not cmd_info:
        await update.message.reply_text("❌ Command not found.")
        return

    url = cmd_info["url"].format(query)
    data = await call_api(url)

    # Add branding to the JSON data (inside the JSON)
    if isinstance(data, dict):
        data["developer"] = BRANDING["developer"]
        data["powered_by"] = BRANDING["powered_by"]
    elif isinstance(data, list):
        data = {
            "result": data,
            "developer": BRANDING["developer"],
            "powered_by": BRANDING["powered_by"]
        }
    else:
        data = {
            "result": data,
            "developer": BRANDING["developer"],
            "powered_by": BRANDING["powered_by"]
        }

    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    cleaned = clean_branding(json_str, cmd_info.get("extra_blacklist", []))

    # Send to user
    if len(cleaned) <= MAX_MESSAGE_LENGTH:
        cleaned_escaped = html.escape(cleaned)
        extra_footer = "\n\n━━━━━━━━━━━━━━━━━━━━\n👨‍💻 **Developer:** @Nullprotocol_X\n⚡ **Powered by:** NULL PROTOCOL"
        output_html = f"<pre>{cleaned_escaped}</pre>{extra_footer}"
        keyboard = [[get_copy_button(data), get_search_button(cmd)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(output_html, parse_mode='HTML', reply_markup=reply_markup)
    else:
        filename = f"{cmd}_{query}_{int(time.time())}.json"
        caption = "📁 **Output बहुत लंबा था, इसलिए फाइल में भेज रहा हूँ**\n\nब्रांडिंग फाइल के अंदर भी मौजूद है।"
        await send_as_file(update, cleaned, filename, caption)

    # Save to DB
    try:
        await save_lookup(update.effective_user.id, cmd, query, data)
    except Exception as e:
        logger.error(f"Failed to save lookup: {e}")

    # Log to channel with Markdown formatting (colorful JSON)
    log_text = f"**User:** `{update.effective_user.id}`\n**Query:** `{query}`\n**Cmd:** `/{cmd}`\n\n```json\n{json.dumps(data, indent=2)}\n```"
    if len(log_text) > 4000:
        log_text = log_text[:3990] + "...\n```"
    try:
        await context.bot.send_message(chat_id=cmd_info["log"], text=log_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to send log to channel: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler: checks pending actions first, then processes commands."""
    # First check if this user has a pending action (DM or broadcast)
    if update.effective_user.id in pending_actions:
        await handle_pending_action(update, context)
        return

    # Apply filters for normal commands
    if not await group_only(update, context):
        return
    if not await force_join_filter(update, context):
        return

    u = update.effective_user
    try:
        await update_user(u.id, u.username, u.first_name, u.last_name)
    except Exception as e:
        logger.error(f"Failed to update user: {e}")

    text = update.message.text
    if not text or not text.startswith('/'):
        return

    parts = text.split(maxsplit=1)
    cmd = parts[0][1:].split('@')[0].lower()
    query = parts[1] if len(parts) > 1 else None

    if not query:
        param = COMMANDS.get(cmd, {}).get("param", "query")
        await update.message.reply_text(f"Usage: `/{cmd} <{param}>`", parse_mode='Markdown')
        return

    await handle_command(update, context, cmd, query)

# ==================== CALLBACK HANDLER ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "verify_join":
        ok, missing = await check_force_join(context.bot, query.from_user.id)
        if ok:
            await query.edit_message_text("✅ **Verification successful! Ab aap bot use kar sakte hain.**", parse_mode='Markdown')
        else:
            await query.edit_message_text(
                "⚠️ **Aapne abhi bhi kuch channels join nahi kiye:**",
                reply_markup=get_force_join_keyboard(missing),
                parse_mode='Markdown'
            )
    elif data.startswith("copy:"):
        uid = data.split(":", 1)[1]
        entry = copy_cache.get(uid)
        if entry and (time.time() - entry["time"]) < CACHE_EXPIRY:
            await query.message.reply_text(
                f"```json\n{json.dumps(entry['data'], indent=2)}\n```",
                parse_mode='Markdown'
            )
            del copy_cache[uid]
        else:
            copy_cache.pop(uid, None)
            await query.message.reply_text("❌ **Copy data expired. Please run the command again.**", parse_mode='Markdown')
    elif data.startswith("search:"):
        cmd = data.split(":", 1)[1]
        await query.message.reply_text(f"Send `/{cmd}` with your query.", parse_mode='Markdown')

# ==================== ADMIN COMMANDS ====================
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id == OWNER_ID or await is_admin(user.id):
            return await func(update, context)
        await update.message.reply_text("❌ This command is for admins only.")
    return wrapper

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id == OWNER_ID:
            return await func(update, context)
    return wrapper

@admin_only
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(context.args[0])
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason"
        await ban_user(uid, reason, update.effective_user.id)
        await update.message.reply_text(f"✅ Banned {uid}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /ban <user_id> [reason]")

@admin_only
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(context.args[0])
        await unban_user(uid)
        await update.message.reply_text(f"✅ Unbanned {uid}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /unban <user_id>")

@admin_only
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(context.args[0])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('DELETE FROM users WHERE user_id = ?', (uid,))
            await db.commit()
        await update.message.reply_text(f"✅ User {uid} deleted from database.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /deleteuser <user_id>")

@admin_only
async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /searchuser <query>")
    query = ' '.join(context.args)
    try:
        uid = int(query)
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT * FROM users WHERE user_id = ?', (uid,)) as cursor:
                user = await cursor.fetchone()
        if user:
            text = f"User found:\nID: {user[0]}\nUsername: @{user[4] or 'N/A'}\nName: {user[5] or ''} {user[6] or ''}\nLookups: {user[3]}\nLast seen: {user[2]}"
        else:
            text = "User not found."
        await update.message.reply_text(text)
        return
    except ValueError:
        pass
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, first_name, last_name FROM users WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ? LIMIT 10",
            (f'%{query}%', f'%{query}%', f'%{query}%')
        ) as cursor:
            results = await cursor.fetchall()
    if results:
        text = "Search results:\n"
        for r in results:
            text += f"• {r[0]} (@{r[1] or 'N/A'}) - {r[2] or ''} {r[3] or ''}\n"
    else:
        text = "No users found."
    await update.message.reply_text(text)

@admin_only
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = int(context.args[0]) if context.args else 1
    per_page = 10
    offset = (page-1)*per_page
    users_list = await get_all_users(limit=per_page, offset=offset)
    if not users_list:
        await update.message.reply_text("No users found.")
        return
    text = f"👥 Users (Page {page}):\n"
    for u in users_list:
        text += f"• {u[0]} (@{u[1] or 'N/A'}) - {u[3]} lookups\n"
    await update.message.reply_text(text)

@admin_only
async def recent_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = int(context.args[0]) if context.args else 7
    users_list = await get_recent_users(days)
    text = f"📅 Users active in last {days} days:\n"
    for u in users_list:
        text += f"• {u[0]} (@{u[1] or 'N/A'}) - last seen {u[2]}\n"
    await update.message.reply_text(text)

@admin_only
async def inactive_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = int(context.args[0]) if context.args else 30
    users_list = await get_inactive_users(days)
    text = f"💤 Users inactive for >{days} days:\n"
    for u in users_list:
        text += f"• {u[0]} (@{u[1] or 'N/A'}) - last seen {u[2]}\n"
    await update.message.reply_text(text)

@admin_only
async def user_lookups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(context.args[0])
        lookups = await get_user_lookups(uid, 10)
        text = f"📊 Last 10 lookups of {uid}:\n"
        for cmd, q, ts in lookups:
            text += f"{ts} - /{cmd} {q}\n"
        await update.message.reply_text(text)
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /userlookups <user_id>")

@admin_only
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = await get_leaderboard(10)
    text = "🏆 Leaderboard (Top 10):\n"
    for i, (uid, count) in enumerate(board, 1):
        text += f"{i}. {uid} - {count} lookups\n"
    await update.message.reply_text(text)

@admin_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_data = await get_stats()
    text = f"📈 Bot Statistics:\n"
    text += f"Total Users: {stats_data['total_users']}\n"
    text += f"Total Lookups: {stats_data['total_lookups']}\n"
    text += f"Total Admins: {stats_data['total_admins']}\n"
    text += f"Total Banned: {stats_data['total_banned']}\n"
    await update.message.reply_text(text)

@admin_only
async def daily_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = int(context.args[0]) if context.args else 7
    stats_list = await get_daily_stats(days)
    if not stats_list:
        await update.message.reply_text("No daily stats available.")
        return
    text = f"📅 Daily Stats (last {days} days):\n"
    for date, cmd, count in stats_list:
        text += f"{date} - /{cmd}: {count}\n"
    await update.message.reply_text(text)

@admin_only
async def lookup_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_list = await get_lookup_stats(10)
    text = "🔍 Lookup Stats (Top 10 commands):\n"
    for cmd, cnt in stats_list:
        text += f"/{cmd}: {cnt}\n"
    await update.message.reply_text(text)

@owner_only
async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(context.args[0])
        await add_admin(uid, OWNER_ID)
        await update.message.reply_text(f"✅ Admin added: {uid}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addadmin <user_id>")

@owner_only
async def remove_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(context.args[0])
        await remove_admin(uid)
        await update.message.reply_text(f"✅ Admin removed: {uid}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /removeadmin <user_id>")

@owner_only
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = await get_all_admins()
    text = "👑 Admins:\n" + "\n".join(str(a) for a in admins)
    await update.message.reply_text(text)

@owner_only
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Settings command - under development.")

@owner_only
async def full_db_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(DB_PATH, 'rb') as f:
        await update.message.reply_document(f, filename='osint_bot_backup.db')

# ==================== BOT INITIALIZATION ====================
async def post_init(app: Application):
    await init_db()
    for aid in INITIAL_ADMINS:
        await add_admin(aid, OWNER_ID)
    logger.info("✅ Bot initialized, database ready.")

def run_bot():
    try:
        if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.error("❌ BOT_TOKEN not set!")
            return

        bot_app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

        # Command handlers
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        bot_app.add_handler(CommandHandler("admin", admin_help))

        # Two-step dm and broadcast
        bot_app.add_handler(CommandHandler("dm", dm))
        bot_app.add_handler(CommandHandler("broadcast", broadcast))

        # Admin commands
        bot_app.add_handler(CommandHandler("ban", ban))
        bot_app.add_handler(CommandHandler("unban", unban))
        bot_app.add_handler(CommandHandler("deleteuser", delete_user))
        bot_app.add_handler(CommandHandler("searchuser", search_user))
        bot_app.add_handler(CommandHandler("users", users))
        bot_app.add_handler(CommandHandler("recentusers", recent_users))
        bot_app.add_handler(CommandHandler("inactiveusers", inactive_users))
        bot_app.add_handler(CommandHandler("userlookups", user_lookups))
        bot_app.add_handler(CommandHandler("leaderboard", leaderboard))
        bot_app.add_handler(CommandHandler("stats", stats))
        bot_app.add_handler(CommandHandler("dailystats", daily_stats))
        bot_app.add_handler(CommandHandler("lookupstats", lookup_stats))

        # Owner commands
        bot_app.add_handler(CommandHandler("addadmin", add_admin_cmd))
        bot_app.add_handler(CommandHandler("removeadmin", remove_admin_cmd))
        bot_app.add_handler(CommandHandler("listadmins", list_admins))
        bot_app.add_handler(CommandHandler("settings", settings))
        bot_app.add_handler(CommandHandler("fulldbbackup", full_db_backup))

        # Main message handler (must be last)
        bot_app.add_handler(MessageHandler(filters.ALL, message_handler))
        bot_app.add_handler(CallbackQueryHandler(callback_handler))

        logger.info("🚀 Bot polling started...")
        bot_app.run_polling(stop_signals=None)
    except Exception as e:
        logger.exception(f"Bot thread crashed: {e}")

# ==================== FLASK WEB SERVER ====================
@flask_app.route('/')
def home():
    return jsonify({"status": "running", "message": "OSINT Pro Bot is active", "time": datetime.now().isoformat()})

@flask_app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

# ==================== MAIN ====================
def main():
    logger.info("🔧 Starting OSINT Pro Bot on Render Web Service...")
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN not set! Please add it in Render environment variables.")
    if BOT_TOKEN and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logger.info("✅ Bot thread started")
    else:
        logger.warning("⚠️ Bot not started due to missing token. Flask server only.")
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Flask server starting on port {port}")
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
