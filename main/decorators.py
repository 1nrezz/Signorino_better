import discord
from discord.ext.commands import check

#ДЕКОРАТОРЫ

def has_role(role_name: str):
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=role_name)
        return role is not None
    return check(predicate)

def in_category(category_name: str):
    async def predicate(ctx):
        if ctx.channel.category and ctx.channel.category.name == category_name:
            return True
        return False
    return check(predicate)