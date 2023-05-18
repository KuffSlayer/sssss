import sqlite3
import discord
from discord.ext import commands
from tools.checks import Perms, Mod


class Misc(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        conn = sqlite3.connect('autolookup.db')

# Create the autotags table if it doesn't exist
        conn.execute('''CREATE TABLE IF NOT EXISTS autotags
                        (guild_id INTEGER PRIMARY KEY,
                        channel_id INTEGER,
                        url TEXT)''')

        # Close the database connection
        conn.close()

    async def webhook_channel(self, url) -> discord.TextChannel | None:
        r = await self.bot.session.get(url)
        data = (await r.json())['channel_id']
        return self.bot.get_channel(int(data))

    @commands.group(name="webhook", invoke_without_command=True)
    async def webhook(self, ctx):
        await ctx.create_pages()

    @commands.group(invoke_without_command=True, aliases=['autotags'])
    async def autolookup(self, ctx):
        return await ctx.create_pages()

    @autolookup.command(name="set", help="config", usage="[channel]", brief="manage server", description="set an autolookup channel where the recently available 0001 tags will be shown")
    @Perms.get_perms('manage_guild')
    async def autotags_set(self, ctx: commands.Context, *, channel: discord.TextChannel):
        check = await self.bot.db.execute("SELECT * FROM autotags WHERE guild_id = ?", (ctx.guild.id,))
        check = check.fetchone()

        async def create_idk():
            webhook = await channel.create_webhook(name="Tough - autolookup", avatar=await self.bot.user.display_avatar.read(), reason=f"autolookup channel configured by {ctx.author}")
            self.bot.db.execute(
                "INSERT INTO autotags VALUES (?,?,?)", (ctx.guild.id, channel.id, webhook.url))

        if not check:
            await create_idk()
        else:
            try:
                webhook = discord.Webhook.from_url(
                    check[2], session=self.bot.session)
                await webhook.edit(channel=channel, reason=f"autolookup channel changed by {ctx.author}")
                self.bot.db.execute(
                    "UPDATE autotags SET channel_id = ? WHERE guild_id = ?", (channel.id, ctx.guild.id))
            except:
                self.bot.db.execute(
                    "DELETE FROM autotags WHERE guild_id = ?", (ctx.guild.id,))
                await create_idk()
        return await ctx.send(f"The **autolookup** channel is now configured to **{channel.mention}**")

    @autolookup.command(name="unset", help="config", aliases=['remove', 'rmv'], brief="manage server", description="unset an autolookup channel")
    @Perms.get_perms('manage_guild')
    async def autotags_unset(self, ctx: commands.Context):
        check = await self.bot.db.execute("SELECT * FROM autotags WHERE guild_id = ?", (ctx.guild.id,))
        check = check.fetchone()
        if not check:
            return await ctx.send("**Autolookup** is not configured")

        try:
            webhook = discord.Webhook.from_url(
                check[2], session=self.bot.session)
            await webhook.delete(reason=f"autolookup channel removed by {ctx.author}")
        except:
            pass

        self.bot.db.execute(
            "DELETE FROM autotags WHERE guild_id = ?", (ctx.guild.id,))
        return await ctx.send("Removed the **autolookup** channel")

    @webhook.group(name="edit", invoke_without_command=True, description="edit a webhook")
    async def webhook_edit(self, ctx):
        return await ctx.create_pages()

    @webhook_edit.command(name="name", description="edit a webhook's name", help="config", usage="[code] [name]", brief="manage server")
    @Perms.get_perms('manage_guild')
    async def webhook_name(self, ctx: commands.Context, code: str, *, name: str):
        check = self.bot.db.execute(
            "SELECT * FROM webhook WHERE code = $1 AND guild_id = $2", code, (ctx.guild.id,))
        if not check:
            return ctx.send("No **webhook** associated with this code")
        webhook = discord.Webhook.from_url(
            check['url'], session=self.bot.session)
        if webhook:
            await webhook.edit(name=name, reason=f"webhook edited by {ctx.author}")
            return await ctx.send(f"Webhook name changed in **{name}**")
        else:
            return ctx.send(f"No **webhook** found")


async def setup(bot: commands.AutoShardedBot) -> None:
    await bot.add_cog(Misc(bot))
