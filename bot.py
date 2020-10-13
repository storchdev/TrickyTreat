from config import *
from cogs.prefix import get_prefix
import asyncpg
from cogs.utils import *


class TrickyTreat(commands.AutoShardedBot):

    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            intents=discord.Intents.all()
        )

    async def on_command_error(self, ctx, err):
        if isinstance(err, commands.CommandNotFound):
            return

        if isinstance(err, commands.MissingRequiredArgument):
            missing = err.param.name.replace('_', ' ')
            await send_error(ctx, 'Argument Missing', ('Missing:', f'**{missing}**'))
        elif isinstance(err, commands.ChannelNotFound):
            await send_error(ctx, 'Channel Not found', ('Invalid:', err.argument))
        elif isinstance(err, commands.RoleNotFound):
            await send_error(ctx, 'Role Not found', ('Invalid:', err.argument))
        elif isinstance(err, commands.MemberNotFound):
            await send_error(ctx, 'Member Not found', ('Invalid:', err.argument))
        elif isinstance(err, CannotMakeGiveaways):
            embed = discord.Embed(
                title='Unauthorized',
                description='Only users with `Manage Server` perm '
                            'or users with a role called `Giveaways` can create giveaways.',
                color=discord.Colour.red()
            )
            await ctx.send(embed=embed)
        else:
            raise err


COGS = (
    'jishaku',
    'cogs.prefix',
    'cogs.giveaway',
    'cogs.tasks',
    'cogs.reactions'
)
QUERIES = (
    '''CREATE TABLE IF NOT EXISTS prefixes (
       "id" SERIAL PRIMARY KEY,
       "guild_id" BIGINT UNIQUE,
       "prefix" TEXT
       )
    ''',
    '''CREATE TABLE IF NOT EXISTS giveaways (
       "id" SERIAL PRIMARY KEY,
       "guild_id" BIGINT,
       "channel_id" BIGINT,
       "message_id" BIGINT,
       "embed" JSON,
       "prize" TEXT,
       "winners_num" SMALLINT,
       "role_req" BIGINT ARRAY,
       "role_req_type" SMALLINT,
       "guild_req" BIGINT,
       "ends_at" INTEGER,
       "ended" BOOLEAN,
       "winners" BIGINT ARRAY
       )
    '''
)
bot = TrickyTreat()
bot.get_pfp = get_pfp
bot.get_icon = get_icon


async def on_ready():
    await bot.wait_until_ready()

    bot.db = await asyncpg.create_pool(**PG)
    [await bot.db.execute(query) for query in QUERIES]

    query = '''SELECT message_id 
               FROM giveaways 
               WHERE ended = $1
            '''
    bot.message_ids = [res['message_id'] for res in await bot.db.fetch(query, False)]
    [bot.load_extension(cog) for cog in COGS]

    print('ready')


if __name__ == '__main__':
    bot.loop.create_task(on_ready())
    bot.run(TOKEN)
