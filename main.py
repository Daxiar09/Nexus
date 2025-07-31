# main.py
import json
import discord
from discord.ext import commands, tasks
from aiohttp import web
import asyncio
import os
from datetime import datetime, timedelta

DATA_FILE = "data.json"


def save_data():
    data = {
        "gemmes": bot.user_gemmes,
        "salon_offres_id": bot.shop_channel_id,
        "salon_gemmes_id": bot.gemmes_channel_id,
        "message_gemmes_id": bot.gemmes_message_id,
        "last_claims": bot.last_claims
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            bot.user_gemmes = data.get("gemmes", {})
            bot.shop_channel_id = data.get("salon_offres_id")
            bot.gemmes_channel_id = data.get("salon_gemmes_id")
            bot.gemmes_message_id = data.get("message_gemmes_id")
            bot.last_claims = data.get("last_claims", {})


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

bot.user_gemmes = {}
bot.shop_channel_id = None
bot.gemmes_channel_id = None
bot.gemmes_message_id = None

OWNER_IDS = [
    1111346420088311808, 1063760778546655263, 1183814362364911707,
    1178017105984094219, 1255880204463898717
]


async def handle(request):
    return web.Response(text="Bot en ligne !")


async def run_webserver():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def update_gemmes_message():
    if bot.gemmes_channel_id and bot.gemmes_message_id:
        channel = bot.get_channel(bot.gemmes_channel_id)
        try:
            message = await channel.fetch_message(bot.gemmes_message_id)
        except:
            return
        content = "**💎 Nexus des membres :**\n"
        for user_id, gemmes in bot.user_gemmes.items():
            user = await bot.fetch_user(int(user_id))
            content += f"{user.mention} → {gemmes} nexus\n"
        await message.edit(content=content)


@bot.event
async def on_ready():
    load_data()
    print(f"{bot.user} est prêt !")


def is_owner(ctx):
    return ctx.author.id in OWNER_IDS


@bot.command()
async def addnexus(ctx, membre: discord.Member, montant: int):
    if not is_owner(ctx):
        return await ctx.send(
            "❌ Tu n'es pas autorisé à utiliser cette commande.")
    uid = str(membre.id)
    bot.user_gemmes[uid] = bot.user_gemmes.get(uid, 0) + montant
    await ctx.send(f"✅ {montant} nexus ajoutées à {membre.mention}")
    await update_gemmes_message()
    save_data()


@bot.command()
async def deletenexus(ctx, membre: discord.Member, montant: int):
    if not is_owner(ctx):
        return await ctx.send(
            "❌ Tu n'es pas autorisé à utiliser cette commande.")
    uid = str(membre.id)
    bot.user_gemmes[uid] = max(0, bot.user_gemmes.get(uid, 0) - montant)
    await ctx.send(f"❌ {montant} nexus retirées à {membre.mention}")
    await update_gemmes_message()
    save_data()


@bot.command()
async def set_salon_offres(ctx, salon: discord.TextChannel):
    if not is_owner(ctx):
        return await ctx.send(
            "❌ Tu n'es pas autorisé à utiliser cette commande.")
    bot.shop_channel_id = salon.id
    await ctx.send(f"✅ Salon des offres défini : {salon.mention}")
    save_data()


@bot.command()
async def set_salon_nexus(ctx, salon: discord.TextChannel):
    if not is_owner(ctx):
        return await ctx.send(
            "❌ Tu n'es pas autorisé à utiliser cette commande.")
    msg = await salon.send("Initialisation des nexus...")
    bot.gemmes_channel_id = salon.id
    bot.gemmes_message_id = msg.id
    await update_gemmes_message()
    await ctx.send("✅ Message de nexus initialisé.")
    save_data()


class CategoryView(discord.ui.View):

    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    async def interaction_check(self, interaction):
        return interaction.user == self.author

    @discord.ui.button(label="🎯 Pub", style=discord.ButtonStyle.blurple)
    async def shorts(self, interaction, button):
        await interaction.response.edit_message(content="Choisis une offre :",
                                                view=ShortsOffersView(
                                                    self.author))

    @discord.ui.button(label="🏆 Hoster", style=discord.ButtonStyle.green)
    async def cache(self, interaction, button):
        await interaction.response.edit_message(content="Choisis une offre :",
                                                view=CacheCacheOffersView(
                                                    self.author))

    @discord.ui.button(label="🎥 Montage", style=discord.ButtonStyle.red)
    async def wordrecord(self, interaction, button):
        await interaction.response.edit_message(content="Choisis une offre :",
                                                view=WROffersView(self.author))


class OfferButton(discord.ui.Button):

    def __init__(self, label, price, description):
        super().__init__(label=f"{label} ({price}💎)",
                         style=discord.ButtonStyle.primary)
        self.price = price
        self.description = description

    async def callback(self, interaction):
        uid = str(interaction.user.id)
        if bot.user_gemmes.get(uid, 0) < self.price:
            await interaction.response.send_message(
                "❌ Tu n'as pas assez de gemmes !", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        bot.user_gemmes[uid] -= self.price
        await update_gemmes_message()
        save_data()

        salon = bot.get_channel(bot.shop_channel_id)
        if salon:
            await salon.send(
                f"{interaction.user.mention} a acheté : **{self.description}** <@1111346420088311808>"
            )
        await interaction.followup.send("✅ Offre achetée !", ephemeral=True)


class BaseOffersView(discord.ui.View):

    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    async def interaction_check(self, interaction):
        return interaction.user == self.author


class ShortsOffersView(BaseOffersView):

    def __init__(self, author):
        super().__init__(author)
        self.add_item(OfferButton("Pub @here", 500, "Pub avec mention @here"))
        self.add_item(
            OfferButton("Pub @everyone", 2000, "Pub avec mention @everyone "))


class CacheCacheOffersView(BaseOffersView):

    def __init__(self, author):
        super().__init__(author)
        self.add_item(OfferButton("Host tournoi", 1000, "Hoster d'un tournoi"))
        self.add_item(OfferButton("Host event", 1000, "Hoster d'un event"))


class WROffersView(BaseOffersView):

    def __init__(self, author):
        super().__init__(author)
        self.add_item(OfferButton("Montage short", 500, "Montage d'un short"))


@bot.command()
async def shop(ctx):
    uid = str(ctx.author.id)
    gemmes = bot.user_gemmes.get(uid, 0)
    await ctx.send(f"Tu as **{gemmes} nexus**.\nChoisis une catégorie :",
                   view=CategoryView(ctx.author))


@bot.command()
async def claim(ctx):
    uid = str(ctx.author.id)
    now = datetime.utcnow()

    # Dernier claim
    last_time_str = bot.last_claims.get(uid)
    if last_time_str:
        last_time = datetime.fromisoformat(last_time_str)
        if now - last_time < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_time)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes = remainder // 60
            return await ctx.send(
                f"⏳ Tu as déjà réclamé tes nexus ! Réessaie dans {remaining.days}j {hours}h {minutes}min."
            )

    # Récompense
    bot.user_gemmes[uid] = bot.user_gemmes.get(uid, 0) + 100
    bot.last_claims[uid] = now.isoformat()
    await ctx.send("✅ Tu as reçu **100 nexus** pour aujourd'hui !")
    await update_gemmes_message()
    save_data()


async def main():
    await run_webserver()
    await bot.start(os.getenv("DISCORD_TOKEN"))


bot.last_claims = {}

asyncio.run(main())
