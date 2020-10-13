from discord.ext import commands
import discord


def get_prefix(bot, message):
    base = [f'<@{bot.user.id}> ', f'<@!{bot.user.id}> ']
    return (bot.prefixes.get(message.guild.id) or ['t!', 'T!']) + base


def insensitive(prefix: str):
    return [
        prefix.lower(),
        prefix.upper(),
        prefix.capitalize()
    ]


class Prefix(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.load())

    async def load(self):
        res = await self.bot.db.fetch('SELECT guild_id, prefix FROM prefixes')
        self.bot.prefixes = {res['guild_id']: insensitive(res['prefix']) for res in res}
        print(self.bot.prefixes)

    @commands.command(aliases=['changeprefix', 'setprefix'])
    async def prefix(self, ctx, new_prefix: str = None):
        """Changes the current server prefix or displays the current one."""

        if not new_prefix:
            prefix = get_prefix(self.bot, ctx.message)[0]
            embed = discord.Embed(
                title=prefix,
                color=discord.Colour.dark_orange()
            ).set_author(
                name='Current Server Prefix',
                icon_url=self.bot.get_icon(ctx.guild)
            ).set_footer(
                text='Admins can provide a new prefix to change the old one'
            )
            return await ctx.send(embed=embed)

        if not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions(['administrator'])

        new_prefix = new_prefix.lower().lstrip()
        self.bot.prefixes[ctx.guild.id] = insensitive(new_prefix)
        query = '''INSERT INTO prefixes (guild_id, prefix)
                   VALUES ($1, $2)
                   ON CONFLICT(guild_id)
                   DO UPDATE SET prefix = $2
                '''
        await self.bot.db.execute(query, ctx.guild.id, new_prefix)

        embed = discord.Embed(
            title=f'Prefix Changed to "{new_prefix}"',
            color=discord.Colour.dark_orange()
        ).set_thumbnail(
            url=self.bot.get_icon(ctx.guild)
        ).set_footer(
            text=f'Do {new_prefix}{ctx.invoked_with} to change it again.'
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Prefix(bot))
