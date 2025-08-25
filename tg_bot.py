import logging
import os
import shutil
import io
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- Import your custom modules ---
from crossword import extract_crossword_grid, matrix_to_crossword_image
from letters import extract_cyrillic_letters
from solver import solve_crossword_all
from words import get_words_data

# --- Setup logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
(
    AWAITING_IMAGE,
    GRID_CONFIRMATION,
    LETTERS_CONFIRMATION,
    AWAITING_CORRECTED_LETTERS,
) = range(4)


# --- Helper Functions ---
async def save_bad_screenshot(context: ContextTypes.DEFAULT_TYPE):
    """Saves the user's screenshot to a 'bad' directory for later analysis."""
    if not os.path.exists("./bad"):
        os.makedirs("./bad")

    user = context.user_data.get("user")
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    original_path = context.user_data.get("screenshot_path")

    if user and original_path and os.path.exists(original_path):
        destination_path = f"./bad/{date_str}_{user.id}_{user.username}.png"
        # Using copyfile so the original temp file can still be cleaned up normally
        shutil.copyfile(original_path, destination_path)
        logger.info(f"Saved bad screenshot to {destination_path}")
        return destination_path
    return None


def cleanup_temp_file(context: ContextTypes.DEFAULT_TYPE):
    """Deletes the temporary screenshot file."""
    temp_path = context.user_data.get("screenshot_path")
    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)
        logger.info(f"Cleaned up temp file: {temp_path}")

# --- Formatting Helpers ---
def format_words_output(words_data: dict) -> str:
    """Formats the list of possible words for display."""
    response_text = "Sorry, the grid extraction failed. Here are some possible words based on the letters:\n\n"
    for size, words in words_data.items():
        words_preview = ", ".join(words[:10])
        response_text += f"**{size}):** {words_preview}\n"
    return response_text

def format_solution_output(solution: list, weights: dict, custom_letters: bool = False) -> str:
    """Formats the crossword solution for display."""
    title = "✨ Solution (with your letters) ✨" if custom_letters else "✨ Crossword Solution ✨"
    res = dict()
    for sol in solution:
        for _, word in sol.items():
            idx = len(word)
            if idx not in res:
                res[idx] = []
            res[idx].append(word)
    solution_lines = [', '.join(list(set(sorted(words, key=lambda w: weights[w])))) for ind, words in res.items()]
    return f"{title}\n\n" + "\n".join(solution_lines)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the bot and asks for an image."""
    await update.message.reply_text(
        "👋 Hello! Please send me a screenshot of a crossword puzzle to solve."
    )
    return AWAITING_IMAGE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled.")
    cleanup_temp_file(context)
    return ConversationHandler.END


# --- Conversation Steps ---
async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's image, extracts grid, and asks for confirmation."""
    # Clean up any existing conversation first
    await cleanup_conversation(context)
    
    photo_file = await update.message.photo[-1].get_file()

    context.user_data["user"] = update.effective_user

    if not os.path.exists("./temp"):
        os.makedirs("./temp")
    screenshot_path = f"./temp/{photo_file.file_id}.png"
    await photo_file.download_to_drive(screenshot_path)
    context.user_data["screenshot_path"] = screenshot_path

    await update.message.reply_text("Processing image... 🧐")

    matrix = extract_crossword_grid(screenshot_path)
    context.user_data["matrix"] = matrix
    grid_image = matrix_to_crossword_image(matrix)

    bio = io.BytesIO()
    grid_image.save(bio, "PNG")
    bio.seek(0)

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, that's correct", callback_data="grid_yes"),
            InlineKeyboardButton("❌ No, it's wrong", callback_data="grid_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await update.message.reply_photo(
        photo=bio,
        caption="I've analyzed the grid. Does this look correct?",
        reply_markup=reply_markup,
    )
    context.user_data["message_id"] = message.message_id

    return GRID_CONFIRMATION


async def grid_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user's confirmation of the grid and then asks to confirm letters."""
    query = update.callback_query
    await query.answer()

    is_correct = query.data == "grid_yes"
    context.user_data["is_crossword_extracted_correct"] = is_correct

    if not is_correct:
        await save_bad_screenshot(context) # Save screenshot if grid is wrong

    # This logic is now the same for both "yes" and "no"
    letters = extract_cyrillic_letters(context.user_data["screenshot_path"])
    context.user_data["letters"] = letters

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="letters_yes"),
            InlineKeyboardButton("✍️ No, I'll type them", callback_data="letters_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_caption(
        chat_id=query.message.chat_id,
        message_id=context.user_data["message_id"],
        caption=f"Great! I've extracted these letters: \n\n`{letters}`\n\nAre they correct?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return LETTERS_CONFIRMATION


def weights_from_words(words):
    trop = {}
    for _, W in enumerate(words.items()):
        for weight, w in enumerate(W):
            trop[w] = weight
    return trop

async def letters_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles confirmation of letters and provides final output."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    message_id = context.user_data["message_id"]

    if query.data == "letters_yes":
        is_grid_correct = context.user_data.get("is_crossword_extracted_correct", False)
        letters = context.user_data["letters"]
        words = get_words_data(letters)

        if is_grid_correct:
            matrix = context.user_data["matrix"]
            solution = solve_crossword_all(matrix, words)
            
            if solution:  # If solution was found
                final_text = format_solution_output(solution, weights=weights_from_words(words))
                
                # Add button to show words as fallback
                keyboard = [
                    [InlineKeyboardButton("🔤 Show possible words instead", callback_data="show_words_fallback")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=final_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
                # Store words data for potential fallback
                context.user_data["words_data"] = words
                return ConversationHandler.END
            else:  # Fallback: couldn't find solution, show words instead
                final_text = format_words_output(words)
                final_text = "❌ Couldn't find a complete solution for the grid. Here are possible words:\n\n" + final_text
        else:
            final_text = format_words_output(words)

        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=final_text,
            parse_mode="Markdown",
        )
        cleanup_temp_file(context)
        return ConversationHandler.END

    elif query.data == "letters_no":
        await save_bad_screenshot(context)
        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption="Got it. Please send me the correct letters as a single text message (e.g., `АБВГДЕЖЗ`).",
        )
        return AWAITING_CORRECTED_LETTERS


async def receive_corrected_letters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives corrected letters and provides final output."""
    corrected_letters = update.message.text
    await update.message.delete()

    chat_id = update.effective_chat.id
    message_id = context.user_data["message_id"]

    is_grid_correct = context.user_data.get("is_crossword_extracted_correct", False)
    words = get_words_data(corrected_letters)
    
    if is_grid_correct:
        matrix = context.user_data["matrix"]
        solution = solve_crossword_all(matrix, words)
        
        if solution:  # If solution was found
            final_text = format_solution_output(solution, weights=weights_from_words(words), custom_letters=True)
            
            # Add button to show words as fallback
            keyboard = [
                [InlineKeyboardButton("🔤 Show possible words instead", callback_data="show_words_fallback")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=final_text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
            # Store words data for potential fallback
            context.user_data["words_data"] = words
            return ConversationHandler.END
        else:  # Fallback: couldn't find solution, show words instead
            final_text = format_words_output(words)
            final_text = "❌ Couldn't find a complete solution for the grid. Here are possible words:\n\n" + final_text
    else:
        final_text = format_words_output(words)

    await context.bot.edit_message_caption(
        chat_id=chat_id,
        message_id=message_id,
        caption=final_text,
        parse_mode="Markdown",
    )
    cleanup_temp_file(context)
    return ConversationHandler.END


async def fallback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the fallback request to show words instead of solution."""
    query = update.callback_query
    await query.answer()

    if query.data == "show_words_fallback":
        words_data = context.user_data.get("words_data")
        if words_data:
            final_text = format_words_output(words_data)
            final_text = "🔤 Here are all possible words:\n\n" + final_text
            
            await context.bot.edit_message_caption(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                caption=final_text,
                parse_mode="Markdown",
            )
        cleanup_temp_file(context)
    
    return ConversationHandler.END

async def cleanup_conversation(context: ContextTypes.DEFAULT_TYPE):
    """Clean up any ongoing conversation."""
    cleanup_temp_file(context)
    # Clear conversation data
    keys_to_remove = ['user', 'screenshot_path', 'matrix', 'message_id', 'letters', 
                     'is_crossword_extracted_correct', 'words_data']
    for key in keys_to_remove:
        if key in context.user_data:
            del context.user_data[key]
    # Also clear any conversation timeout if exists
    if 'conversation_timeout' in context.user_data:
        if context.user_data['conversation_timeout']:
            context.user_data['conversation_timeout'].cancel()
        del context.user_data['conversation_timeout']

async def new_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles new image input during any conversation state, restarting the process."""
    # Clean up existing conversation
    await cleanup_conversation(context)
    
    # Process the new image
    return await image_handler(update, context)

def main() -> None:
    """Run the bot."""
    token = os.getenv("TELEGRAM_TOKEN")
    
    application = Application.builder().token(token).build()

    # Handler for new images that can interrupt any conversation
    new_image_handler_obj = MessageHandler(filters.PHOTO & ~filters.COMMAND, new_image_handler)

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.PHOTO & ~filters.COMMAND, image_handler),
        ],
        states={
            AWAITING_IMAGE: [new_image_handler_obj],
            GRID_CONFIRMATION: [
                CallbackQueryHandler(grid_confirmation_callback, pattern="^grid_.*$"),
                new_image_handler_obj
            ],
            LETTERS_CONFIRMATION: [
                CallbackQueryHandler(letters_confirmation_callback, pattern="^letters_.*$"),
                new_image_handler_obj
            ],
            AWAITING_CORRECTED_LETTERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_corrected_letters),
                new_image_handler_obj
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add the fallback callback handler separately (not part of conversation states)
    application.add_handler(CallbackQueryHandler(fallback_callback, pattern="^show_words_fallback$"))
    application.add_handler(conv_handler)

    print("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
