# ========================================================
#  REWARDIUS v8.2 "Market Mayhem Ultra" — Super-Merged
#  (FULL bot: Inventory, Shop, Timers, Mint, Trade, Admin)
#  Last updated: 2025-07-05
# ========================================================

REWARDIUS_VERSION = "v8.2"

import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import json, os, math, asyncio, random
from datetime import datetime, timedelta, timezone

# ========================================================
#           [ SECTION 1: GLOBAL CONSTANTS/CONFIG ]
# ========================================================

GUILD_ID = discord.Object(id=1389242255969091584)
ADMIN_ROLE = "Admin"  # Name of admin role for admin commands

# --- File paths ---
ITEMS_FILE = "items.json"
COIN_FILE = "coins.json"
SHOP_FILE = "shop.json"
SHOP_POOL_FILE = "shop_pool.json"
SECONDHAND_FILE = "secondhand.json"
SHOPLOG_FILE = "shoplog.json"

# --- Rarity, Colors, Category Emoji ---
RARITY_ORDER = {"Common":0,"Uncommon":1,"Rare":2,"Epic":3,"Legendary":4,"Mythic":5,"Unknown":-1}
RARITY_GLYPHS = {"Common":"⚪️","Uncommon":"🟢","Rare":"🔵","Epic":"🟣","Legendary":"🟠","Mythic":"🔴"}
RARITY_COLORS = {
    "Common": discord.Color.light_grey(), "Uncommon": discord.Color.green(), "Rare": discord.Color.blue(),
    "Epic": discord.Color.purple(), "Legendary": discord.Color.orange(), "Mythic": discord.Color.red()
}
CATEGORY_EMOJIS = {
    "Trophy": "🏆", "Cosmetic": "🎨", "Powerup": "⚡", "Bundle": "🎁", "Collectible": "📦", "Rune": "🔮",
    "Special": "✨", "Holiday": "🎄", "Sale": "💸", "Flash": "⚡"
}

# ========================================================
#         [ SECTION 2: HELPERS & FILE I/O ]
# ========================================================

def utcnow(): return datetime.now(timezone.utc)
def ensure_file(fp, val):
    if not os.path.exists(fp):
        with open(fp, "w", encoding="utf-8") as f: json.dump(val, f, indent=2, ensure_ascii=False)
def loadj(fp, default):
    ensure_file(fp, default)
    with open(fp, "r", encoding="utf-8") as f: return json.load(f)
def dumpj(fp, val):
    with open(fp, "w", encoding="utf-8") as f: json.dump(val, f, indent=2, ensure_ascii=False)
def user_is_admin(member): 
    return member.guild_permissions.administrator or any(r.name == ADMIN_ROLE for r in member.roles)
def shoplog(event):  
    logs = loadj(SHOPLOG_FILE, [])
    logs.append(event)
    dumpj(SHOPLOG_FILE, logs)
def parse_dt(dt_str): 
    return datetime.fromisoformat(dt_str) if dt_str else None
def dt_to_hms(dt):
    if not dt: return ""
    delta = dt - utcnow()
    s = max(int(delta.total_seconds()), 0)
    h, m, s = s//3600, (s%3600)//60, s%60
    return f"{h} Hours {m} Minutes {s} Seconds" if h+m+s > 0 else "Expired!"

# ====== [ Shop Pool Initialization: Safe to Edit or Expand! ] ======
def create_sample_shop_pool():
    """
    Run once to generate a sample pool of items for the shop!
    You can expand, copy, or customize this after first run.
    """
    pool = [
        {
            "name": "Golden Boot",
            "emoji": "🥇",
            "description": "Awarded to the highest scorer.",
            "price": 1000,
            "stock": 1,
            "rarity": "Legendary",
            "category": "Trophy"
        },
        {
            "name": "Champion's Cape",
            "emoji": "🧥",
            "description": "For those with winning style.",
            "price": 600,
            "stock": 3,
            "rarity": "Epic",
            "category": "Cosmetic"
        },
        {
            "name": "Lucky Clover",
            "emoji": "🍀",
            "description": "Grants good fortune (probably placebo).",
            "price": 250,
            "stock": 5,
            "rarity": "Uncommon",
            "category": "Powerup"
        },
        {
            "name": "Goalkeeper's Glove",
            "emoji": "🧤",
            "description": "For the brave and the bold.",
            "price": 150,
            "stock": 2,
            "rarity": "Rare",
            "category": "Trophy"
        },
        {
            "name": "Mystery Rune",
            "emoji": "🔮",
            "description": "A rune of unknown power.",
            "price": 333,
            "stock": 1,
            "rarity": "Epic",
            "category": "Rune"
        },
        {
            "name": "Hat Trick Medal",
            "emoji": "🥉",
            "description": "Did you really score 3 in one match?",
            "price": 400,
            "stock": 2,
            "rarity": "Rare",
            "category": "Trophy"
        },
        {
            "name": "Commemorative Coin",
            "emoji": "🪙",
            "description": "A shiny coin for your achievements.",
            "price": 70,
            "stock": 10,
            "rarity": "Common",
            "category": "Collectible"
        },
    ]
    dumpj(SHOP_POOL_FILE, pool)

# Uncomment this for first run to create a pool, then comment out again:
# create_sample_shop_pool()

def random_items_from_shop_pool(n, tag=None, timer_hours=None):
    pool = loadj(SHOP_POOL_FILE, [])
    items = random.sample(pool, min(n, len(pool)))
    now = utcnow()
    # Assign unique ids and timers for shop display
    for item in items:
        item = item.copy()
        item["id"] = f"{item['name'].replace(' ','_')}_{random.randint(1000,9999)}"
        if tag: item["category"] = tag
        if timer_hours:
            item["expires_at"] = (now + timedelta(hours=timer_hours)).isoformat()
        yield item

# ========================================================
#        [ SECTION 3: DISCORD BOT SETUP ]
# ========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ========================================================
#         [ SECTION 4: CURRENCY / COIN LEDGER ]
# ========================================================

def get_balance(user_id):
    ledger = loadj(COIN_FILE, {})
    return float(ledger.get(str(user_id), 0.0))
def set_balance(user_id, amt):
    ledger = loadj(COIN_FILE, {})
    ledger[str(user_id)] = round(float(amt),2)
    dumpj(COIN_FILE, ledger)
def add_coins(user_id, amt): set_balance(user_id, get_balance(user_id)+amt)
def subtract_coins(user_id, amt): set_balance(user_id, max(0.0, get_balance(user_id)-amt))

# ========================================================
#         [ SECTION 5: INVENTORY SYSTEM ]
# ========================================================

def get_inventory(user_id):
    items = loadj(ITEMS_FILE, [])
    return [i for i in items if i.get("owner")==str(user_id)]
def remove_inventory_item(user_id, item_id):
    items = loadj(ITEMS_FILE, [])
    found = False
    for i in items:
        if i.get("owner")==str(user_id) and i.get("id")==item_id:
            items.remove(i)
            found = True
            break
    dumpj(ITEMS_FILE, items)
    return found
def add_inventory_item(item, user_id):
    items = loadj(ITEMS_FILE, [])
    item = item.copy()
    item['owner'] = str(user_id)
    item['mint_date'] = utcnow().isoformat()
    items.append(item)
    dumpj(ITEMS_FILE, items)

# --- Inventory UI (Paginator class & /inventory command) ---
class InventoryPaginator(ui.View):
    def __init__(self, user, items, page, total_pages, sortby, ephemeral, balance, networth):
        super().__init__(timeout=120)
        self.user = user
        self.items = items
        self.page = page
        self.total_pages = total_pages
        self.sortby = sortby
        self.ephemeral = ephemeral
        self.balance = balance
        self.networth = networth

        self.prev_button = ui.Button(label="Previous", style=discord.ButtonStyle.secondary, disabled=(self.page == 1))
        self.next_button = ui.Button(label="Next", style=discord.ButtonStyle.secondary, disabled=(self.page == self.total_pages))
        self.counter_button = ui.Button(label=f"Page {page}/{total_pages}", style=discord.ButtonStyle.gray, disabled=True)
        self.prev_button.callback = self.go_previous
        self.next_button.callback = self.go_next
        self.add_item(self.prev_button)
        self.add_item(self.counter_button)
        self.add_item(self.next_button)
    async def go_previous(self, interaction: discord.Interaction):
        if interaction.user != self.user: await interaction.response.send_message("❌ You're not authorized.", ephemeral=True); return
        if self.page > 1: self.page -= 1; await self.update_page(interaction)
    async def go_next(self, interaction: discord.Interaction):
        if interaction.user != self.user: await interaction.response.send_message("❌ You're not authorized.", ephemeral=True); return
        if self.page < self.total_pages: self.page += 1; await self.update_page(interaction)
    async def update_page(self, interaction: discord.Interaction):
        self.counter_button.label = f"Page {self.page}/{self.total_pages}"
        per_page = 10
        start = (self.page - 1) * per_page
        end = start + per_page
        display_items = self.items[start:end]
        self.prev_button.disabled = (self.page == 1)
        self.next_button.disabled = (self.page == self.total_pages)
        summary = "\n".join([
            f"{RARITY_GLYPHS.get(item.get('rarity'), '📦')} **{item.get('name', 'Unknown')}** [{item.get('rarity', 'Unknown')} • {item.get('roll_grade', 'N/A')}] – `{item.get('id', '???')}`"
            for item in display_items
        ])
        rarity_color = RARITY_COLORS.get(self.items[0].get('rarity', 'Common'), discord.Color.gold())
        embed = discord.Embed(
            title=f"📜 {self.user.display_name}'s Inventory",
            description=f"**BALANCE:** `{self.balance:,.2f}pc`    **NET WORTH:** `{self.networth:,}pc`\n\n{summary}",
            color=rarity_color
        )
        embed.set_footer(text=f"Page {self.page}/{self.total_pages}, Sorted by {self.sortby}")
        await interaction.response.edit_message(embed=embed, view=self)

async def show_inventory(user, send_func, sortby="rarity", page=1, ephemeral=False):
    user_id = str(user.id)
    if not os.path.exists(ITEMS_FILE):
        await send_func("📬 You have no items in your inventory.", ephemeral=ephemeral); return
    with open(ITEMS_FILE, "r", encoding="utf-8") as f: items = json.load(f)
    user_items = [item for item in items if item.get("owner") == user_id]
    if not user_items:
        await send_func("📬 You have no items in your inventory.", ephemeral=ephemeral); return
    sorted_items = sorted(user_items, key=lambda x: RARITY_ORDER.get(x.get("rarity", "Unknown"), 0), reverse=True)
    per_page = 10
    total_pages = max(1, math.ceil(len(sorted_items) / per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    display_items = sorted_items[start:end]
    balance = get_balance(user_id)
    networth = sum(item.get("pitch_value", 0) for item in user_items)
    summary = "\n".join([
        f"{RARITY_GLYPHS.get(item.get('rarity'), '📦')} **{item.get('name', 'Unknown')}** [{item.get('rarity', 'Unknown')} • {item.get('roll_grade', 'N/A')}] – `{item.get('id', '???')}`"
        for item in display_items
    ])
    rarity_color = RARITY_COLORS.get(display_items[0].get('rarity', 'Common'), discord.Color.gold())
    embed = discord.Embed(
        title=f"📜 {user.display_name}'s Inventory",
        description=f"**BALANCE:** `{balance:,.2f}pc`    **NET WORTH:** `{networth:,}pc`\n\n{summary}",
        color=rarity_color
    )
    embed.set_footer(text=f"Page {page}/{total_pages}, Sorted by {sortby}")
    view = InventoryPaginator(user, sorted_items, page, total_pages, sortby, ephemeral, balance, networth)
    await send_func(embed=embed, view=view, ephemeral=ephemeral)

@bot.tree.command(name="inventory", description="View your inventory")
@app_commands.describe(sortby="Sort by rarity, float, or date", page="Page number to view")
@app_commands.guilds(GUILD_ID)
async def inventory(interaction: discord.Interaction, sortby: str = "rarity", page: int = 1):
    await show_inventory(interaction.user, interaction.response.send_message, sortby, page, ephemeral=True)

# ========================================================
#      [ SECTION 6: SHOP SYSTEM — ROTATION & FLASH DEALS ]
# ========================================================

def get_shop_items(): return loadj(SHOP_FILE, [])
def set_shop_items(items): dumpj(SHOP_FILE, items)

def rotate_shop_items():
    # Rotates the main shop: 3 random items from shop pool, resets their expires_at to 4h
    new_items = list(random_items_from_shop_pool(3, timer_hours=4))
    set_shop_items(new_items)

def add_flash_deal():
    # Adds a flash deal to the shop, only at the top, with a 1-hour timer and [Flash] tag
    pool = loadj(SHOP_POOL_FILE, [])
    if not pool: return
    item = random.choice(pool).copy()
    item["id"] = f"{item['name'].replace(' ','_')}_flash_{random.randint(1000,9999)}"
    item["category"] = "Flash"
    item["expires_at"] = (utcnow() + timedelta(hours=1)).isoformat()
    # Insert flash at top, keep at most 4 items total in shop
    items = get_shop_items()
    items = [i for i in items if i.get("category") != "Flash"]  # Remove any old flash
    items = [item] + items
    set_shop_items(items[:4])

def cleanup_expired_shop_items():
    # Remove expired shop items, and rotate if none left
    now = utcnow()
    items = get_shop_items()
    items = [i for i in items if not i.get("expires_at") or parse_dt(i["expires_at"]) > now]
    set_shop_items(items)
    if not items:
        rotate_shop_items()

# ========================================================
#   [ SECTION 7: SHOP UI & COMMANDS — BUTTONS, FLASH DEAL ]
# ========================================================

def shop_item_embed(item, show_timer=True):
    cat = item.get("category")
    em = CATEGORY_EMOJIS.get(cat, "")
    r = item.get("rarity","Common")
    glyph = RARITY_GLYPHS.get(r,"")
    title = f"{em} {item['name']} [{r}]"
    price = item.get('sale_price') if item.get('on_sale') else item.get('price')
    desc = f"{item.get('emoji','')} {item.get('description','')}\n\n**Price:** `{price:,}pc`"
    if item.get('on_sale'):
        desc += f"\n**💸 On Sale!** Original: `{item.get('price',0):,}pc`"
    if item.get('featured'):
        desc += "\n✨ *Featured Item!*"
    if item.get('bundle'):
        desc += f"\n🎁 *Includes:* {', '.join(item['bundle'])}"
    if show_timer and item.get("expires_at"):
        dt = parse_dt(item["expires_at"])
        desc += f"\n⏳ Expires in: `{dt_to_hms(dt)}`"
    color = RARITY_COLORS.get(r, discord.Color.gold())
    return discord.Embed(title=title, description=desc, color=color)

class ShopItemView(ui.View):
    def __init__(self, user, item, buy_callback, inspect_callback):
        super().__init__(timeout=120)
        self.user = user
        self.item = item
        self.buy_callback = buy_callback
        self.inspect_callback = inspect_callback

    @ui.button(label="🛒 Buy", style=discord.ButtonStyle.success)
    async def buy(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You can only buy for yourself.", ephemeral=True)
            return
        await self.buy_callback(interaction, self.item)

    @ui.button(label="🔎 Inspect", style=discord.ButtonStyle.primary)
    async def inspect(self, interaction: discord.Interaction, button: ui.Button):
        await self.inspect_callback(interaction, self.item)

# ========================================================
#        [ /SHOP COMMAND – 3-at-a-time, clocks always shown ]
# ========================================================

from datetime import timedelta

SHOP_ROTATE_HOURS = 4

def ensure_shop_item_timers():
    """Ensures every shop item has a valid expires_at field (auto-rotates every 4h)."""
    items = get_shop_items()
    now = utcnow()
    changed = False
    for i in items:
        if not i.get("expires_at") or parse_dt(i.get("expires_at")) < now:
            # Give it a new rotation window
            i["expires_at"] = (now + timedelta(hours=SHOP_ROTATE_HOURS)).isoformat()
            changed = True
    if changed:
        set_shop_items(items)

def remove_expired_shop_items():
    """Optional: Removes expired shop items (if you want them gone, not rotated)."""
    items = get_shop_items()
    now = utcnow()
    items = [i for i in items if not i.get("expires_at") or parse_dt(i["expires_at"]) > now]
    set_shop_items(items)

@bot.tree.command(name="shop", description="Browse the Rewardius Shop (rotates every 4h + flash deals).")
@app_commands.guilds(GUILD_ID)
async def shop(interaction: discord.Interaction, page: int = 1):
    user_id = str(interaction.user.id)
    ensure_shop_item_timers()  # <-- Ensures timers are always set!
    items = sorted(get_shop_items(), key=lambda i: parse_dt(i.get("expires_at")) or utcnow())
    per_page = 3
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start, end = (page - 1) * per_page, page * per_page
    display_items = items[start:end]
    balance = get_balance(user_id)

    await interaction.response.send_message(
        content=f"**Your Balance:** `{balance:,.2f}pc`\n_Page {page}/{total_pages}_\n🕓 Shop rotates every 4 hours. Use `/flashdeal` for 1-hour flash deals!",
        ephemeral=False
    )
    # Your buy/inspect callback code:
    async def buy_callback(inter, item):
        price = item.get('sale_price') if item.get('on_sale') else item.get('price')
        if get_balance(user_id) < price:
            await inter.response.send_message(f"Not enough Pitch Coins for {item['name']}.", ephemeral=True)
            return
        subtract_coins(user_id, price)
        add_inventory_item(item, user_id)
        await inter.response.send_message(f"✅ You bought **{item['name']}** for `{price:,}pc`!", ephemeral=True)
        shoplog({
            "timestamp": utcnow().isoformat(),
            "action": "buy",
            "user_id": user_id,
            "item_id": item.get("id"),
            "price": price
        })

    async def inspect_callback(inter, item):
        embed = shop_item_embed(item, show_timer=True)
        await inter.response.send_message(embed=embed, ephemeral=True)

    for item in display_items:
        embed = shop_item_embed(item, show_timer=True)
        view = ShopItemView(interaction.user, item, buy_callback, inspect_callback)
        await interaction.channel.send(embed=embed, view=view)



async def buy_callback(interaction, item):
    user_id = str(interaction.user.id)
    price = item.get('sale_price') if item.get('on_sale') else item.get('price')
    if get_balance(user_id) < price:
        await interaction.response.send_message(f"Not enough Pitch Coins for {item['name']}.", ephemeral=True)
        return
    subtract_coins(user_id, price)
    add_inventory_item(item, user_id)
    await interaction.response.send_message(f"✅ You bought **{item['name']}** for `{price:,}pc`!", ephemeral=True)
    shoplog({
        "timestamp": utcnow().isoformat(),
        "action": "buy",
        "user_id": user_id,
        "item_id": item.get("id"),
        "price": price
    })
async def inspect_callback(interaction, item):
    embed = shop_item_embed(item, show_timer=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="flashdeal", description="Add a 1-hour [Flash] deal to the top of the shop.")
@app_commands.guilds(GUILD_ID)
async def flashdeal(interaction: discord.Interaction):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    add_flash_deal()
    await interaction.response.send_message("⚡ Flash deal added! Check `/shop`.", ephemeral=True)

# ========================================================
#     [ SECTION 8: SCHEDULED TASKS — SHOP ROTATION ]
# ========================================================

@tasks.loop(minutes=1)
async def shop_rotation_task():
    """
    Runs every minute. Rotates shop every 4 hours, cleans expired flash deals.
    """
    cleanup_expired_shop_items()
    # If oldest non-flash is expired or it's been >4 hours, rotate
    items = get_shop_items()
    now = utcnow()
    if not items or all(i.get("expires_at") and parse_dt(i["expires_at"]) <= now for i in items if i.get("category")!="Flash"):
        rotate_shop_items()

# ========================================================
#    [ SECTION 9: BARGAIN BIN / SECONDHAND SHOP ]
# ========================================================

def get_secondhand_items(): return loadj(SECONDHAND_FILE, [])
def set_secondhand_items(items): dumpj(SECONDHAND_FILE, items)
def rotate_secondhand_bin():
    all_items = get_secondhand_items()
    display_items = []
    now = utcnow()
    choices = random.sample(all_items, min(3, len(all_items)))
    for i in all_items:
        if i in choices:
            i['expires_at'] = (now + timedelta(hours=1)).isoformat()
            display_items.append(i)
    set_secondhand_items(all_items)
    return display_items
def get_display_secondhand():
    now = utcnow()
    all_items = get_secondhand_items()
    disp = [i for i in all_items if parse_dt(i.get("expires_at")) and parse_dt(i["expires_at"]) > now]
    if len(disp)<3 and len(all_items)>=3:
        disp = rotate_secondhand_bin()
    return disp
def move_item_to_secondhand(item, seller_id):
    all_items = get_secondhand_items()
    item = item.copy()
    item['from_user'] = str(seller_id)
    item['expires_at'] = (utcnow() + timedelta(hours=1)).isoformat()
    all_items.append(item)
    set_secondhand_items(all_items)
def remove_secondhand_item(item_id):
    items = get_secondhand_items()
    items = [i for i in items if i["id"]!=item_id]
    set_secondhand_items(items)

@bot.tree.command(name="bargainbin", description="Browse the Bargain Bin (second hand shop).")
@app_commands.guilds(GUILD_ID)
async def bargainbin(interaction: discord.Interaction):
    items = get_display_secondhand()
    embeds = []
    for item in items:
        embed = shop_item_embed(item, show_timer=True)
        embeds.append(embed)
    await interaction.response.send_message(content="🛒 **The Bargain Bin**\nSecond hand treasures—rotates hourly!", embeds=embeds)

@bot.tree.command(name="sell", description="Sell an item from your inventory for Pitch Coins.")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(item_id="The ID of the item you want to sell")
async def sell(interaction: discord.Interaction, item_id: str):
    user_id = str(interaction.user.id)
    inv = get_inventory(user_id)
    item = next((i for i in inv if i["id"]==item_id), None)
    if not item:
        await interaction.response.send_message("You don't own that item.", ephemeral=True)
        return
    sale_price = int(item.get("price", item.get("pitch_value", 100)) * 0.6)
    add_coins(user_id, sale_price)
    if random.random() < 0.2:  # 20% chance to second hand
        move_item_to_secondhand(item, user_id)
        dest = "secondhand"
    else:
        dest = "sold"
    remove_inventory_item(user_id, item_id)
    shoplog({
        "timestamp": utcnow().isoformat(),
        "action": "sell",
        "user_id": user_id,
        "item_id": item_id,
        "price": sale_price,
        "location": dest
    })
    await interaction.response.send_message(f"Sold **{item['name']}** for `{sale_price:,}pc`!\n{'It was sent to the Bargain Bin!' if dest=='secondhand' else ''}")

# ========================================================
#        [ SECTION 10: MINTING SYSTEM ]
# ========================================================
# (Add your existing minting code/commands here or request for the full block)

# ========================================================
#        [ SECTION 11: PLAYER-TO-PLAYER TRADING ]
# ========================================================

@bot.tree.command(name="trade", description="Propose a trade with another player.")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(
    user="User to trade with",
    your_item="Your item id",
    their_item="Their item id (optional)",
    coins="Offer coins (optional)"
)
async def trade(interaction: discord.Interaction, user: discord.Member, your_item: str, their_item: str = None, coins: int = 0):
    user1, user2 = interaction.user, user
    if user1 == user2:
        await interaction.response.send_message("You can't trade with yourself!", ephemeral=True)
        return
    inv1 = get_inventory(str(user1.id))
    inv2 = get_inventory(str(user2.id))
    item1 = next((i for i in inv1 if i["id"]==your_item), None)
    item2 = next((i for i in inv2 if their_item and i["id"]==their_item), None) if their_item else None
    if not item1:
        await interaction.response.send_message("You don't own that item.", ephemeral=True)
        return

    trade_embed = discord.Embed(
        title="Proposed Trade",
        description=(
            f"**{user1.display_name}** offers: `{item1['name']}`"
            + (f" + `{coins}pc`" if coins > 0 else "")
            + (f"\nfor `{item2['name']}`" if item2 else "")
        ),
        color=discord.Color.blue()
    )

    class TradeView(ui.View):
        def __init__(self):
            super().__init__(timeout=60)
        @ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
        async def accept_trade(self, btn_interaction: discord.Interaction, button: ui.Button):
            if btn_interaction.user != user2:
                await btn_interaction.response.send_message("Only the other party can accept.", ephemeral=True)
                return
            remove_inventory_item(str(user1.id), your_item)
            add_inventory_item(item1, str(user2.id))
            if item2:
                remove_inventory_item(str(user2.id), their_item)
                add_inventory_item(item2, str(user1.id))
            if coins>0:
                if get_balance(str(user1.id))<coins:
                    await btn_interaction.response.send_message("Not enough coins to trade!", ephemeral=True)
                    return
                subtract_coins(str(user1.id), coins)
                add_coins(str(user2.id), coins)
            shoplog({
                "timestamp": utcnow().isoformat(),
                "action": "trade",
                "user1": str(user1.id),
                "user2": str(user2.id),
                "item1": your_item,
                "item2": their_item if their_item else None,
                "coins": coins
            })
            await btn_interaction.response.edit_message(content=f"Trade complete! {user1.mention} ⇄ {user2.mention}", embed=None, view=None)

    await interaction.response.send_message(
        content=f"{user2.mention}, do you accept this trade?",
        embed=trade_embed,
        view=TradeView()
    )

# ========================================================
#        [ SECTION 12: ADMIN SHOP COMMANDS ]
# ========================================================

@bot.tree.command(name="shopadd", description="(Admin) Add a new item to the shop pool.")
@app_commands.guilds(GUILD_ID)
async def shopadd(
    interaction: discord.Interaction, 
    name: str, 
    price: int, 
    emoji: str, 
    description: str, 
    stock: int = 1, 
    category: str = "Trophy"
):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    pool = loadj(SHOP_POOL_FILE, [])
    new_item = {
        "id": f"{name.replace(' ','_')}_{random.randint(1000,9999)}",
        "name": name, 
        "emoji": emoji, 
        "description": description,
        "price": price, 
        "stock": stock, 
        "rarity": "Common", 
        "category": category,
        "featured": False, 
        "on_sale": False, 
        "sale_price": None, 
        "bundle": None, 
        "expires_at": None
    }
    pool.append(new_item)
    dumpj(SHOP_POOL_FILE, pool)
    await interaction.response.send_message(f"Added **{name}** to the shop pool!")

@bot.tree.command(name="shopedit", description="(Admin) Edit a shop pool item field.")
@app_commands.guilds(GUILD_ID)
async def shopedit(interaction: discord.Interaction, item_id: str, field: str, value: str):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    pool = loadj(SHOP_POOL_FILE, [])
    for i in pool:
        if i["id"]==item_id:
            i[field] = value
    dumpj(SHOP_POOL_FILE, pool)
    await interaction.response.send_message(f"Updated `{item_id}` in pool.")

@bot.tree.command(name="shopremove", description="(Admin) Remove a shop pool item by ID.")
@app_commands.guilds(GUILD_ID)
async def shopremove(interaction: discord.Interaction, item_id: str):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    pool = loadj(SHOP_POOL_FILE, [])
    pool = [i for i in pool if i["id"]!=item_id]
    dumpj(SHOP_POOL_FILE, pool)
    await interaction.response.send_message(f"Removed `{item_id}` from pool.")

# ========================================================
#     [ SECTION 13: SCHEDULED TASKS — SHOP/BIN LOOP ]
# ========================================================

@bot.event
async def on_ready():
    print(f"Rewardius {REWARDIUS_VERSION} loaded.")
    await bot.wait_until_ready()
    try:
        synced = await bot.tree.sync(guild=GUILD_ID)
        print(f"✅ Synced {len(synced)} slash command(s) to guild {GUILD_ID.id}.")
        shop_rotation_task.start()
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ========================================================
#    [ SECTION 14: BOT TOKEN RUNNER — INSERT TOKEN HERE ]
# ========================================================

bot.run("")

# ========================================================
#    [ END OF REWARDIUS v8.2 — ALL SYSTEMS MERGED! ]
# ========================================================

