import discord
from discord.ext import commands, tasks
import random
import asyncio
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

PREFIX = "!"
COLOR = 0x1E90FF
TIME_LIMIT = 30
ROLE_CHAMPION = "Champion BLD"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

quiz_questions = [
    {"question": "Quel est le plus grand océan du monde ?", "choices": ["A. Océan Atlantique", "B. Océan Indien", "C. Océan Pacifique", "D. Océan Arctique"], "answer": "C", "difficulty": "Facile", "category": "Géographie"},
    {"question": "Combien de couleurs y a-t-il dans un arc-en-ciel ?", "choices": ["A. 5", "B. 6", "C. 7", "D. 8"], "answer": "C", "difficulty": "Facile", "category": "Science"},
    {"question": "Quelle planète est connue comme la Planète Rouge ?", "choices": ["A. Mars", "B. Jupiter", "C. Vénus", "D. Saturne"], "answer": "A", "difficulty": "Facile", "category": "Astronomie"}
]

current_question = {}
scoreboard = {}
question_task = None
start_time = 0
cooldown_end_time = 0

felicitations = [
    "🎉 Bravo, tu déchires !", 
    "✨ Excellente réponse !", 
    "🧠 Ton cerveau est en feu !", 
    "🔥 Impressionnant ! Continue comme ça !", 
    "🏅 Tu viens de gagner un point bien mérité !",
    "😂 Tu es plus rapide que l'éclair !",
    "👏 Ta mémoire ferait rougir un champion de mémoire !"
]

SCORE_FILE = "scores.json"

def sauvegarder_scores():
    with open(SCORE_FILE, "w") as f:
        json.dump(scoreboard, f)

def charger_scores():
    global scoreboard
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r") as f:
            scoreboard = json.load(f)

@bot.event
async def on_ready():
    print(f"✅ BLD est connecté en tant que {bot.user}")
    charger_scores()
    reset_scores.start()

@bot.command()
async def quiz(ctx, niveau: str = None, categorie: str = None):
    global current_question, question_task, start_time, cooldown_end_time

    if time.time() < cooldown_end_time:
        temps_restant = int(cooldown_end_time - time.time())
        await ctx.send(f"🕒 Merci de patienter {temps_restant} secondes avant de lancer un nouveau quiz.")
        return

    if current_question:
        await ctx.send("❗ Une question est déjà en cours. Réponds d'abord !")
        return

    questions_filtrees = quiz_questions
    if niveau:
        questions_filtrees = [q for q in questions_filtrees if q['difficulty'].lower() == niveau.lower()]
    if categorie:
        questions_filtrees = [q for q in questions_filtrees if q['category'].lower() == categorie.lower()]
    if not questions_filtrees:
        await ctx.send("❗ Aucune question trouvée avec ces critères.")
        return

    question = random.choice(questions_filtrees)
    current_question = {"data": question, "channel": ctx.channel, "author": ctx.author}
    embed = discord.Embed(title="🧠 Quiz Time !", description=f"**{question['question']}**", color=COLOR)
    for choice in question['choices']:
        embed.add_field(name="", value=choice, inline=False)
    embed.add_field(name="Difficulté", value=question['difficulty'], inline=True)
    embed.add_field(name="Catégorie", value=question['category'], inline=True)
    embed.set_author(name="BLD")
    embed.set_footer(text=f"create by Ghqst 🧠 | ⏳ Temps restant : {TIME_LIMIT} secondes")
    message = await ctx.send(embed=embed)

    await message.add_reaction("⏳")

    question_task = asyncio.create_task(timeout_question(ctx))
    start_time = time.time()

    cooldown_end_time = time.time() + 10

async def timeout_question(ctx):
    global current_question
    await asyncio.sleep(TIME_LIMIT)
    if current_question:
        await ctx.send(f"⏰ Temps écoulé ! La bonne réponse était : {current_question['data']['answer']}")
        current_question = {}

@bot.command()
async def reponse(ctx, choix: str):
    global current_question, scoreboard, question_task, start_time
    if not current_question:
        await ctx.send("❗ Aucun quiz en cours. Utilise !quiz pour commencer.")
        return

    choix = choix.upper()
    bonne_reponse = current_question['data']['answer']
    if choix == bonne_reponse:
        temps_reponse = time.time() - start_time
        bonus = 2 if temps_reponse <= 5 else 1 if temps_reponse <= 10 else 0
        felicitations_message = random.choice(felicitations)
        await ctx.send(f"✅ Bonne réponse ! {felicitations_message} (Bonus de vitesse : +{bonus} point(s))")
        user_id = str(ctx.author.id)
        scoreboard[user_id] = scoreboard.get(user_id, 0) + 1 + bonus
        sauvegarder_scores()
    else:
        await ctx.send(f"❌ Mauvaise réponse. La bonne réponse était : {bonne_reponse}")

    if question_task:
        question_task.cancel()
    current_question = {}

@bot.command()
async def classement(ctx):
    if not scoreboard:
        await ctx.send("📊 Aucun score pour le moment.")
        return

    sorted_scores = sorted(scoreboard.items(), key=lambda x: x[1], reverse=True)
    desc = ""
    top_user_id = None
    for idx, (user_id, score) in enumerate(sorted_scores, start=1):
        user = await bot.fetch_user(int(user_id))
        desc += f"**{idx}. {user.name}** : {score} point(s)\n"
        if idx == 1:
            top_user_id = int(user_id)

    embed = discord.Embed(title="🏆 Classement BLD", description=desc, color=COLOR)
    await ctx.send(embed=embed)

    if top_user_id:
        guild = ctx.guild
        role = discord.utils.get(guild.roles, name=ROLE_CHAMPION)
        if not role:
            role = await guild.create_role(name=ROLE_CHAMPION, color=discord.Color.gold())
        for member in guild.members:
            if role in member.roles and member.id != top_user_id:
                await member.remove_roles(role)
        top_member = guild.get_member(top_user_id)
        if top_member and role not in top_member.roles:
            await top_member.add_roles(role)
            await ctx.send(f"👑 {top_member.display_name} reçoit le rôle **{ROLE_CHAMPION}** !")

@bot.command()
async def score(ctx):
    user_id = str(ctx.author.id)
    score = scoreboard.get(user_id, 0)
    await ctx.send(f"🏅 {ctx.author.display_name}, ton score actuel est : **{score}** point(s) !")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    score = scoreboard.get(user_id, 0)
    await ctx.send(f"📊 Statistiques de {ctx.author.display_name} :\n**Score total** : {score} point(s).\n**Réponses correctes** : {score} (bonus de vitesse inclus).\nD'autres statistiques arriveront bientôt ! 🧠")

@bot.command(name="aide")
async def aide(ctx):
    embed = discord.Embed(title="🧠 Commandes disponibles pour BLD", color=COLOR)
    embed.add_field(name="!quiz", value="Commencer un quiz.", inline=False)
    embed.add_field(name="!reponse [choix]", value="Répondre à la question en cours.", inline=False)
    embed.add_field(name="!classement", value="Afficher le classement actuel.", inline=False)
    embed.add_field(name="!score", value="Afficher ton score.", inline=False)
    embed.add_field(name="!stats", value="Afficher tes statistiques personnelles.", inline=False)
    embed.set_footer(text="create by Ghqst 🧠")
    await ctx.send(embed=embed)

@tasks.loop(hours=168)
async def reset_scores():
    global scoreboard
    if scoreboard:
        scoreboard.clear()
        sauvegarder_scores()
        for guild in bot.guilds:
            await guild.system_channel.send("🔄 Les scores ont été réinitialisés pour une nouvelle semaine de compétition ! Bonne chance à tous !")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong ! BLD est en ligne.")

if __name__ == "__main__":
    bot.run(TOKEN)


