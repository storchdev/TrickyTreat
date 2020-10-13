from discord.ext import commands
from parsedatetime import Calendar
import discord
import time
import json
from humanize import precisedelta
from cogs.utils import is_giveaway_manager, EmojiConverter
from datetime import datetime
import asyncio
import re
from cogs.tasks import end


class Giveaway(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.time_parser = Calendar()
        self.min_time = 5
        self.bold = re.compile(r'(\d+)')

    async def prompt(self, ctx, prompt: str):
        await ctx.send(prompt)

        def check(m):
            return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

        try:
            msg = await self.bot.wait_for('message', timeout=420, check=check)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title='Timeout',
                descripton='You took too long to respond to my prompt. '
                           'Please restart the command and try again.'
            )
            await ctx.send(embed=embed)
            return None
        return msg.content

    async def create_giveaway(self, ctx, prize, channel, total_time,
                              winners, desc, req_int, role_reqs, invite, req_text, emoji):
        ts = int(time.time() + total_time)
        final_req_text = ''
        req = req_text
        if req:
            final_req_text += req
        else:
            if role_reqs:
                if req_int:
                    req_text += '\U0001f4dd __Must have any of the following roles:__ '
                else:
                    req_text += '\U0001f4dd __Must have all of the following roles:__ '
                req_text += ', '.join(role.mention for role in role_reqs)
            if invite:
                req_text += f'\n\U0001f4dd __Must be in the server:__ ' \
                            f'[**{invite.guild.name}**]({invite})'
        final_req_text = final_req_text or 'No requirements'
        s = '' if winners == 1 else 's'

        embed = discord.Embed(
            title=prize,
            description=desc,
            color=discord.Colour.dark_orange(),
            timestamp=datetime.utcfromtimestamp(ts)
        ).add_field(
            name='\U0001f60e Requirements:',
            value=final_req_text,
            inline=False
        ).add_field(
            name='\u23f0 Ends In:',
            value=self.bold.sub(r'**\1**', precisedelta(total_time)),
            inline=False
        ).add_field(
            name='\U0001f451 Host:',
            value=ctx.author.mention,
            inline=False
        ).set_author(
            name='New Giveaway!',
            icon_url=self.bot.get_icon(ctx.guild)
        ).set_footer(
            text=str(winners) + f' Winner{s} | Ending at ->'
        )
        msg = await channel.send(embed=embed)
        await msg.add_reaction(emoji)

        role_ids = [role.id for role in role_reqs]

        query = '''INSERT INTO giveaways (
                   guild_id, 
                   channel_id,
                   message_id,
                   embed,
                   prize,
                   winners_num,
                   role_req,
                   role_req_type,
                   guild_req,
                   ends_at,
                   ended
                   )
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                '''
        ended = False if total_time > 30 else True
        dumped = json.dumps(msg.embeds[0].to_dict(), indent=4)
        values = (ctx.guild.id, channel.id, msg.id, dumped,
                  prize, winners, role_ids, req_int,
                  invite.guild.id if invite else None,
                  ts, ended)
        self.bot.message_ids.append(msg.id)
        await self.bot.db.execute(query, *values)

        ping = discord.utils.find(lambda r: 'giveaway ping' in r.name.lower(), ctx.guild.roles)
        if ping:
            msg = await channel.send(ping.mention)
            await msg.delete()

        if ctx.channel.id != channel.id:
            await ctx.send('Giveaway created!')

        if total_time < 30:
            await end(self.bot, ts, msg.id, channel.id, dumped)

    @commands.command(aliases=['create'])
    @is_giveaway_manager()
    async def giveaway(self, ctx):
        channel = await self.prompt(ctx, 'What channel is this giveaway in?')
        try:
            channel = await commands.TextChannelConverter().convert(ctx, channel)
        except commands.ChannelNotFound:
            return await ctx.send('Invalid channel.')

        prize = await self.prompt(ctx, 'What are you giving away?')
        if not prize:
            return

        winners = await self.prompt(ctx, 'How many winners will there be?')
        if not winners:
            return
        try:
            winners = int(winners)
        except ValueError:
            return await ctx.send('Invalid number.')
        if winners < 1:
            return await ctx.send('Must be greater than 1.')

        t = await self.prompt(ctx, 'How long will the giveaway last?')
        if not t:
            return
        parsed = self.time_parser.parse(t)
        ts = time.mktime(parsed[0])
        total = int(ts - time.time())
        if not total:
            return await ctx.send('Invalid time.')

        desc = await self.prompt(ctx, 'Enter a description for this giveaway (150 chars max) '
                                      'or type `skip`.')
        if not desc:
            return

        while len(desc) > 150:
            desc = await self.prompt(ctx, 'Not under 150 characters. Try again.')
            if not desc:
                return
        if desc.lower() == 'skip':
            desc = ''

        roles = await self.prompt(ctx, 'What are the role requirements to enter? '
                                       'Enter comma-separated role names/IDs/mentions. '
                                       'Type `skip` for no role requirements.')
        if not roles:
            return
        role_reqs = []
        req_int = 0
        if roles.lower() != 'skip':
            rc = commands.RoleConverter()
            roles = roles.replace(', ', ',').split(',')
            for role in roles:
                try:
                    role_reqs.append(await rc.convert(ctx, role))
                except commands.RoleNotFound as err:
                    return await ctx.send(f'`{err.argument}` is not a valid role. Try again.')
            req_type = await self.prompt(ctx, 'Does the user need **all** the roles to enter, '
                                              'or **any** of the roles to enter? '
                                              'Respond with `all` or `any`.')
            if not req_type:
                return
            if req_type.lower() == 'all':
                req_int = 0
            elif req_type.lower() == 'any':
                req_int = 1
            else:
                return await ctx.send('Not a valid option.')

        invite_obj = None
        invite = await self.prompt(ctx, 'What server does this user have to be in '
                                        'to enter the giveaway? Enter a **permanent '
                                        'invite link that has infinite uses** or type '
                                        '`skip`.')
        if not invite:
            return
        if invite.lower() != 'skip':
            ic = commands.InviteConverter()
            try:
                invite = await ic.convert(ctx, invite)
            except commands.BadInviteArgument:
                return await ctx.send(f'`{invite}` was not a valid invite.')

            if invite.max_uses or invite.max_age:
                return await ctx.send('The invite provided is not permanent '
                                      'and does not have infinite usage.')

            if isinstance(invite, discord.PartialInviteGuild):
                return await ctx.send('I am not in the server with that invite.')
            in_guild = invite.guild.get_member(ctx.author.id)
            if not in_guild:
                return await ctx.send('You must also be in that server to '
                                      'set it as a requirement.')
            invite_obj = invite

        req_text = await self.prompt(ctx, 'Enter a manual requirement text, '
                                          'or type `skip`.')
        if not req_text:
            return
        if req_text.lower() == 'skip':
            req_text = ''

        emoji = await self.prompt(ctx, 'Enter an emoji that will be reacted for entering, '
                                       'or type `skip` for the default :tada:')
        if not emoji:
            return
        if emoji.lower() == 'skip':
            emoji = '\U0001f389'
        else:
            try:
                emoji = await EmojiConverter().convert(ctx, emoji)
            except commands.EmojiNotFound:
                return await ctx.send(f'`{emoji}` was not a valid emoji. '
                                      "Make sure I am also in the emoji's server")

        await self.create_giveaway(ctx, prize, channel, total, winners, desc,
                                   req_int, role_reqs, invite_obj, req_text, emoji)


def setup(bot):
    bot.add_cog(Giveaway(bot))
