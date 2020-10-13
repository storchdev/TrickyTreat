import discord
from discord.ext import commands
from emoji import UNICODE_EMOJI


class CannotMakeGiveaways(commands.CheckFailure):
    pass


class EmojiConverter(commands.Converter):

    async def convert(self, ctx, argument):
        try:
            emoji = await commands.EmojiConverter().convert(ctx, argument)
            return emoji
        except commands.BadArgument:
            if argument in UNICODE_EMOJI:
                return argument
            else:
                raise commands.EmojiNotFound(argument)


def is_giveaway_manager():
    def predicate(ctx):
        if not ctx.author.guild_permissions.manage_guild:
            if not any(
                    [name for name in ('giveaways', 'giveaway manager', 'giveaway managers')
                     if name in [role.name.lower() for role in ctx.author.roles]]
            ):
                raise CannotMakeGiveaways()
        return True

    return commands.check(predicate)


async def can_enter(bot, member, message_id: int) -> bool:
    query = '''SELECT guild_req, role_req, role_req_type
               FROM giveaways
               WHERE message_id = $1
            '''
    res = await bot.db.fetchrow(query, message_id)
    if res:
        role_req = res['role_req']
        guild_req = res['guild_req']
        role_req_type = res['role_req_type']
        if role_req:
            if role_req_type == 0:
                for role_id in role_req:
                    if role_id not in (role.id for role in member.roles):
                        return False
            else:
                if not any(role_id not in (role.id for role in member.roles)
                           for role_id in role_req):
                    return False
        if guild_req:
            if member.id not in (gm.id for gm in bot.get_guild(guild_req)):
                return False
        return True


def get_pfp(user) -> str:
    fmt = 'gif' if user.is_avatar_animated() else 'png'
    return str(user.avatar_url_as(format=fmt))


def get_icon(guild: discord.Guild) -> str:
    fmt = 'gif' if guild.is_icon_animated() else 'png'
    return str(guild.icon_url_as(format=fmt))


async def send_error(ctx, title: str, nv: tuple):
    sig = ctx.command.signature.replace('_', ' ')
    usage = f'{ctx.prefix.lower()}{ctx.invoked_with} {sig}'
    embed = discord.Embed(
        title=title,
        color=discord.Colour.dark_red(),
    ).add_field(
        name='Usage',
        value=f'`{usage}`',
        inline=False
    ).add_field(
        name=nv[0],
        value=nv[1],
        inline=False
    )
    await ctx.send(embed=embed)
