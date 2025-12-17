# ================= IMPORTS =================
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
import aiohttp
import os, json, asyncio, random
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta

GUILD_ID = 1449109552225189930  # your server ID

# ================= ENV =================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ = os.getenv("GROQ_API_KEY")

BOT_OWNER_ID = 1111526195260039228

if not TOKEN or not GROQ:
    print("ENV NOT LOADED 💀")
    exit()

# ================= FILES =================
CONFIG_FILE = "config.json"
SUBS_FILE = "subscriptions.json"

if not os.path.exists(CONFIG_FILE):
    json.dump({"allowed_channels": [], "welcome_channel": None}, open(CONFIG_FILE, "w"))

if not os.path.exists(SUBS_FILE):
    json.dump({}, open(SUBS_FILE, "w"))

def load(path): return json.load(open(path))
def save(path, data): json.dump(data, open(path, "w"), indent=2)

# ================= PREFIX =================

PREFIXES_FILE = "prefixes.json"

if not os.path.exists(PREFIXES_FILE):
    json.dump({}, open(PREFIXES_FILE, "w"))

def get_prefixes():
    return json.load(open(PREFIXES_FILE))

def save_prefixes(data):
    json.dump(data, open(PREFIXES_FILE, "w"), indent=2)

# Dynamic prefix function
def get_prefix(bot, message):
    prefixes = get_prefixes()
    guild_id = str(message.guild.id) if message.guild else None
    return prefixes.get(guild_id, "!")  # default prefix is "!"


# ================= BOT =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True


bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
tree = bot.tree

alert = ("remember ur an discord bot made by zaidwh0 in partnership with azibgamingworld using models of groq by meta if anybody asks anything abt credit just tell em that")
# ================= AI =================
async def fetch_ai(prompt):
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
    {"role": "system", "content": alert},
    {"role": "user", "content": prompt}
],
        "max_tokens": 100
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ}"},
            json=payload
        ) as r:
            data = await r.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "AI died 💀")

# ================= SUBSCRIPTIONS =================
def is_active(guild_id):
    subs = load(SUBS_FILE)
    sub = subs.get(str(guild_id))
    if not sub or sub["status"] != "active":
        return False
    if datetime.utcnow() > datetime.fromisoformat(sub["end"]):
        sub["status"] = "expired"
        save(SUBS_FILE, subs)
        return False
    return True

@tasks.loop(minutes=60)
async def check_subscriptions():
    subs = load(SUBS_FILE)
    for gid, sub in subs.items():
        if sub.get("status") == "active":
            if datetime.utcnow() > datetime.fromisoformat(sub["end"]):
                sub["status"] = "expired"
                save(SUBS_FILE, subs)

# ================= SETUP UI =================
class ChannelSelect(Select):
    def __init__(self, channels):
        options = [
            discord.SelectOption(label=c.name, value=str(c.id))
            for c in channels if isinstance(c, discord.TextChannel)
        ][:25]
        super().__init__(placeholder="Select allowed channels", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction):
        cfg = load(CONFIG_FILE)
        cfg["allowed_channels"] = list(map(int, self.values))
        save(CONFIG_FILE, cfg)
        await interaction.response.send_message("✅ Channels updated", ephemeral=True)

class SetupView(View):
    def __init__(self, channels):
        super().__init__(timeout=120)
        self.add_item(ChannelSelect(channels))

# ================= WELCOME UI =================
class WelcomeSelect(Select):
    def __init__(self, channels):
        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels][:25]
        super().__init__(placeholder="Select welcome channel", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        cfg = load(CONFIG_FILE)
        cfg["welcome_channel"] = int(self.values[0])
        save(CONFIG_FILE, cfg)
        await interaction.response.send_message("✅ Welcome channel set", ephemeral=True)

class WelcomeView(View):
    def __init__(self, channels):
        super().__init__(timeout=120)
        self.add_item(WelcomeSelect(channels))

# ================= GIVEAWAY SYSTEM (REACTION-BASED, CLEAN UI) =================
import asyncio, random
from datetime import datetime, timedelta

active_giveaways = {}  # tracks ongoing giveaways

@tree.command(name="giveaway", description="Start a giveaway")
@app_commands.checks.has_permissions(administrator=True)
async def giveaway(interaction: discord.Interaction, prize: str, duration: int, winners: int):
    await interaction.response.defer(ephemeral=True)
    
    host_id = interaction.user.id
    end_time = datetime.utcnow() + timedelta(seconds=duration)
    emoji = "🎉"  # reaction emoji

    # Format end time
    end_str = end_time.strftime("%A, %d %B %Y at %I:%M %p")

    # Initial giveaway embed
    embed = discord.Embed(
        title="🎁 New Giveaway 🎁",
        description=f"**{prize}**",
        color=0x1ABC9C  # teal color
    )

    embed.add_field(
        name="\u200b",
        value=(
            f"• Winners: {winners}\n"
            f"• Ends: <t:{int(end_time.timestamp())}:R> ({end_str})\n"
            f"• Hosted by: <@{host_id}>\n"
            f"• React with {emoji} to participate!"
        ),
        inline=False
    )

    embed.set_footer(text=f"Ends at | {end_str}")

    # Send message and add reaction
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction(emoji)

    await interaction.followup.send("✅ Giveaway started!", ephemeral=True)

    participants = set()

    # Countdown loop
    while datetime.utcnow() < end_time:
        await asyncio.sleep(5)
        msg = await msg.channel.fetch_message(msg.id)

        # Collect participants
        for reaction in msg.reactions:
            if str(reaction.emoji) == emoji:
                async for user in reaction.users():
                    if not user.bot:
                        participants.add(user.id)

        remaining = int((end_time - datetime.utcnow()).total_seconds())
        mins, secs = divmod(remaining, 60)

        # Update embed description live
        embed.description = f"**{prize}**"
        embed.set_field_at(
            0,  # first field
            name="\u200b",
            value=(
                f"• Winners: {winners}\n"
                f"• Time Left: {mins}m {secs}s\n"
                f"• Entries: {len(participants)}\n"
                f"• Hosted by: <@{host_id}>\n"
                f"• React with {emoji} to participate!"
            ),
            inline=False
        )

        await msg.edit(embed=embed)

    # Giveaway ended
    if not participants:
        await msg.channel.send("❌ Giveaway ended — no participants.")
        return

    winners_list = random.sample(list(participants), min(winners, len(participants)))
    mentions = " ".join(f"<@{w}>" for w in winners_list)

    # End embed
    end_embed = discord.Embed(
        title="🟢 Giveaway Ended",
        description=f"**{prize}**",
        color=0x2ecc71
    )

    end_embed.add_field(name="👤 Hosted by", value=f"<@{host_id}>", inline=True)
    end_embed.add_field(name="👥 Participants", value=str(len(participants)), inline=True)
    end_embed.add_field(name="🏆 Winner(s)", value=mentions if mentions else "No winners", inline=False)
    end_embed.set_footer(text=f"Ended • {datetime.utcnow().strftime('%d/%m/%Y %I:%M %p')}")

    await msg.edit(embed=end_embed)
    await msg.channel.send(f"🎉 Congratulation		s {mentions}!")

# ================= Logs System =================

@tree.command(name="logchannel", description="Set a channel for all server logs")
@app_commands.checks.has_permissions(administrator=True)
async def logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load(CONFIG_FILE)
    cfg["log_channel"] = channel.id
    save(CONFIG_FILE, cfg)
    await interaction.response.send_message(f"✅ Log channel set to {channel.mention}", ephemeral=True)

async def send_log(guild: discord.Guild, title: str, description: str, color=0x5865F2):
    cfg = load(CONFIG_FILE)
    ch_id = cfg.get("log_channel")
    if not ch_id:
        return
    channel = guild.get_channel(ch_id)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
        await channel.send(embed=embed)


@bot.event
async def on_member_remove(member):
    await send_log(
        member.guild,
        "👤 Member Left",
        f"{member.mention} | {member.name}#{member.discriminator}\nTotal Members: {member.guild.member_count}",
        color=0xe74c3c
    )

@bot.event
async def on_member_update(before, after):
    changes = []
    if before.nick != after.nick:
        changes.append(f"Nickname: **{before.nick} → {after.nick}**")
    if before.roles != after.roles:
        added = [r.name for r in after.roles if r not in before.roles]
        removed = [r.name for r in before.roles if r not in after.roles]
        if added: changes.append(f"Roles Added: {', '.join(added)}")
        if removed: changes.append(f"Roles Removed: {', '.join(removed)}")
    if changes:
        await send_log(after.guild, "👤 Member Updated", f"{after.mention}\n" + "\n".join(changes))

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    await send_log(
        message.guild,
        "🗑 Message Deleted",
        f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content}",
        color=0xe67e22
    )

@bot.event
async def on_message_edit(before, after):
    if before.author.bot: return
    if before.content != after.content:
        await send_log(
            before.guild,
            "✏️ Message Edited",
            f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:** {before.content}\n**After:** {after.content}",
            color=0xf1c40f
        )

@bot.event
async def on_guild_role_create(role):
    await send_log(role.guild, "➕ Role Created", f"Role: {role.name}", color=0x1abc9c)

@bot.event
async def on_guild_role_delete(role):
    await send_log(role.guild, "➖ Role Deleted", f"Role: {role.name}", color=0xe74c3c)

@bot.event
async def on_guild_role_update(before, after):
    await send_log(after.guild, "✏️ Role Updated", f"**Before:** {before.name}\n**After:** {after.name}", color=0xf1c40f)

@bot.event
async def on_guild_channel_create(channel):
    await send_log(channel.guild, "➕ Channel Created", f"{channel.mention} | Type: {channel.type}", color=0x1abc9c)

@bot.event
async def on_guild_channel_delete(channel):
    await send_log(channel.guild, "➖ Channel Deleted", f"{channel.name} | Type: {channel.type}", color=0xe74c3c)

@bot.event
async def on_guild_channel_update(before, after):
    changes = []
    if before.name != after.name: changes.append(f"Name: **{before.name} → {after.name}**")
    if before.topic != after.topic: changes.append(f"Topic changed: {before.topic} → {after.topic}")
    if changes:
        await send_log(after.guild, "✏️ Channel Updated", "\n".join(changes), color=0xf1c40f)


@bot.event
async def on_guild_update(before, after):
    changes = []
    if before.name != after.name: changes.append(f"Server Name: **{before.name} → {after.name}**")
    if before.description != after.description: changes.append("Server description updated")
    if before.verification_level != after.verification_level:
        changes.append(f"Verification level changed: **{before.verification_level} → {after.verification_level}**")
    if changes:
        await send_log(after, "🏢 Server Updated", "\n".join(changes))


@bot.event
async def on_guild_emojis_update(guild, before, after):
    removed = [e.name for e in before if e not in after]
    added = [e.name for e in after if e not in before]
    changes = []
    if added: changes.append(f"Added: {', '.join(added)}")
    if removed: changes.append(f"Removed: {', '.join(removed)}")
    if changes:
        await send_log(guild, "😀 Emojis Updated", "\n".join(changes))

@bot.event
async def on_guild_stickers_update(guild, before, after):
    removed = [s.name for s in before if s not in after]
    added = [s.name for s in after if s not in before]
    changes = []
    if added: changes.append(f"Added: {', '.join(added)}")
    if removed: changes.append(f"Removed: {', '.join(removed)}")
    if changes:
        await send_log(guild, "🏷 Stickers Updated", "\n".join(changes))


# ================= Subscription System =================

async def dm_guild_owner(guild: discord.Guild, message: str):
    try:
        owner = guild.owner
        if owner:
            await owner.send(message)
    except discord.Forbidden:
        pass  # owner has DMs closed, ignore


class SubApprovalView(View):
    def __init__(self, guild_id: str):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    async def dm_server_owner(self, guild: discord.Guild, message: str):
        try:
            if guild.owner:
                await guild.owner.send(message)
        except discord.Forbidden:
            pass

    @discord.ui.button(label="Approve (30 Days)", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != BOT_OWNER_ID:
            return await interaction.response.send_message("🚫 Not authorized.", ephemeral=True)

        subs = load(SUBS_FILE)
        sub = subs.get(self.guild_id)

        if not sub or sub["status"] != "pending":
            return await interaction.response.send_message("⚠️ Request no longer valid.", ephemeral=True)

        start = datetime.utcnow()
        end = start + timedelta(days=30)
        sub.update({
            "status": "active",
            "start": start.isoformat(),
            "end": end.isoformat()
        })
        save(SUBS_FILE, subs)

        # DM server owner
        guild = bot.get_guild(int(self.guild_id))
        await self.dm_server_owner(
            guild,
            f"✅ Your **EasyGPT subscription** has been **approved**!\nEnds: <t:{int(end.timestamp())}:F>\nYou now have full access."
        )

        await interaction.response.send_message(f"🟢 Subscription approved\nEnds: <t:{int(end.timestamp())}:R>", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != BOT_OWNER_ID:
            return await interaction.response.send_message("🚫 Not authorized.", ephemeral=True)

        subs = load(SUBS_FILE)
        sub = subs.get(self.guild_id)
        if sub:
            sub["status"] = "rejected"
            save(SUBS_FILE, subs)

        # DM server owner
        guild = bot.get_guild(int(self.guild_id))
        await self.dm_server_owner(
            guild,
            "❌ Your **EasyGPT subscription** request has been **rejected**."
        )

        await interaction.response.send_message("❌ Subscription rejected.", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)


@tree.command(name="subscribe", description="Request EasyGPT subscription")
@app_commands.checks.has_permissions(administrator=True)
async def subscribe(interaction: discord.Interaction):

    subs = load(SUBS_FILE)
    gid = str(interaction.guild.id)

    if gid in subs and subs[gid]["status"] in ("pending", "active"):
        return await interaction.response.send_message(
            "⚠️ This server already has a pending or active subscription.",
            ephemeral=True
        )

    subs[gid] = {
        "status": "pending",
        "guild_name": interaction.guild.name,
        "requested_by": interaction.user.id,
        "requested_at": datetime.utcnow().isoformat()
    }
    save(SUBS_FILE, subs)

    owner = bot.get_user(BOT_OWNER_ID)
    if owner:
        await owner.send(
            embed=discord.Embed(
                title="📩 New Subscription Request",
                description=(
                    f"**Server:** {interaction.guild.name}\n"
                    f"**Server ID:** `{interaction.guild.id}`\n"
                    f"**Requested by:** <@{interaction.user.id}>"
                ),
                color=0x5865F2
            ),
            view=SubApprovalView(gid)
        )

    await interaction.response.send_message(
        "✅ Subscription request sent.\nComplete payment and wait for approval.",
        ephemeral=True
    )
    

@tree.command(name="subrevoke", description="Revoke subscription for this server (OWNER ONLY)")
async def subrevoke(interaction: discord.Interaction):
    if interaction.user.id != BOT_OWNER_ID:
        return await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)

    subs = load(SUBS_FILE)
    gid = str(interaction.guild.id)

    if gid not in subs or subs[gid]["status"] != "active":
        return await interaction.response.send_message("⚠️ This server does not have an active subscription.", ephemeral=True)

    subs[gid]["status"] = "revoked"
    subs[gid]["revoked_at"] = datetime.utcnow().isoformat()
    subs[gid]["revoked_by"] = interaction.user.id
    save(SUBS_FILE, subs)

    # DM server owner
    owner = interaction.guild.owner
    if owner:
        try:
            await owner.send("🛑 Your **EasyGPT subscription** has been **revoked** by the bot owner. You no longer have access.")
        except discord.Forbidden:
            pass

    await interaction.response.send_message("🛑 **Subscription revoked successfully.** This server no longer has access.", ephemeral=True)

# ================= HELP DROPDOWN =================
class HelpSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="AI", description="Ask AI questions", emoji="🤖"),
            discord.SelectOption(label="Giveaways", description="Start giveaways", emoji="🎁"),
            discord.SelectOption(label="Moderation", description="Kick, Ban, Warn, etc.", emoji="🛡"),
            discord.SelectOption(label="Logs", description="View logs setup", emoji="📊"),
            discord.SelectOption(label="Setup", description="Setup channels & welcome", emoji="⚙️"),
            discord.SelectOption(label="Custom Prefix", description="Set server prefix", emoji="⚡"),
            discord.SelectOption(label="Subscription", description="Subscribe and Trial", emoji="💳"),
            discord.SelectOption(label="Info", description="Information Commands", emoji="ℹ"),
        ]
        super().__init__(placeholder="Select a category", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="✨ EasyGPT Command Center", color=0x5865F2)
        
        if self.values[0] == "AI":
            embed.add_field(name="🤖 AI", value="`/ask <question>` – Ask the AI anything *(subscription required)*", inline=False)
        elif self.values[0] == "Giveaways":
            embed.add_field(name="🎁 Giveaways", value="`/giveaway <prize> <duration> <winners>` – Start a reaction-based giveaway", inline=False)
        elif self.values[0] == "Moderation":
            embed.add_field(name="🛡 Moderation", value="`!clear <amount>`\n`!warn <user> <reason>`\n`!timeout <user> <minutes> <reason>`\n`!kick <user> <reason>`\n`!ban <user> <reason>`", inline=False)
        elif self.values[0] == "Logs":
            embed.add_field(name="📊 Logs", value="`/logchannel <channel>` – Logs joins, leaves, message edits/deletes, role changes, channel & server updates", inline=False)
        elif self.values[0] == "Setup":
            embed.add_field(name="⚙️ Setup", value="`/setup` – Configure allowed AI channels\n`/setwelcome` – Set welcome messages", inline=False)
        elif self.values[0] == "Custom Prefix":
            embed.add_field(name="⚡ Custom Prefix", value="`/setprefix <prefix>` – Set the server's custom prefix", inline=False)
        elif self.values[0] == "Subscription":
            embed.add_field(name="💳 Subscription", value="`/subscribe` – Request access\n`/subrevoke` – Owner only\n`/trial` – Activate a 3-day trial to use `/ask` (once per server)", inline=False)
        elif self.values[0] == "Info":  # NEW
            embed.add_field(name="ℹ️ Info Commands", value="`/avatar [user]` – Show a user's avatar\n`/userinfo [user]` – Show user info\n`/serverinfo` – Show server stats", inline=False)

        embed.set_footer(
    text="EasyGPT • Built by zaidwh0 • Powered by Groq",
    icon_url=interaction.client.user.display_avatar.url
    )

        await interaction.response.edit_message(embed=embed)

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpSelect())


# ================= INFO COMMANDS =================
@tree.command(name="avatar", description="Show a user's profile picture")
@app_commands.describe(user="The user to show avatar for")
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    embed = discord.Embed(title=f"{user.name}'s Avatar", color=0x5865F2)
    embed.set_image(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@tree.command(name="serverinfo", description="Shows server stats")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title=guild.name,
        description=guild.description if guild.description else "No server description.",
        color=0x5865F2
    )

    # Big server icon on the top left
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    # Add stats fields
    embed.add_field(name="📊 Members", value=f"{guild.member_count}", inline=True)
    embed.add_field(name="🛡 Roles", value=f"{len(guild.roles)}", inline=True)
    embed.add_field(name="💬 Channels", value=f"{len(guild.channels)}", inline=True)
    embed.add_field(name="🌐 Boost Level", value=f"{guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
    embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
    embed.add_field(name="📅 Created On", value=guild.created_at.strftime("%d %b %Y"), inline=True)

    await interaction.response.send_message(embed=embed)

# ================= COMMANDS ================

@tree.command(name="welcome", description="Set the welcome channel")
@app_commands.checks.has_permissions(administrator=True)
async def welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load(CONFIG_FILE)

    cfg["welcome_channel"] = channel.id
    save(CONFIG_FILE, cfg)

    await interaction.response.send_message(
        f"✅ Welcome messages will be sent in {channel.mention}",
        ephemeral=True
    )


@tree.command(name="invite", description="Get the bot's invite link")
async def invite(interaction: discord.Interaction):
    invite_url = "https://discord.com/oauth2/authorize?client_id=1449334619815018557&permissions=8&scope=bot%20applications.commands"
    embed = discord.Embed(
        title="🤖 Invite EasyGPT",
        description=f"[Click here to invite EasyGPT to your server]({invite_url})",
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="help", description="Open the EasyGPT command center")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ EasyGPT Command Center",
        description="Select a category from the dropdown below",
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)
    

@tree.command(name="trial", description="Start a 3-day trial for EasyGPT AI (one-time per server)")
async def trial(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    subs = load(SUBS_FILE)

    if gid in subs and subs[gid]["status"] in ("active", "pending", "trial_used"):
        return await interaction.response.send_message(
            "⚠️ Trial already used or an active subscription exists.", ephemeral=True
        )

    start = datetime.utcnow()
    end = start + timedelta(days=3)

    subs[gid] = {
        "status": "active",
        "type": "trial",
        "start": start.isoformat(),
        "end": end.isoformat()
    }
    save(SUBS_FILE, subs)

    await interaction.response.send_message(
        f"✅ Trial activated! You can now use `/ask` for 3 days until <t:{int(end.timestamp())}:F>.",
        ephemeral=True
    )


@bot.hybrid_command(name="setprefix", description="Set a custom prefix for this server")
@commands.has_permissions(administrator=True)
async def setprefix(ctx, prefix: str):
    prefixes = get_prefixes()
    prefixes[str(ctx.guild.id)] = prefix
    save_prefixes(prefixes)
    await ctx.send(f"✅ Prefix updated to `{prefix}` for this server")

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="✨ EasyGPT Command Center", description="Select a category from the dropdown below", color=0x5865F2)
    await ctx.send(embed=embed, view=HelpView())


async def dm_user(member: discord.Member, message: str):
    try:
        await member.send(message)
    except discord.Forbidden:
        pass  # DMs are closed, ignore


@bot.hybrid_command(name="clear", description="Delete messages in bulk")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0 or amount > 100:
        return await ctx.send("❌ Amount must be between 1 and 100")

    deleted = await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(f"🧹 **Cleared {len(deleted)-1} messages**")
    await asyncio.sleep(3)
    await msg.delete()


@bot.hybrid_command(name="warn", description="Warn a member")
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason):
    warns = load("warns.json") if os.path.exists("warns.json") else {}
    gid, uid = str(ctx.guild.id), str(member.id)

    warns.setdefault(gid, {}).setdefault(uid, [])
    warns[gid][uid].append({
        "reason": reason,
        "by": ctx.author.id,
        "time": datetime.utcnow().isoformat()
    })

    save("warns.json", warns)
    await ctx.send(f"⚠️ **Warned** {member.mention}\nReason: {reason}")


# Timeout command
@bot.hybrid_command(name="timeout", description="Temporarily timeout a member")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    # Check bot permissions
    if not ctx.guild.me.guild_permissions.moderate_members:
        return await ctx.send("❌ I do not have permission to timeout members.")

    # Check role hierarchy
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You cannot timeout this member due to role hierarchy.")
    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send("❌ I cannot timeout this member because their role is higher than mine.")

    # Calculate timeout datetime
    until = datetime.utcnow() + timedelta(minutes=minutes)

    # Attempt to DM the user
    await dm_user(
        member,
        f"You have been timed out in **{ctx.guild.name}** for {minutes} minutes.\n"
        f"Reason: {reason}\nModerator: {ctx.author}"
    )

    # Apply the timeout
    try:
        await member.edit(timeout=until, reason=reason)
    except Exception as e:
        return await ctx.send(f"❌ Failed to timeout the member: {e}")

    # Confirm to command user
    await ctx.send(f"⏱ {member.mention} has been timed out for {minutes} minutes.\nReason: {reason}")

@bot.hybrid_command(name="kick", description="Kick a member")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ You can’t kick this user.")

    await member.kick(reason=reason)
    await ctx.send(f"👢 **Kicked** {member.mention}\nReason: {reason}")


@bot.hybrid_command(name="ban", description="Ban a member")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ You can’t ban this user.")

    await member.ban(reason=reason)
    await ctx.send(f"🔨 **Banned** {member.mention}\nReason: {reason}")


@tree.command(name="ask")
async def ask(interaction, question: str):
    if not is_active(interaction.guild.id):
        return await interaction.response.send_message("🚫 No subscription", ephemeral=True)
    await interaction.response.defer(thinking=True)
    reply = await fetch_ai(question)
    await interaction.followup.send(reply)

# ================= EVENTS =================

WELCOME_BANNERS = [
    "https://i.pinimg.com/originals/51/2f/c3/512fc362a4ca2663778db016c2b7f703.gif",
    "https://i.pinimg.com/originals/ff/34/3a/ff343aa8819c2573ad3409baf4af5e3e.gif",
    "https://i.pinimg.com/originals/41/60/61/416061b9d95e206d7bbeb51e644cca6e.gif",
    "https://i.pinimg.com/originals/18/b1/77/18b177f65bd1119ce41186d0d0959910.gif",
    "https://i.pinimg.com/originals/29/9d/7c/299d7cccb5263b70e10aa312a8c41cc6.gif",
    "https://i.pinimg.com/originals/70/37/d4/7037d478852af21357f038fac2d2e9f6.gif",
    "https://i.pinimg.com/originals/29/e5/5c/29e55c6087d9cdeea86c91f6dcf52ba1.gif",
    "https://i.pinimg.com/originals/6f/10/ae/6f10aeb8bbfa771da23e0f13ee409463.gif",
    "https://i.pinimg.com/originals/8c/0b/e0/8c0be00493d066019b27416d4df3e9e6.gif",
    "https://i.pinimg.com/originals/a1/1d/41/a11d416a30a7a0d4c75a51bdba5d6670.gif",
    "https://i.pinimg.com/originals/fa/8b/ab/fa8bab291d3e6866db2e8d049bd8f453.gif",
    "https://i.pinimg.com/originals/fb/51/a7/fb51a7031951124fba1515356535e84c.gif",
    "https://i.pinimg.com/originals/35/c9/33/35c93381f2a65582e6dfc5d077e71cbd.gif",
    "https://i.pinimg.com/originals/57/f8/25/57f8258b3548c13d53ee2a888e70a127.gif",
    # Add as many URLs as you want
]

@bot.event
async def on_member_join(member):
    cfg = load(CONFIG_FILE)
    ch = member.guild.get_channel(cfg.get("welcome_channel"))
    if not ch:
        return

    banner_url = random.choice(WELCOME_BANNERS)

    embed = discord.Embed(
        title=f"Welcome to {member.guild.name}!",
        description=f"Hey {member.mention}, glad you joined us!",
        color=0x5865F2,
        timestamp=datetime.utcnow()
    )

    embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
    embed.set_image(url=banner_url)
    embed.set_footer(text="EasyGPT • Enjoy your stay!")

    await ch.send(embed=embed)

    # Log
    await send_log(
        member.guild,
        "👤 Member Joined",
        f"{member.mention} | {member.name}#{member.discriminator}\nTotal Members: {member.guild.member_count}",
        color=0x2ecc71
    )

@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)

    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    check_subscriptions.start()
    print("⚡ Commands synced instantly to dev server")

bot.run(TOKEN)
