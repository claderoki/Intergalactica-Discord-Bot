import discord

async def get_context_embed(message : discord.Message, amount = 5) -> discord.Embed:
    """Returns an embed showing the context of a message (the conversation that lead to the message)."""
    embed = discord.Embed()
    lines = []
    lines.append("\n**Context:**")

    messages = []
    async for msg in message.channel.history(limit = amount, before = message):
        messages.insert(0, msg)
    messages.append(message)

    last_author = None
    fields = []
    for msg in messages:
        content = msg.content

        if not content:
            if len(msg.embeds) > 0:
                content = "[embed]"
            if len(msg.attachments) > 0:
                content = "[attachment(s)]"

        if last_author is not None and last_author.id == msg.author.id:
            fields[-1]["value"] += f"\n{content}"
        else:
            fields.append({"name": str(msg.author), "value": content})

        last_author = msg.author

    for field in fields:
        embed.add_field(**field, inline = False)

    embed.description = "\n".join(lines)

    return embed

