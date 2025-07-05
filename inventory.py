import discord
from discord.ext import commands
import json
import os
import math
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

RARITY_ORDER = {
    "Common": 0,
    "Uncommon": 1,
    "Rare": 2,
    "Epic": 3,
    "Legendary": 4,
    "Mythic": 5,
    "Unknown": -1
}

def sort_items(items, key="rarity"):
    if key == "rarity":
        return sorted(items, key=lambda x: RARITY_ORDER.get(x.get("rarity", "Unknown"), 0), reverse=True)
    elif key == "float":
        return sorted(items, key=lambda x: float(x.get("float", "0.00")))
    elif key == "date":
        return sorted(items, key=lambda x: x.get("mint_date", ""), reverse=True)
    else:
        return items

@bot.command()
async def inventory(ctx, sortby: str = "rarity", page: int = 1):
    user_id = str(ctx.author.id)

    if not os.path.exists("items.json"):
        await ctx.send("\U0001f4ed You have no items in your inventory.")
        return

    with open("items.json", "r") as f:
        items = json.load(f)

    user_items = [item for item in items if item.get("owner") == user_id]
    if not user_items:
        await ctx.send("\U0001f4ed You have no items in your inventory.")
        return

    sorted_items = sort_items(user_items, sortby)
    per_page = 5
    total_pages = math.ceil(len(sorted_items) / per_page)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    display_items = sorted_items[start:end]

    summary = "\n".join([
        f"\U0001f4e6 **{item['name']}** [{item['rarity']} • {item['roll_grade']}] – `{item['id']}`"
        for item in display_items
    ])

    await ctx.send(
        f"\U0001f3eb **{ctx.author.display_name}'s Inventory** (Page {page}/{total_pages}, Sorted by `{sortby}`):\n{summary}"
    )

@bot.command()
async def inspect(ctx, item_id: str):
    if not os.path.exists("items.json"):
        await ctx.send("❌ No items found.")
        return

    with open("items.json", "r") as f:
        items = json.load(f)

    item = next((i for i in items if i.get("id") == item_id), None)
    if not item:
        await ctx.send("❌ Item not found.")
        return

    embed = discord.Embed(title=f"🔍 Inspecting: {item['name']}", description=item.get("lore", "No lore."))
    embed.add_field(name="ID", value=item['id'], inline=True)
    embed.add_field(name="Rarity", value=item['rarity'], inline=True)
    embed.add_field(name="Float", value=item['float'], inline=True)
    embed.add_field(name="Grade", value=item['roll_grade'], inline=True)
    embed.add_field(name="Pitch Value", value=f"{item['pitch_value']} PC", inline=True)
    embed.add_field(name="Minted On", value=item['mint_date'], inline=True)
    embed.set_footer(text=f"Owned by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command()
async def sell(ctx, item_id: str):
    user_id = str(ctx.author.id)
    if not os.path.exists("items.json"):
        await ctx.send("❌ No items found.")
        return

    with open("items.json", "r") as f:
        items = json.load(f)

    for item in items:
        if item.get("id") == item_id and item.get("owner") == user_id:
            value = item.get("pitch_value", 0)
            item["owner"] = None
            with open("items.json", "w") as f:
                json.dump(items, f, indent=4)
            with open("wallets.json", "r") as f:
                wallets = json.load(f) if os.path.getsize("wallets.json") > 0 else {}
            wallets[user_id] = wallets.get(user_id, 0) + value
            with open("wallets.json", "w") as f:
                json.dump(wallets, f, indent=4)
            await ctx.send(f"💰 You sold **{item['name']}** for `{value}` Pitch Coins!")
            return

    await ctx.send("❌ Either the item doesn't exist or you don't own it.")

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    if not os.path.exists("wallets.json"):
        wallets = {}
    else:
        with open("wallets.json", "r") as f:
            wallets = json.load(f) if os.path.getsize("wallets.json") > 0 else {}

    balance = wallets.get(user_id, 0)
    await ctx.send(f"💰 {ctx.author.display_name}, you have `{balance}` Pitch Coins.")

@bot.command()
async def trade(ctx, member: discord.Member, item_id: str):
    sender_id = str(ctx.author.id)
    recipient_id = str(member.id)
    if sender_id == recipient_id:
        await ctx.send("❌ You can't trade with yourself.")
        return

    if not os.path.exists("items.json"):
        await ctx.send("❌ No items found.")
        return

    with open("items.json", "r") as f:
        items = json.load(f)

    for item in items:
        if item.get("id") == item_id and item.get("owner") == sender_id:
            item["owner"] = recipient_id
            with open("items.json", "w") as f:
                json.dump(items, f, indent=4)
            await ctx.send(f"🔁 {ctx.author.display_name} has traded **{item['name']}** to {member.mention}!")
            return

    await ctx.send("❌ Either the item doesn't exist or you don't own it.")

# gift and giftcoins updated already to ask for anonymity
