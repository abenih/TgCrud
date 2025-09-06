from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from src.auth import create_user, get_user_by_telegram_id, verify_pattern_lock
from src.notes import create_note, get_user_notes, get_note_by_id, update_note, delete_note
import src.config as config

# Store user states for conversation flow
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and set admin if not already set"""
    user = await get_user_by_telegram_id(str(update.effective_user.id))

    # Set admin if not yet assigned
    if config.ADMIN_ID is None:
        config.ADMIN_ID = update.effective_user.id
        await update.message.reply_text("You are now set as the admin.")
    elif user and user.is_locked:
        await update.message.reply_text("Device locked. Please use the Swipe to Unlock button.",
                                        reply_markup=get_unlock_keyboard())
    else:
        await update.message.reply_text("Welcome back!")

    # Continue with normal start logic
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        user = await create_user(telegram_id, username)
    
    if not user.pattern_lock:
        # First time user - need to set pattern lock
        await show_pattern_setup(update, context, user)
    elif user.is_locked:
        # User is locked - show pattern lock screen
        await show_pattern_lock(update, context, user)
    else:
        # User is unlocked - show main menu
        await show_main_menu(update, context, user)

async def show_pattern_setup(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show pattern setup screen for first-time users"""
    print(f"DEBUG: Showing pattern setup for user {user.username}")
    keyboard = [
        [InlineKeyboardButton("1", callback_data="pattern_1"),
         InlineKeyboardButton("2", callback_data="pattern_2"),
         InlineKeyboardButton("3", callback_data="pattern_3")],
        [InlineKeyboardButton("4", callback_data="pattern_4"),
         InlineKeyboardButton("5", callback_data="pattern_5"),
         InlineKeyboardButton("6", callback_data="pattern_6")],
        [InlineKeyboardButton("7", callback_data="pattern_7"),
         InlineKeyboardButton("8", callback_data="pattern_8"),
         InlineKeyboardButton("9", callback_data="pattern_9")],
        [InlineKeyboardButton("🔒 Set Pattern", callback_data="set_pattern")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📱 Welcome to NotePad!\n\n"
        "🔐 First, set your pattern lock:\n"
        "• Tap the numbers in your desired pattern\n"
        "• Then tap 'Set Pattern' to confirm\n\n"
        "Current pattern: " + context.user_data.get('temp_pattern', ''),
        reply_markup=reply_markup
    )
    
    # Store user state
    user_states[user.id] = "setting_pattern"
    context.user_data['temp_pattern'] = ""
    print(f"DEBUG: Pattern setup displayed, user state set to 'setting_pattern'")

async def show_pattern_lock(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show pattern lock screen for locked users"""
    keyboard = [
        [InlineKeyboardButton("🔓 Unlock", callback_data="unlock_pattern")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📱 NotePad is locked\n\n"
        "🔐 Enter your pattern to unlock:\n\n"
        "Current pattern: " + context.user_data.get('temp_pattern', ''),
        reply_markup=reply_markup
    )
    
    # Store user state
    user_states[user.id] = "unlocking"
    context.user_data['temp_pattern'] = ""

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show main menu when user is unlocked"""
    keyboard = [
        [InlineKeyboardButton("📝 New Note", callback_data="new_note")],
        [InlineKeyboardButton("📚 My Notes", callback_data="list_notes")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("🔒 Lock", callback_data="lock_device")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Check if this is a callback query or message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📱 NotePad - Main Menu\n\n"
            "Welcome back, " + user.username + "!\n"
            "What would you like to do?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📱 NotePad - Main Menu\n\n"
            "Welcome back, " + user.username + "!\n"
            "What would you like to do?",
            reply_markup=reply_markup
        )

async def handle_pattern_setup(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Handle pattern setup button presses"""
    query = update.callback_query
    print(f"DEBUG: Pattern setup called with: {query.data}")
    await query.answer()
    
    if query.data.startswith("pattern_"):
        number = query.data.split("_")[1]
        current_pattern = context.user_data.get('temp_pattern', "")
        if number not in current_pattern:
            context.user_data['temp_pattern'] = current_pattern + number
            await query.edit_message_text(
                "📱 Welcome to NotePad!\n\n"
                "🔐 First, set your pattern lock:\n"
                "• Tap the numbers in your desired pattern\n"
                "• Then tap 'Set Pattern' to confirm\n\n"
                "Current pattern: " + context.user_data['temp_pattern'],
                reply_markup=query.message.reply_markup
            )
    
    elif query.data == "set_pattern":
        pattern = context.user_data.get('temp_pattern', "")
        if len(pattern) >= 4:
            await query.edit_message_text("✅ Pattern lock set successfully!")
            await show_main_menu(update, context, user)
        else:
            await query.answer("❌ Pattern must be at least 4 digits!")

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Handle main menu button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "new_note":
        await show_new_note_form(update, context, user)
    elif query.data == "list_notes":
        await show_user_notes(update, context, user)
    elif query.data == "settings":
        await show_settings(update, context, user)
    elif query.data == "lock_device":
        await query.edit_message_text("🔒 Device locked!")
        await show_pattern_lock(update, context, user)

async def show_new_note_form(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show form to create a new note"""
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "📝 Create New Note\n\n"
        "Please send your note in this format:\n"
        "Title: [Your title here]\n"
        "Content: [Your note content here]\n\n"
        "Or send 'cancel' to go back.",
        reply_markup=reply_markup
    )
    
    user_states[user.id] = "creating_note"

async def show_user_notes(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show list of user's notes"""
    notes = await get_user_notes(user.id)
    
    if not notes:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "📚 My Notes\n\n"
            "You don't have any notes yet.\n"
            "Create your first note!",
            reply_markup=reply_markup
        )
        return
    
    text = "📚 My Notes:\n\n"
    keyboard = []
    
    for note in notes:
        text += f"📝 {note.title}\n"
        text += f"   {note.content[:50]}{'...' if len(note.content) > 50 else ''}\n"
        text += f"   📅 {note.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"📖 {note.title}", callback_data=f"view_note_{note.id}"),
            InlineKeyboardButton(f"✏️ Edit", callback_data=f"edit_note_{note.id}"),
            InlineKeyboardButton(f"🗑️ Delete", callback_data=f"delete_note_{note.id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show settings menu"""
    keyboard = [
        [InlineKeyboardButton("🔐 Change Pattern", callback_data="change_pattern")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "⚙️ Settings\n\n"
        "Manage your NotePad settings:",
        reply_markup=reply_markup
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for note creation"""
    telegram_id = str(update.effective_user.id)
    user = await get_user_by_telegram_id(telegram_id)
    
    if not user or user.id not in user_states:
        return
    
    if user_states[user.id] == "creating_note":
        text = update.message.text
        
        if text.lower() == "cancel":
            user_states.pop(user.id, None)
            await update.message.reply_text("❌ Note creation cancelled.")
            return
        
        # Simple parsing for title and content
        if "title:" in text.lower() and "content:" in text.lower():
            try:
                title_part = text.split("title:")[1].split("content:")[0].strip()
                content_part = text.split("content:")[1].strip()
                
                if title_part and content_part:
                    note = await create_note(user.id, title_part, content_part)
                    user_states.pop(user.id, None)
                    await update.message.reply_text(
                        f"✅ Note created successfully!\n\n"
                        f"📝 Title: {note.title}\n"
                        f"📄 Content: {note.content[:100]}{'...' if len(note.content) > 100 else ''}"
                    )
                else:
                    await update.message.reply_text("❌ Please provide both title and content.")
            except:
                await update.message.reply_text("❌ Invalid format. Please use:\nTitle: [title]\nContent: [content]")
        else:
            await update.message.reply_text("❌ Please use the format:\nTitle: [title]\nContent: [content]")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    print("DEBUG: handle_callback_query function called!")
    query = update.callback_query
    print(f"DEBUG: Received callback: {query.data}")
    telegram_id = str(query.from_user.id)
    user = await get_user_by_telegram_id(telegram_id)
    
    if not user:
        await query.answer("❌ User not found!")
        return
    
    # Handle different callback types
    if query.data.startswith("pattern_"):
        await handle_pattern_setup(update, context, user)
    elif query.data == "set_pattern":
        await handle_pattern_setup(update, context, user)
    elif query.data == "unlock_pattern":
        await show_locked_message(update, context)
    elif query.data in ["new_note", "list_notes", "settings", "lock_device"]:
        await handle_main_menu(update, context, user)
    elif query.data == "back_to_menu":
        await show_main_menu(update, context, user)
    elif query.data.startswith("view_note_"):
        note_id = int(query.data.split("_")[2])
        await show_note_details(update, context, user, note_id)
    elif query.data.startswith("edit_note_"):
        note_id = int(query.data.split("_")[2])
        await show_edit_note_form(update, context, user, note_id)
    elif query.data.startswith("delete_note_"):
        note_id = int(query.data.split("_")[2])
        await delete_note_confirmation(update, context, user, note_id)
    elif query.data == "change_pattern":
        await show_pattern_change(update, context, user)
    else:
        # Debug: log unknown callback data
        print(f"Unknown callback data: {query.data}")
        await query.answer("❌ Unknown action!")

async def show_note_details(update: Update, context: ContextTypes.DEFAULT_TYPE, user, note_id):
    """Show full note details"""
    note = await get_note_by_id(note_id, user.id)
    if not note:
        await update.callback_query.answer("❌ Note not found!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit", callback_data=f"edit_note_{note.id}")],
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_note_{note.id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="list_notes")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        f"📖 {note.title}\n\n"
        f"📄 {note.content}\n\n"
        f"📅 Created: {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"📅 Updated: {note.updated_at.strftime('%Y-%m-%d %H:%M')}",
        reply_markup=reply_markup
    )

async def show_edit_note_form(update: Update, context: ContextTypes.DEFAULT_TYPE, user, note_id):
    """Show form to edit a note"""
    note = await get_note_by_id(note_id, user.id)
    if not note:
        await update.callback_query.answer("❌ Note not found!")
        return
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data=f"view_note_{note.id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        f"✏️ Edit Note: {note.title}\n\n"
        f"Current content:\n{note.content}\n\n"
        f"Send your new content, or 'cancel' to go back.",
        reply_markup=reply_markup
    )
    
    user_states[user.id] = f"editing_note_{note_id}"

async def delete_note_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, user, note_id):
    """Show delete confirmation for a note"""
    note = await get_note_by_id(note_id, user.id)
    if not note:
        await update.callback_query.answer("❌ Note not found!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{note.id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"view_note_{note.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        f"🗑️ Delete Note\n\n"
        f"Are you sure you want to delete:\n"
        f"📝 {note.title}\n\n"
        f"This action cannot be undone!",
        reply_markup=reply_markup
    )

async def show_pattern_change(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Show pattern change form"""
    keyboard = [
        [InlineKeyboardButton("1", callback_data="new_pattern_1"),
         InlineKeyboardButton("2", callback_data="new_pattern_2"),
         InlineKeyboardButton("3", callback_data="new_pattern_3")],
        [InlineKeyboardButton("4", callback_data="new_pattern_4"),
         InlineKeyboardButton("5", callback_data="new_pattern_5"),
         InlineKeyboardButton("6", callback_data="new_pattern_6")],
        [InlineKeyboardButton("7", callback_data="new_pattern_7"),
         InlineKeyboardButton("8", callback_data="new_pattern_8"),
         InlineKeyboardButton("9", callback_data="new_pattern_9")],
        [InlineKeyboardButton("🔒 Set New Pattern", callback_data="set_new_pattern")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "🔐 Change Pattern Lock\n\n"
        "Enter your new pattern:\n\n"
        "Current pattern: " + context.user_data.get('new_temp_pattern', ''),
        reply_markup=reply_markup
    )
    
    user_states[user.id] = "changing_pattern"
    context.user_data['new_temp_pattern'] = ""

# Add new function get_unlock_keyboard for creating a WebApp button for pattern unlock

def get_unlock_keyboard():
    # Telegram WebApp integration for sliding pattern unlock
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    web_app_url = "https://abenih.github.io/my-bot-webapp/webapp/pattern_lock.html"  # Updated URL
    keyboard = [
        [InlineKeyboardButton("Swipe to Unlock", web_app=WebAppInfo(url=web_app_url))]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_handlers():
    """Return all handlers for the bot"""
    return [
        CommandHandler("start", start),
        CallbackQueryHandler(handle_callback_query),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    ]

async def show_locked_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message instructing the user to use the Swipe to Unlock interface."""
    message = "Device locked. Please use the 'Swipe to Unlock' button to unlock your Notepad."
    if update.callback_query:
        await update.callback_query.edit_message_text(message)
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(message)
