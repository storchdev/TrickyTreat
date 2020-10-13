from discord.ext.menus import Menu, button
import discord


class BaseMenu(Menu):

    def __init__(self, pages):
        super().__init__(timeout=30, clear_reactions_after=True)
        self.page = 0
        self.pages = pages
        self.title = None

    async def send_initial_message(self, ctx, channel):
        if len(self.pages) == 1:
            await ctx.send(embed=self.embed)
            await self.stop()
        else:
            return await ctx.send(embed=self.embed)

    async def desc(self):
        pass

    async def embed(self):
        embed = discord.Embed(
            title=self.title,
            description=(await self.desc())[self.page],
            color=discord.Colour.dark_orange()
        )
        embed.set_author(
            name=f'Page {self.page + 1} of {len(self.pages)}',
            icon_url=self.bot.get_pfp(self.ctx.author)
        )
        return embed

    @button('\u23ee')
    async def first(self, payload):
        if self.page:
            self.page = 0
            await self.message.edit(embed=await self.embed())

    @button('\u2b05')
    async def previous(self, payload):
        if self.page:
            self.page -= 1
            await self.message.edit(embed=await self.embed())

    @button('\u27a1')
    async def next(self, payload):
        if self.page == len(self.pages) - 1:
            self.page += 1
            await self.message.edit(embed=await self.embed())

    @button('\u23ed')
    async def last(self, payload):
        max_len = len(self.pages) - 1
        if self.page == max_len:
            self.page = max_len
            await self.message.edit(embed=await self.embed())

    @button('\U0001f500')
    async def jump(self, payload):
        pass

    @button('\u23f9')
    async def stop(self, payload):
        try:
            await self.message.clear_reactions()
        finally:
            await self.stop()
