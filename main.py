import discord
from discord.ext import commands
from discord import app_commands
import os
import io
from flask import Flask
from threading import Thread
from pydub import AudioSegment
from pydub.generators import Sine

# Flask app for uptime monitoring
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"  # Response for UptimeRobot

def run():
    app.run(host='0.0.0.0', port=8080, threaded=True)

# Intents setup
intents = discord.Intents.default()
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Morse Code Dictionaries
STANDARD_MORSE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..',
    '9': '----.', '0': '-----', ' ': '/'
}
ALTERNATIVE_MORSE = {key: val.replace('.', '•').replace('-', '−') for key, val in STANDARD_MORSE.items()}
STANDARD_TO_TEXT = {value: key for key, value in STANDARD_MORSE.items()}
ALTERNATIVE_TO_TEXT = {value: key for key, value in ALTERNATIVE_MORSE.items()}

# Convert Text to Morse
def text_to_morse(text, morse_dict):
    return ' '.join(morse_dict.get(char.upper(), '?') for char in text)

# Convert Morse to Text
def morse_to_text(morse, text_dict):
    return ''.join(text_dict.get(code, '?') for code in morse.split())

# Generate Morse Audio
def generate_morse_audio(text, morse_dict):
    morse_code = text_to_morse(text, morse_dict)

    # Define timing for 20 WPM
    dot_duration = 60
    dash_duration = dot_duration * 3
    intra_char_space = dot_duration
    inter_char_space = dot_duration * 3
    word_space = dot_duration * 7

    dot = Sine(800).to_audio_segment(duration=dot_duration)
    dash = Sine(800).to_audio_segment(duration=dash_duration)
    silence = AudioSegment.silent(duration=intra_char_space)
    space = AudioSegment.silent(duration=word_space)

    audio = AudioSegment.silent(duration=500)

    for symbol in morse_code:
        if symbol == "." or symbol == "•":
            audio += dot + silence
        elif symbol == "-" or symbol == "−":
            audio += dash + silence
        elif symbol == "/":
            audio += space
        else:
            audio += AudioSegment.silent(duration=inter_char_space)

    audio = audio + AudioSegment.silent(duration=500)
    audio_buffer = io.BytesIO()
    audio.export(audio_buffer, format="mp3")
    audio_buffer.seek(0)
    return audio_buffer

# Morse Type Selection
class MorseTypeSelect(discord.ui.Select):
    def __init__(self, conversion_type, text):
        self.conversion_type = conversion_type
        self.text = text
        options = [
            discord.SelectOption(label="Standard Morse", value="standard", description="Convert using Standard Morse"),
            discord.SelectOption(label="Alternative Morse", value="alternative", description="Convert using Alternative Morse"),
        ]
        super().__init__(placeholder="Select Morse Type", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        morse_dict = STANDARD_MORSE if self.values[0] == "standard" else ALTERNATIVE_MORSE
        text_dict = STANDARD_TO_TEXT if self.values[0] == "standard" else ALTERNATIVE_TO_TEXT

        if self.conversion_type == "text_to_morse":
            morse_code = text_to_morse(self.text, morse_dict)
            await interaction.followup.send(f'```Morse Code: {morse_code}```')

        elif self.conversion_type == "text_to_audio":
            audio_file = generate_morse_audio(self.text, morse_dict)
            await interaction.followup.send(content="🔊 Here is your Morse code audio:", file=discord.File(audio_file, "morse_code.mp3"))

        elif self.conversion_type == "morse_to_text":
            decoded_text = morse_to_text(self.text, text_dict)
            await interaction.followup.send(f'```Text: {decoded_text}```')

# Conversion Selection
class ConversionSelect(discord.ui.Select):
    def __init__(self, text):
        self.text = text
        options = [
            discord.SelectOption(label="Text to Morse", value="text_to_morse", description="Convert text to Morse code"),
            discord.SelectOption(label="Text to Morse Audio", value="text_to_audio", description="Convert text to Morse audio"),
            discord.SelectOption(label="Morse to Text", value="morse_to_text", description="Convert Morse code to text"),
        ]
        super().__init__(placeholder="Select Conversion Type", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("📌 Now, select the Morse type:", view=MorseTypeView(self.values[0], self.text))

# Views for Dropdowns
class ConversionView(discord.ui.View):
    def __init__(self, text):
        super().__init__()
        self.add_item(ConversionSelect(text))

class MorseTypeView(discord.ui.View):
    def __init__(self, conversion_type, text):
        super().__init__()
        self.add_item(MorseTypeSelect(conversion_type, text))

# Slash Command: Convert text or Morse code
@bot.tree.command(name="convert", description="Convert text to Morse, Morse to text, or generate Morse audio.")
async def convert(interaction: discord.Interaction, text: str):
    await interaction.response.send_message("📌 Please select a conversion type:", view=ConversionView(text))

# Event: Bot is Ready
@bot.event
async def on_ready():
    print(f"✅ Bot is ready! Logged in as {bot.user}")
    await bot.tree.sync()

# Run Flask server in background
Thread(target=run).start()

# Run the bot
bot.run(os.getenv("BOT_TOKEN"))
