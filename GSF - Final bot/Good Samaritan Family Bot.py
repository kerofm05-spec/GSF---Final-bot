from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont
import os
import arabic_reshaper
from bidi.algorithm import get_display

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOT_TOKEN = "8478196077:AAFp9oxQxSPfixOFFKLtXjN64pzHv5g2xoI"  # <-- Replace with your bot token

# Templates for each faculty
TEMPLATES = {
    "Medicine": os.path.join(BASE_DIR, "Template_Medicine.png"),
    "Dentistry": os.path.join(BASE_DIR, "Template_Dentistry.png"),
    "Pharmacy": os.path.join(BASE_DIR, "Template_Pharmacy.png"),
    "Veterinary": os.path.join(BASE_DIR, "Template_Veterinary.png")
}

# Fonts
VERSE_FONT_PATH = os.path.join(BASE_DIR, "Amiri-Bold.ttf")        # verse
LOCATION_FONT_PATH = os.path.join(BASE_DIR, "Amiri-Regular.ttf")  # location

# Safe text area
IMAGE_WIDTH = 1200
VERSE_Y = 280
LOCATION_Y = 825
MAX_VERSE_WIDTH = 1100

# Store user states
user_data = {}

# --- Helper for multi-line Arabic ---
def draw_arabic(draw, text, font_path, font_size, position, max_width, align="right"):
    font = ImageFont.truetype(font_path, font_size)

    # Reshape + bidi
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)

    # Wrap text manually
    lines = []
    words = bidi_text.split(" ")
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0,0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    # Draw lines vertically (top to bottom)
    y_offset = 0
    for line in reversed(lines):
        bbox = draw.textbbox((0,0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = position[0] if align == "left" else position[0] - w
        y = position[1] + y_offset
        draw.text((x, y), line, font=font, fill=(0,0,0))
        y_offset += h + 5

# ---------- Bot Handlers ----------

# Step 1: Start → show buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {"step": "faculty"}

    keyboard = [
        [InlineKeyboardButton("Medicine", callback_data="Medicine"),
         InlineKeyboardButton("Dentistry", callback_data="Dentistry")],
        [InlineKeyboardButton("Pharmacy", callback_data="Pharmacy"),
         InlineKeyboardButton("Veterinary", callback_data="Veterinary")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📚 اختر الكلية:", reply_markup=reply_markup)

# Step 2: Handle faculty button click
async def faculty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    faculty = query.data
    user_id = query.from_user.id

    user_data[user_id] = {"step": "verse", "faculty": faculty}
    await query.edit_message_text(f"📖 اخترت كلية: {faculty}\nالآن ابعت الآية أولاً:")

# Step 3: Handle verse and location messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data:
        await update.message.reply_text("اكتب /start للبدء")
        return

    step = user_data[user_id]["step"]

    # Verse
    if step == "verse":
        user_data[user_id]["verse"] = text
        user_data[user_id]["step"] = "location"
        await update.message.reply_text("📍 الآن ابعت مكان الآية (مثال: يوحنا 3:16)")
        return

    # Location → generate image
    if step == "location":
        faculty = user_data[user_id]["faculty"]
        verse = user_data[user_id]["verse"]
        location = text

        template_file = TEMPLATES.get(faculty)
        if not os.path.exists(template_file):
            await update.message.reply_text("❌ لم أجد القالب للكلية المحددة.")
            return

        img = Image.open(template_file).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Draw verse (right-aligned)
        draw_arabic(draw, verse, VERSE_FONT_PATH, 80,(IMAGE_WIDTH-80, VERSE_Y), MAX_VERSE_WIDTH, align="right")
        # Draw location (left-aligned)
        draw_arabic(draw, location, LOCATION_FONT_PATH, 40, (80, LOCATION_Y), MAX_VERSE_WIDTH, align="left")

        output_path = os.path.join(BASE_DIR, f"result_{user_id}.png")
        img.save(output_path)

        await update.message.reply_photo(photo=open(output_path, "rb"))

        # Clean up
        os.remove(output_path)
        del user_data[user_id]

# ---------- Run Bot ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(faculty_callback))  # faculty buttons
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 Verse Template Bot Running...")
app.run_polling()
