import sqlite3
import discord
from discord.ext import commands
from tools.utils import EmbedBuilder
from tools.checks import Perms


class Greet(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        conn = sqlite3.connect('greet.db')
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS welcome (
                    guild_id INTEGER PRIMARY KEY,
                    message TEXT,
                    channel_id INTEGER
                    )''')
        conn.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        conn = sqlite3.connect('greet.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM welcome WHERE guild_id = ?",
                    (member.guild.id,))
        res = cur.fetchone()
        if res:
            channel = member.guild.get_channel(res[2])
            if channel is None:
                return
            try:
                x = await EmbedBuilder.to_object(EmbedBuilder.embed_replacement(member, res[1]))
                await channel.send(content=x[0], embed=x[1], view=x[2])
            except:
                await channel.send(EmbedBuilder.embed_replacement(member, res[1]))

    @commands.group(aliases=["welc"], invoke_without_command=True)
    async def welcome(self, ctx):
        await ctx.create_pages()

    @welcome.command(name="variables", help="config", description="return the variables for the welcome message")
    async def welcome_variables(self, ctx: commands.Context):
        await ctx.send(self.bot.get_command('embed variables'))

    @welcome.command(name="config", help="config", description="returns stats of the welcome message")
    async def welcome_config(self, ctx: commands.Context):
        conn = sqlite3.connect('greet.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM welcome WHERE guild_id = ?",
                    (ctx.guild.id,))
        res = cur.fetchone()
        if not res:
            return await ctx.send("Welcome is not **configured**")
        channel = f'#{ctx.guild.get_channel(res[2]).name}' if ctx.guild.get_channel(
            res[2]) else "none"
        e = res[1] or "none"
        embed = discord.Embed(
            color=self.bot.color, title=f"channel {channel}", description=f"```{e}```")
        await ctx.reply(embed=embed)

    @welcome.command(name="message", help="config", description="configure the welcome message", brief="manage guild", usage="[message]")
    @Perms.get_perms("manage_guild")
    async def welcome_message(self, ctx: commands.Context, *, code: str):
        conn = sqlite3.connect('greet.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM welcome WHERE guild_id = ?",
                    (ctx.guild.id,))
        check = cur.fetchone()
        if check:
            cur.execute(
                "UPDATE welcome SET message = ? WHERE guild_id = ?", (code, ctx.guild.id))
        else:
            cur.execute("INSERT INTO welcome VALUES (?,?,?)",
                        (ctx.guild.id, 0, code))
        conn.commit()
        return await ctx.send(f"Configured welcome message as `{code}`")

    @welcome.command(name="channel", help="config", description="configure the welcome channel", brief="manage guild", usage="[channel]")
    @Perms.get_perms("manage_guild")
    async def welcome_channel(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        conn = sqlite3.connect('greet.db')
        cur = conn.cursor()
        if channel is None:
            cur.execute(
                "SELECT channel_id FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
            check = cur.fetchone()
            if not check:
                return await ctx.send("Welcome **channel** is not configured")
            cur.execute(
                "UPDATE welcome SET channel_id = ? WHERE guild_id = ?", (None, ctx.guild.id))
            conn.commit()
            return await ctx.send("Removed the welcome **channel**")
        else:
            cur.execute(
                "SELECT channel_id FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
            check = cur.fetchone()
            if check:
                cur.execute(
                    "UPDATE welcome SET channel_id = ? WHERE guild_id = ?", (channel.id, ctx.guild.id))
            else:
                cur.execute("INSERT INTO welcome VALUES (?,?,?)",
                            (ctx.guild.id, channel.id, None))
            conn.commit()
            await ctx.send("Configured welcome **channel** to {}".format(channel.mention))

    @welcome.command(name="delete", help="config", description="delete the welcome module", brief="manage guild")
    @Perms.get_perms("manage_guild")
    async def welcome_delete(self, ctx: commands.Context):
        conn = sqlite3.connect('greet.db')
        cur = conn.cursor()
        check = await cur.execute("SELECT * FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
        if not check.fetchone():
            return await ctx.send("Welcome module is not configured")
        await cur.execute("DELETE FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
        await cur.commit()
        await ctx.send("Welcome module is now **disabled**")

    @welcome.command(name="test", help="config", description="test welcome module", brief="manage guild")
    @Perms.get_perms("manage_guild")
    async def welcome_test(self, ctx: commands.Context):
        conn = sqlite3.connect('greet.db')
        c = conn.cursor()
        c.execute("SELECT * FROM welcome WHERE guild_id = ?", (ctx.guild.id,))
        res = c.fetchone()
        conn.close()

        if res:
            channel = ctx.guild.get_channel(res[1])
            print(res[1])
            if channel is None:
                return await ctx.send("Channel **not** found")
            try:
                x = await EmbedBuilder.to_object(EmbedBuilder.embed_replacement(ctx.author, res[2]))
                await channel.send(content=x[0], embed=x[1], view=x[2])
            except:
                await channel.send(EmbedBuilder.embed_replacement(ctx.author, res[2]))
            await ctx.send("Sent the **welcome** message to {}".format(channel.mention))


async def setup(bot: commands.Bot):
    await bot.add_cog(Greet(bot))
