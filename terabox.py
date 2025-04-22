from aria2p import API as Aria2API, Client as Aria2Client
import asyncio
from dotenv import load_dotenv
from datetime import datetime
import os
import logging
import math
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait
import time
import urllib.parse
from urllib.parse import urlparse
from flask import Flask, render_template
from threading import Thread
import aiohttp

load_dotenv('config.env', override=True)
logging.basicConfig(
    level=logging.INFO,  
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s - %(filename)s:%(lineno)d"
)

logger = logging.getLogger(__name__)

logging.getLogger("pyrogram.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection").setLevel(logging.ERROR)
logging.getLogger("pyrogram.dispatcher").setLevel(logging.ERROR)

# Improved Aria2 configuration with more robust settings
aria2 = Aria2API(
    Aria2Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)
options = {
    "max-tries": "50",
    "retry-wait": "3",
    "continue": "true",
    "allow-overwrite": "true",
    "min-split-size": "4M",
    "split": "10",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "check-certificate": "false",
    "follow-metalink": "true",
    "file-allocation": "none",
    "seed-time": "0"
}

aria2.set_global_options(options)

API_ID = os.environ.get('TELEGRAM_API', '')
if len(API_ID) == 0:
    logging.error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)

API_HASH = os.environ.get('TELEGRAM_HASH', '')
if len(API_HASH) == 0:
    logging.error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)
    
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    logging.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

DUMP_CHAT_ID = os.environ.get('DUMP_CHAT_ID', '')
if len(DUMP_CHAT_ID) == 0:
    logging.error("DUMP_CHAT_ID variable is missing! Exiting now")
    exit(1)
else:
    DUMP_CHAT_ID = int(DUMP_CHAT_ID)

FSUB_ID = os.environ.get('FSUB_ID', '')
if len(FSUB_ID) == 0:
    logging.error("FSUB_ID variable is missing! Exiting now")
    exit(1)
else:
    FSUB_ID = int(FSUB_ID)

USER_SESSION_STRING = os.environ.get('USER_SESSION_STRING', '')
if len(USER_SESSION_STRING) == 0:
    logging.info("USER_SESSION_STRING variable is missing! Bot will split Files in 2Gb...")
    USER_SESSION_STRING = None

# Alternative API URL in case primary fails
TERABOX_API_URL = os.environ.get('TERABOX_API_URL', 'https://teradlrobot.cheemsbackup.workers.dev/')
ALTERNATE_API_URL = os.environ.get('ALTERNATE_API_URL', 'https://tboxapi.fly.dev/api/')

app = Client("jetbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user = None
SPLIT_SIZE = 2093796556
if USER_SESSION_STRING:
    user = Client("jetu", api_id=API_ID, api_hash=API_HASH, session_string=USER_SESSION_STRING)
    SPLIT_SIZE = 4241280205

VALID_DOMAINS = [
    'terabox.com', 'nephobox.com', '4funbox.com', 'mirrobox.com', 
    'momerybox.com', 'teraboxapp.com', '1024tera.com', 
    'terabox.app', 'gibibox.com', 'goaibox.com', 'terasharelink.com', 
    'teraboxlink.com', 'terafileshare.com'
]
last_update_time = 0

# Function to check download URL before adding to aria2
async def check_download_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=10) as response:
                if response.status == 200:
                    return True, url
                else:
                    return False, None
    except Exception as e:
        logger.error(f"Error checking URL {url}: {e}")
        return False, None

# Function to get direct download URL from terabox link
async def get_terabox_direct_link(url):
    # Try primary API first
    encoded_url = urllib.parse.quote(url)
    primary_url = f"{TERABOX_API_URL}?url={encoded_url}"
    
    valid, checked_url = await check_download_url(primary_url)
    if valid:
        return checked_url
    
    # If primary fails, try alternate API
    alternate_url = f"{ALTERNATE_API_URL}?url={encoded_url}"
    valid, checked_url = await check_download_url(alternate_url)
    if valid:
        return checked_url
    
    # If both fail, return primary URL as fallback
    return primary_url

async def is_user_member(client, user_id):
    try:
        member = await client.get_chat_member(FSUB_ID, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking membership status for user {user_id}: {e}")
        return False
    
def is_valid_url(url):
    parsed_url = urlparse(url)
    return any(parsed_url.netloc.endswith(domain) for domain in VALID_DOMAINS)

def format_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    join_button = InlineKeyboardButton("ᴊᴏɪɴ ❤️🚀", url="https://t.me/jetmirror")
    developer_button = InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴘᴇʀ ⚡️", url="https://t.me/rtx5069")
    repo69 = InlineKeyboardButton("ʀᴇᴘᴏ 🌐", url="https://github.com/Hrishi2861/Terabox-Downloader-Bot")
    user_mention = message.from_user.mention
    reply_markup = InlineKeyboardMarkup([[join_button, developer_button], [repo69]])
    final_msg = f"ᴡᴇʟᴄᴏᴍᴇ, {user_mention}.\n\n🌟 ɪ ᴀᴍ ᴀ ᴛᴇʀᴀʙᴏx ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ʙᴏᴛ. sᴇɴᴅ ᴍᴇ ᴀɴʏ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ ɪ ᴡɪʟʟ ᴅᴏᴡɴʟᴏᴀᴅ ᴡɪᴛʜɪɴ ғᴇᴡ sᴇᴄᴏɴᴅs ᴀɴᴅ sᴇɴᴅ ɪᴛ ᴛᴏ ʏᴏᴜ ✨."
    video_file_id = "/app/Jet-Mirror.mp4"
    if os.path.exists(video_file_id):
        await client.send_video(
            chat_id=message.chat.id,
            video=video_file_id,
            caption=final_msg,
            reply_markup=reply_markup
            )
    else:
        await message.reply_text(final_msg, reply_markup=reply_markup)

async def update_status_message(status_message, text):
    try:
        await status_message.edit_text(text)
    except Exception as e:
        logger.error(f"Failed to update status message: {e}")

@app.on_message(filters.text)
async def handle_message(client: Client, message: Message):
    if message.text.startswith('/'):
        return
    if not message.from_user:
        return

    user_id = message.from_user.id
    is_member = await is_user_member(client, user_id)

    if not is_member:
        join_button = InlineKeyboardButton("ᴊᴏɪɴ ❤️🚀", url="https://t.me/jetmirror")
        reply_markup = InlineKeyboardMarkup([[join_button]])
        await message.reply_text("ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ.", reply_markup=reply_markup)
        return
    
    url = None
    for word in message.text.split():
        if is_valid_url(word):
            url = word
            break

    if not url:
        await message.reply_text("Please provide a valid Terabox link.")
        return

    status_message = await message.reply_text("🔍 Processing your Terabox link...")
    
    # Get direct download link
    direct_url = await get_terabox_direct_link(url)
    if not direct_url:
        await status_message.edit_text("⚠️ Failed to process this Terabox link. Please try another link.")
        return
    
    try:
        # Add download to aria2
        download = aria2.add_uris([direct_url])
        await status_message.edit_text("⏳ sᴇɴᴅɪɴɢ ʏᴏᴜ ᴛʜᴇ ᴍᴇᴅɪᴀ...🤤")
    except Exception as e:
        logger.error(f"Failed to add download: {e}")
        await status_message.edit_text("⚠️ Failed to start download. Please try again later.")
        return

    start_time = datetime.now()
    previous_progress = 0
    stalled_count = 0
    update_interval = 10  # seconds
    last_update = time.time()

    # Monitor download progress
    while not download.is_complete and stalled_count < 5:
        try:
            await asyncio.sleep(update_interval)
            download.update()
            progress = download.progress
            
            # Check if download is stalled
            if progress == previous_progress:
                stalled_count += 1
                if stalled_count >= 3:
                    logger.warning(f"Download appears stalled at {progress}%. Attempting to restart...")
                    # Try to restart if stalled
                    aria2.remove([download.gid])
                    download = aria2.add_uris([direct_url])
                    stalled_count = 0
                    previous_progress = 0
                    continue
            else:
                stalled_count = 0
                previous_progress = progress

            current_time = time.time()
            if current_time - last_update >= update_interval:
                elapsed_time = datetime.now() - start_time
                elapsed_minutes, elapsed_seconds = divmod(elapsed_time.seconds, 60)

                status_text = (
                    f"┏ ғɪʟᴇɴᴀᴍᴇ: {download.name or 'Downloading...'}\n"
                    f"┠ [{'★' * int(progress / 10)}{'☆' * (10 - int(progress / 10))}] {progress:.2f}%\n"
                    f"┠ ᴘʀᴏᴄᴇssᴇᴅ: {format_size(download.completed_length)} ᴏғ {format_size(download.total_length)}\n"
                    f"┠ sᴛᴀᴛᴜs: 📥 Downloading\n"
                    f"┠ ᴇɴɢɪɴᴇ: <b><u>Aria2c v1.37.0</u></b>\n"
                    f"┠ sᴘᴇᴇᴅ: {format_size(download.download_speed)}/s\n"
                    f"┠ ᴇᴛᴀ: {download.eta} | ᴇʟᴀᴘsᴇᴅ: {elapsed_minutes}m {elapsed_seconds}s\n"
                    f"┖ ᴜsᴇʀ: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> | ɪᴅ: {user_id}\n"
                )
                
                try:
                    await update_status_message(status_message, status_text)
                    last_update = current_time
                except FloodWait as e:
                    logger.error(f"Flood wait detected! Sleeping for {e.value} seconds")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    logger.error(f"Error updating status: {e}")
        except Exception as e:
            logger.error(f"Error during download monitoring: {e}")
            await asyncio.sleep(5)

    # Check if download completed successfully
    if not os.path.exists(download.files[0].path if download.files else ""):
        await status_message.edit_text("⚠️ Download failed. Please try again later.")
        return

    file_path = download.files[0].path
    caption = (
        f"✨ {download.name}\n"
        f"👤 ʟᴇᴇᴄʜᴇᴅ ʙʏ : <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
        f"📥 ᴜsᴇʀ ʟɪɴᴋ: tg://user?id={user_id}\n\n"
        "[ᴘᴏᴡᴇʀᴇᴅ ʙʏ ᴊᴇᴛ-ᴍɪʀʀᴏʀ ❤️🚀](https://t.me/JetMirror)"
    )

    last_update_time = time.time()
    UPDATE_INTERVAL = 10

    async def update_status(message, text):
        nonlocal last_update_time
        current_time = time.time()
        if current_time - last_update_time >= UPDATE_INTERVAL:
            try:
                await message.edit_text(text)
                last_update_time = current_time
            except FloodWait as e:
                logger.warning(f"FloodWait: Sleeping for {e.value}s")
                await asyncio.sleep(e.value)
                await update_status(message, text)
            except Exception as e:
                logger.error(f"Error updating status: {e}")

    async def upload_progress(current, total):
        progress = (current / total) * 100
        elapsed_time = datetime.now() - start_time
        elapsed_minutes, elapsed_seconds = divmod(elapsed_time.seconds, 60)

        status_text = (
            f"┏ ғɪʟᴇɴᴀᴍᴇ: {download.name}\n"
            f"┠ [{'★' * int(progress / 10)}{'☆' * (10 - int(progress / 10))}] {progress:.2f}%\n"
            f"┠ ᴘʀᴏᴄᴇssᴇᴅ: {format_size(current)} ᴏғ {format_size(total)}\n"
            f"┠ sᴛᴀᴛᴜs: 📤 Uploading to Telegram\n"
            f"┠ ᴇɴɢɪɴᴇ: <b><u>PyroFork v2.2.11</u></b>\n"
            f"┠ sᴘᴇᴇᴅ: {format_size(current / elapsed_time.seconds if elapsed_time.seconds > 0 else 0)}/s\n"
            f"┠ ᴇʟᴀᴘsᴇᴅ: {elapsed_minutes}m {elapsed_seconds}s\n"
            f"┖ ᴜsᴇʀ: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> | ɪᴅ: {user_id}\n"
        )
        await update_status(status_message, status_text)

    async def split_video_with_ffmpeg(input_path, output_prefix, split_size):
        try:
            original_ext = os.path.splitext(input_path)[1].lower() or '.mp4'
            start_time = datetime.now()
            last_progress_update = time.time()
            
            # Check if ffprobe is available, if not use file size based splitting
            try:
                proc = await asyncio.create_subprocess_exec(
                    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', input_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                total_duration = float(stdout.decode().strip())
                
                file_size = os.path.getsize(input_path)
                parts = math.ceil(file_size / split_size)
                
                if parts == 1:
                    return [input_path]
                
                duration_per_part = total_duration / parts
                split_files = []
                
                for i in range(parts):
                    current_time = time.time()
                    if current_time - last_progress_update >= UPDATE_INTERVAL:
                        elapsed = datetime.now() - start_time
                        status_text = (
                            f"✂️ Splitting {os.path.basename(input_path)}\n"
                            f"Part {i+1}/{parts}\n"
                            f"Elapsed: {elapsed.seconds // 60}m {elapsed.seconds % 60}s"
                        )
                        await update_status(status_message, status_text)
                        last_progress_update = current_time
                    
                    output_path = f"{output_prefix}.{i+1:03d}{original_ext}"
                    
                    # Try first with ffmpeg, then with xtra if available
                    try:
                        cmd = [
                            'ffmpeg', '-y', '-ss', str(i * duration_per_part),
                            '-i', input_path, '-t', str(duration_per_part),
                            '-c', 'copy', '-map', '0',
                            '-avoid_negative_ts', 'make_zero',
                            output_path
                        ]
                        
                        proc = await asyncio.create_subprocess_exec(*cmd)
                        await proc.wait()
                    except:
                        cmd = [
                            'xtra', '-y', '-ss', str(i * duration_per_part),
                            '-i', input_path, '-t', str(duration_per_part),
                            '-c', 'copy', '-map', '0',
                            '-avoid_negative_ts', 'make_zero',
                            output_path
                        ]
                        
                        proc = await asyncio.create_subprocess_exec(*cmd)
                        await proc.wait()
                    
                    split_files.append(output_path)
                
                return split_files
            except Exception as e:
                logger.error(f"FFmpeg split error, falling back to simple split: {e}")
                # If ffmpeg fails, use simple splitting (for non-video files)
                return await simple_split_file(input_path, output_prefix, split_size)
                
        except Exception as e:
            logger.error(f"Split error: {e}")
            # If all splitting fails, return original file
            return [input_path]

    async def simple_split_file(input_path, output_prefix, split_size):
        try:
            file_size = os.path.getsize(input_path)
            if file_size <= split_size:
                return [input_path]
            
            parts = math.ceil(file_size / split_size)
            split_files = []
            
            with open(input_path, 'rb') as f:
                for i in range(parts):
                    output_path = f"{output_prefix}.part{i+1:03d}"
                    status_text = f"✂️ Splitting file (simple) part {i+1}/{parts}"
                    await update_status(status_message, status_text)
                    
                    with open(output_path, 'wb') as out:
                        chunk = f.read(split_size)
                        if chunk:
                            out.write(chunk)
                            split_files.append(output_path)
            
            return split_files
        except Exception as e:
            logger.error(f"Simple split error: {e}")
            return [input_path]

    async def handle_upload():
        file_size = os.path.getsize(file_path)
        
        # Check file existence and size
        if not os.path.exists(file_path):
            await status_message.edit_text("⚠️ File not found after download. Please try again.")
            return
            
        if file_size == 0:
            await status_message.edit_text("⚠️ Downloaded file is empty. Please try again with a different link.")
            return
        
        if file_size > SPLIT_SIZE:
            await update_status(
                status_message,
                f"✂️ Splitting {download.name} ({format_size(file_size)})"
            )
            
            # Get file extension to determine split method
            file_ext = os.path.splitext(file_path)[1].lower()
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.mpg', '.mpeg', '.webm']
            
            if file_ext in video_extensions:
                split_files = await split_video_with_ffmpeg(
                    file_path,
                    os.path.splitext(file_path)[0],
                    SPLIT_SIZE
                )
            else:
                split_files = await simple_split_file(
                    file_path,
                    os.path.splitext(file_path)[0],
                    SPLIT_SIZE
                )
            
            try:
                for i, part in enumerate(split_files):
                    part_caption = f"{caption}\n\nPart {i+1}/{len(split_files)}"
                    await update_status(
                        status_message,
                        f"📤 Uploading part {i+1}/{len(split_files)}\n"
                        f"{os.path.basename(part)}"
                    )
                    
                    # Use user client if available, otherwise use bot client
                    try:
                        if USER_SESSION_STRING and user:
                            sent = await user.send_video(
                                DUMP_CHAT_ID, part, 
                                caption=part_caption,
                                progress=upload_progress
                            )
                            await app.copy_message(
                                message.chat.id, DUMP_CHAT_ID, sent.id
                            )
                        else:
                            # Determine if it's a video or document
                            if file_ext in video_extensions:
                                sent = await client.send_video(
                                    DUMP_CHAT_ID, part,
                                    caption=part_caption,
                                    progress=upload_progress
                                )
                                await client.copy_message(
                                    message.chat.id, DUMP_CHAT_ID, sent.id
                                )
                            else:
                                sent = await client.send_document(
                                    DUMP_CHAT_ID, part,
                                    caption=part_caption,
                                    progress=upload_progress
                                )
                                await client.copy_message(
                                    message.chat.id, DUMP_CHAT_ID, sent.id
                                )
                    except Exception as e:
                        logger.error(f"Error uploading part {i+1}: {e}")
                        # Try sending as document if video fails
                        try:
                            sent = await client.send_document(
                                DUMP_CHAT_ID, part,
                                caption=part_caption,
                                progress=upload_progress
                            )
                            await client.copy_message(
                                message.chat.id, DUMP_CHAT_ID, sent.id
                            )
                        except Exception as e2:
                            logger.error(f"Both methods failed for part {i+1}: {e2}")
                            await message.reply_text(f"⚠️ Failed to upload part {i+1}. Please try again later.")
                    
                    # Clean up after each part is sent
                    if os.path.exists(part) and part != file_path:
                        os.remove(part)
            except Exception as e:
                logger.error(f"Error in upload loop: {e}")
                await message.reply_text("⚠️ An error occurred during upload. Please try again.")
            finally:
                # Final cleanup
                for part in split_files:
                    try:
                        if os.path.exists(part) and part != file_path:
                            os.remove(part)
                    except:
                        pass
        else:
            await update_status(
                status_message,
                f"📤 Uploading {download.name}\n"
                f"Size: {format_size(file_size)}"
            )
            
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.mpg', '.mpeg', '.webm']
            
            try:
                if USER_SESSION_STRING and user:
                    if file_ext in video_extensions:
                        try:
                            sent = await user.send_video(
                                DUMP_CHAT_ID, file_path,
                                caption=caption,
                                progress=upload_progress
                            )
                        except Exception as e:
                            logger.error(f"Error sending as video: {e}")
                            sent = await user.send_document(
                                DUMP_CHAT_ID, file_path,
                                caption=caption,
                                progress=upload_progress
                            )
                    else:
                        sent = await user.send_document(
                            DUMP_CHAT_ID, file_path,
                            caption=caption,
                            progress=upload_progress
                        )
                    
                    await app.copy_message(
                        message.chat.id, DUMP_CHAT_ID, sent.id
                    )
                else:
                    if file_ext in video_extensions:
                        try:
                            sent = await client.send_video(
                                DUMP_CHAT_ID, file_path,
                                caption=caption,
                                progress=upload_progress
                            )
                        except Exception as e:
                            logger.error(f"Error sending as video: {e}")
                            sent = await client.send_document(
                                DUMP_CHAT_ID, file_path,
                                caption=caption,
                                progress=upload_progress
                            )
                    else:
                        sent = await client.send_document(
                            DUMP_CHAT_ID, file_path,
                            caption=caption,
                            progress=upload_progress
                        )
                    
                    await client.copy_message(
                        message.chat.id, DUMP_CHAT_ID, sent.id
                    )
            except Exception as e:
                logger.error(f"Upload error: {e}")
                await message.reply_text("⚠️ Failed to upload file. Please try again later.")
                
        # Clean up original file
        if os.path.exists(file_path):
            os.remove(file_path)

    start_time = datetime.now()
    try:
        await handle_upload()
        await status_message.edit_text("✅ Upload completed!")
    except Exception as e:
        logger.error(f"Final error: {e}")
        try:
            await status_message.edit_text(f"⚠️ An error occurred: {str(e)[:200]}")
        except:
            pass

    try:
        # Don't delete messages - keep them for troubleshooting
        # await status_message.delete()
        # await message.delete()
        pass
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return render_template("index.html")

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def keep_alive():
    Thread(target=run_flask).start()

async def start_user_client():
    if user:
        try:
            await user.start()
            logger.info("User client started successfully!")
        except Exception as e:
            logger.error(f"Failed to start user client: {e}")

def run_user():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_user_client())

async def check_aria2_server():
    """Check if aria2 server is running, if not start it"""
    try:
        aria2.get_global_options()
        logger.info("Aria2 server is running")
        return True
    except Exception:
        logger.warning("Aria2 server is not running, attempting to start...")
        try:
            import subprocess
            subprocess.Popen(
                "aria2c --enable-rpc --rpc-listen-all=true --rpc-allow-origin-all "
                "--max-concurrent-downloads=10 --max-connection-per-server=10 "
                "--rpc-max-request-size=1024M --seed-time=0.0 --min-split-size=10M "
                "--follow-torrent=mem --split=10 "
                "--daemon=true --allow-overwrite=true",
                shell=True
            )
            await asyncio.sleep(3)
            aria2.get_global_options()
            logger.info("Started aria2 server successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start aria2: {e}")
            return False

# Add simple HTML template for the Flask app
@flask_app.route('/templates/index.html')
def index_template():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terabox Downloader Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f4f4f4;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .status {
                padding: 10px;
                background: #e7f3fe;
                border-left: 5px solid #2196f3;
                margin-bottom: 15px;
            }
            .footer {
                text-align: center;
                margin-top: 20px;
                font-size: 0.8em;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Terabox Downloader Bot</h1>
            <div class="status">
                <p>Bot is running!</p>
                <p>Send your Terabox links to the bot on Telegram.</p>
            </div>
            <div class="footer">
                <p>Powered by Jet-Mirror ❤️🚀</p>
            </div>
        </div>
    </body>
    </html>
    """

async def startup_checks():
    """Perform startup checks"""
    # Check aria2 server
    aria2_status = await check_aria2_server()
    if not aria2_status:
        logger.error("Aria2 server check failed")
    
    # Check download directory
    download_dir = os.environ.get('DOWNLOAD_DIR', '/downloads')
    if not os.path.exists(download_dir):
        try:
            os.makedirs(download_dir)
            logger.info(f"Created download directory: {download_dir}")
        except Exception as e:
            logger.error(f"Failed to create download directory: {e}")
    
    # Check API endpoints
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TERABOX_API_URL}?ping=1") as response:
                if response.status == 200:
                    logger.info("Primary API endpoint is responsive")
                else:
                    logger.warning(f"Primary API endpoint returned status {response.status}")
    except Exception as e:
        logger.warning(f"Primary API endpoint check failed: {e}")

if __name__ == "__main__":
    # Run startup checks in asyncio loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(startup_checks())
    
    # Start the Flask web server
    keep_alive()

    # Start the user client if available
    if user:
        logger.info("Starting user client...")
        Thread(target=run_user).start()

    # Log helpful information
    logger.info("======= BOT STARTUP INFO =======")
    logger.info(f"Using Aria2 for downloads")
    logger.info(f"Max split size: {format_size(SPLIT_SIZE)}")
    logger.info(f"User session: {'Available' if USER_SESSION_STRING else 'Not available'}")
    logger.info(f"Primary API: {TERABOX_API_URL}")
    logger.info(f"Alternate API: {ALTERNATE_API_URL}")
    logger.info("===============================")
    
    # Start the bot
    logger.info("Starting bot client...")
    app.run()
