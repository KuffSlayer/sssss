import sqlite3
import discord
from discord.ext import commands
from tools.checks import Owners
from cogs.auth import owners


class owner(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        conn = sqlite3.connect('blacklist.db')
        cursor = conn.cursor()

        # create table if it does not exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                state TEXT
            )
        """)

    @commands.command(aliases=["guilds"])
    @Owners.check_owners()
    async def servers(self, ctx: commands.Context):
        def key(s):
            return s.member_count
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        lis = [g for g in self.bot.guilds]
        lis.sort(reverse=True, key=key)
        for guild in lis:
            mes = f"{mes}`{k}` {guild.name} ({guild.id}) - ({guild.member_count})\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(discord.Embed(
                    color=self.bot.color, title=f"guilds ({len(self.bot.guilds)})", description=messages[i]))
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(discord.Embed(color=self.bot.color,
                      title=f"guilds ({len(self.bot.guilds)})", description=messages[i]))
        await ctx.paginator(number)

    @commands.command()
    @Owners.check_owners()
    async def portal(self, ctx, id: int):
        await ctx.message.delete()
        guild = self.bot.get_guild(id)
        for c in guild.text_channels:
            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()
                await ctx.author.send(f"{guild.name} invite link - {invite}")
                break

    @commands.command()
    @Owners.check_owners()
    async def unblacklist(self, ctx, *, member: discord.User):
        conn = sqlite3.connect('blacklist.db')
        cursor = conn.cursor()
        check = cursor.execute(
            "SELECT * FROM nodata WHERE user_id = ?", (member.id,)).fetchone()
        if check is None:
            return await ctx.send_warning(f"{member.mention} is not blacklisted")
        cursor.execute("DELETE FROM nodata WHERE user_id = ?", (member.id,))
        conn.commit()
        await ctx.send_success(f'{member.mention} can use the bot')

    @commands.command()
    @Owners.check_owners()
    async def blacklist(self, ctx: commands.Context, *, member: discord.User):
        conn = sqlite3.connect('blacklist.db')
        cursor = conn.cursor()
        if member.id in owners:
            return await ctx.reply("Do not blacklist a bot owner, retard")
        check = cursor.execute(
            "SELECT * FROM nodata WHERE user_id = ? AND state = ?", (member.id, "false")).fetchone()
        if check is not None:
            return await ctx.send_warning(f"{member.mention} is already blacklisted")
        cursor.execute("DELETE FROM nodata WHERE user_id = ?", (member.id,))
        cursor.execute(
            "INSERT INTO nodata (user_id, state) VALUES (?, ?)", (member.id, "false"))
        conn.commit()
        await ctx.send_success(f"{member.mention} can no longer use the bot")


async def setup(bot) -> None:
    await bot.add_cog(owner(bot))
