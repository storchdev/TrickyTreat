from discord.ext import commands, tasks
import time 
import asyncio 
import json
import discord
from humanize import precisedelta
import random
from datetime import datetime
from cogs.utils import can_enter
import re


bold = re.compile(r'(\d+)')


def edit_field(embed: discord.Embed, index: int, new_value: str):
    name = embed.fields[index].name
    inline = embed.fields[index].inline
    embed.set_field_at(index, name=name, value=new_value, inline=inline)
    return embed


async def end(bot, ends_at: int, message_id: int, channel_id: int, embed):
    interval = 5
    message = await bot.get_channel(channel_id).fetch_message(message_id)
    embed = discord.Embed.from_dict(json.loads(embed))
    left = int(ends_at - time.time())
    remaining = left % interval
    for i in range(left // interval):
        embed = edit_field(embed, 1, bold.sub(r'**\1**', precisedelta(left)))
        await message.edit(embed=embed)
        await asyncio.sleep(interval)
        left -= interval
    await asyncio.sleep(remaining)

    prize = embed.title
    embed.title = 'LAST CHANCE TO ENTER!!!'
    left = interval
    for i in range(interval):
        embed = edit_field(embed, 1, bold.sub(r'**\1**', precisedelta(left)))
        embed.colour = discord.Colour.red()
        await message.edit(embed=embed)
        left -= 1
        await asyncio.sleep(1)
    
    query = 'SELECT winners_num, prize FROM giveaways WHERE message_id = $1'
    res = await bot.db.fetchrow(query, message_id)
    users = await message.reactions[0].users().flatten()
    if message.guild.me in users:
        users.remove(message.guild.me)
    winners = []
    if not users:
        await message.channel.send('No one has entered the giveaway.')
    else:
        for i in range(res['winners_num']):
            try:
                winner = random.choice(users)
            except IndexError:
                break
            users.remove(winner)
            if await can_enter(bot, winner, message.id):
                winners.append(winner)
        query = '''UPDATE giveaways
                   SET winners = $1
                   WHERE message_id = $2
                '''
        await bot.db.execute(query, [winner.id for winner in winners], message_id)
        bot.message_ids.remove(message_id)

        winners = ', '.join(winner.mention for winner in winners)
        await message.channel.send(f'Congratulations {winners}! '
                                   f'You won the **{prize}**\n{message.jump_url}')

    embed = discord.Embed(
        title=prize,
        description=embed.description,
        color=discord.Colour.dark_orange(),
        timestamp=datetime.utcnow()
    ).add_field(
        name='Winners',
        value=winners or 'No winners.'
    ).set_footer(
        text='Ended at ->'
    )
    await message.edit(embed=embed)


class Tasks(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.update_giveaway_messages.start()

    @tasks.loop(seconds=15)
    async def update_giveaway_messages(self):
        query = '''SELECT channel_id, message_id, embed, ends_at
                   FROM giveaways
                   WHERE ended = $1
                '''
        res = await self.bot.db.fetch(query, False)
        for res in res:
            if res['ends_at'] < time.time() + 32:
                query = '''UPDATE giveaways 
                           SET ended = $1
                           WHERE message_id = $2
                        '''
                await self.bot.db.execute(query, True, res['message_id'])
                args = (
                    self.bot, 
                    res['ends_at'], 
                    res['message_id'],
                    res['channel_id'], 
                    res['embed']
                )
                self.bot.loop.create_task(end(*args))
            else:
                left = res['ends_at'] - time.time()
                embed = discord.Embed.from_dict(json.loads(res['embed']))
                embed = edit_field(embed, 1, bold.sub(r'**\1**', precisedelta(left)))
                try:
                    await self.bot.http.edit_message(
                        res['channel_id'],
                        res['message_id'],
                        embed=embed.to_dict()
                    )
                except discord.NotFound:
                    query = '''UPDATE giveaways
                               SET ended = $1,
                               winners = $2
                               WHERE message_id = $3
                            '''
                    await self.bot.db.execute(query, True, [], res['message_id'])

    @update_giveaway_messages.error
    async def ugm_error(self, error):
        print(type(error))
        raise error


def setup(bot):
    bot.add_cog(Tasks(bot))
