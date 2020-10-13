from discord.ext import commands
from cogs.utils import can_enter


class Reactions(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.message_id in self.bot.message_ids:
            if not await can_enter(self.bot, payload.member, payload.message_id):
                await self.bot.http.remove_reaction(
                    payload.channel_id,
                    payload.message_id,
                    payload.emoji,
                    payload.user_id
                )


def setup(bot):
    bot.add_cog(Reactions(bot))
