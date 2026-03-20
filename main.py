import discord
from discord.ext import commands, tasks
import requests
import sqlite3
from datetime import datetime, time
import os

# === BOT TOKEN UND COC API KEY AUS ENVIRONMENT VARIABLES ===
TOKEN = os.environ["TOKEN"]
COC_API_KEY = os.environ["COC_API_KEY"]

# Header für die Clash of Clans API
HEADERS = {"Authorization": f"Bearer {COC_API_KEY}"}

# Liste der Spieler, die im Leaderboard auftauchen sollen
SPIELER = ["#ABC123", "#XYZ789"]  # Hier deine Spieler-Tags eintragen

# Channel-ID, in dem das Leaderboard gepostet wird
CHANNEL_ID = 123456789  # Hier die Channel-ID eintragen

# Discord-Bot einrichten
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# Datenbank vorbereiten
conn = sqlite3.connect("daten.db")
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS trophaen (
    spieler_tag TEXT,
    trophaen INTEGER,
    datum TEXT
)""")
conn.commit()


# Spieler-Daten von COC abrufen
def hole_spieler(tag):
    url = f"https://api.clashofclans.com/v1/players/{tag.replace('#','%23')}"
    r = requests.get(url, headers=HEADERS)
    return r.json()


# Tägliches Leaderboard um 6 Uhr
@tasks.loop(time=time(hour=6, minute=0))
async def taegliches_leaderboard():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    ergebnisse = []

    for tag in SPIELER:
        daten = hole_spieler(tag)
        name = daten["name"]
        trophaen = daten["trophies"]

        heute = datetime.now().strftime("%Y-%m-%d")

        c.execute("SELECT trophaen FROM trophaen WHERE spieler_tag=? ORDER BY datum DESC LIMIT 1", (tag,))
        letzte = c.fetchone()

        diff = 0
        if letzte:
            diff = trophaen - letzte[0]

        c.execute("INSERT INTO trophaen VALUES (?, ?, ?)", (tag, trophaen, heute))
        conn.commit()

        ergebnisse.append((name, trophaen, diff))

    ergebnisse.sort(key=lambda x: x[1], reverse=True)

    msg = "🏆 Tages-Leaderboard\n\n"
    for i, (name, trophaen, diff) in enumerate(ergebnisse, 1):
        zeichen = "+" if diff >= 0 else ""
        msg += f"{i}. {name} – {trophaen} ({zeichen}{diff})\n"

    await channel.send(msg)


@bot.event
async def on_ready():
    print(f"Bot gestartet als {bot.user}")
    taegliches_leaderboard.start()


bot.run(TOKEN)
