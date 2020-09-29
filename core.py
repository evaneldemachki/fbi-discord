import os
import random
import discord
import sqlite3
import re
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

conn = sqlite3.connect('core.db')
c = conn.cursor()
# Create table
c.execute('''CREATE TABLE IF NOT EXISTS trump
             (quote text)''')

conn.commit()

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if re.search(r"\b" + 'trump' + r"\b", message.content.lower()):
        response = random.choice(
            c.execute('SELECT * FROM trump').fetchall())[0]
        
        if '—' in response:
            response = response.split('—')[0] + '\n— ' + response.split('—')[1]
        else:
            response += '\n— Donald J. Trump'
            await message.channel.send(response)
            return


client.run(TOKEN)