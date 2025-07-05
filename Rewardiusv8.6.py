# ========================================================
#  REWARDIUS v8.3 "Market Mayhem Ultra" — Complete System
#  FULL BOT: Inventory, Shop, Timers, Mint, Flash, Trade
#  Last updated: 2025-07-05
#  PASTE YOUR TOKEN AT THE BOTTOM!
# ========================================================

import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import json, os, math, asyncio, random
from datetime import datetime, timedelta, timezone

# === [MINTLOG CHANNEL CONFIG: Put your channel ID here!] ===
MINTLOG_CHANNEL_ID = 1391140923907510322  # <-- REPLACE with your mintlog channel's real ID!

# ========================================================
#   [ SECTION 1: GLOBAL CONSTANTS & CONFIG ]
# ========================================================

REWARDIUS_VERSION = "v8.3"
GUILD_ID = discord.Object(id=1389242255969091584)
ADMIN_ROLE = "Admin"

# ---- FILES (edit these if you move data files) ----
ITEMS_FILE = "items.json"
COIN_FILE = "coins.json"
SHOP_FILE = "shop.json"
SHOP_POOL_FILE = "shop_pool.json"
SECONDHAND_FILE = "secondhand.json"
SHOPLOG_FILE = "shoplog.json"

# ---- Rarity, Color, Categories ----
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

# === [Mintlog: Write mint event to JSON file for tracking/history] ===
def log_mint(user, item, method):
    log_entry = {
        "timestamp": utcnow().isoformat(),
        "user_id": str(user.id),
        "username": user.display_name,
        "item_id": item.get("id"),
        "item_name": item.get("name"),
        "rarity": item.get("rarity"),
        "float": item.get("float"),
        "float_title": item.get("float_title"),
        "roll_grade": item.get("roll_grade"),
        "method": method
    }
    logs = loadj("mintlog.json", [])
    logs.append(log_entry)
    dumpj("mintlog.json", logs)

# === [Announce every mint to a specific Discord channel] ===
# ========================================
# [MINT ANNOUNCE TO CHANNEL - IMPROVED]
# ========================================

MINT_CHANNEL_ID = 1391140923907510322  # Change to your #minting-factory channel ID

async def announce_mint_to_channel(bot, user, item, method):
    MINTLOG_CHANNEL_ID = 1240317974708641872  # <-- update this as needed
    channel = bot.get_channel(MINTLOG_CHANNEL_ID)
    if not channel:
        print(f"[Mintlog] Couldn't find channel {MINTLOG_CHANNEL_ID}")
        return

    mint_method_label = method.lower()
    glyph = RARITY_GLYPHS.get(item['rarity'],'')
    embed = discord.Embed(
        title=f"✨ New Mint: The {item['name']}",
        description=(
            f"**Rarity:** {item['rarity']} {glyph}\n"
            f"**Float:** `{item['float']}` [{item.get('float_title','')}]\n"
            f"**Roll Grade:** `{item.get('roll_grade','')}`\n"
            f"**Pitch Value:** `{item.get('pitch_value', 0)}pc`\n"
            f"**ID:** `{item.get('id','')}`"
        ),
        color=RARITY_COLORS.get(item['rarity'], discord.Color.gold())
    )
    embed.set_footer(text=f"Minted by {user.display_name} • {mint_method_label}")
    await channel.send(embed=embed)


    glyph = RARITY_GLYPHS.get(item['rarity'], '')
    # Mint method label for display (always titlecase for pretty embeds)
    mint_method_label = {
        "mint": "Mint",
        "mintrandom": "MintRandom",
        "mintfor": "MintFor"
    }.get(method.lower(), method.capitalize())

async def announce_mint_to_channel(client, user, item, method):
    print(f"Announcing mint to channel {MINTLOG_CHANNEL_ID} ...")  # DEBUG
    channel = client.get_channel(MINTLOG_CHANNEL_ID)
    print(f"Channel object: {channel}")  # DEBUG
    if channel is None:
        print("Channel not found! Is the ID correct?")
        return

    glyph = RARITY_GLYPHS.get(item['rarity'], '')

    embed = discord.Embed(
        title=f"✨ New Mint: The {item['name']}",
        description=(
            f"**Rarity:** {item['rarity']} {glyph}\n"
            f"**Float:** `{item['float']}` [{item.get('float_title','')}]\n"
            f"**Roll Grade:** `{item.get('roll_grade','')}`\n"
            f"**Pitch Value:** `{item.get('pitch_value', 0)}pc`\n"
            f"**ID:** `{item.get('id','')}`\n\n"
            f"*{method.lower()}*"
        ),
        color=RARITY_COLORS.get(item['rarity'], discord.Color.gold())
    )

    embed.set_footer(text=f"Minted by {user.display_name} • {method.lower()}")
    await channel.send(embed=embed)
    print("Mint announced to channel!")  # DEBUG




# ========================================================
#   [ SECTION 2: HELPERS, FILE I/O & DATETIME ]
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

def random_items_from_shop_pool(n, tag=None, timer_hours=None):
    pool = loadj(SHOP_POOL_FILE, [])
    items = random.sample(pool, min(n, len(pool)))
    now = utcnow()
    for item in items:
        item = item.copy()
        item["id"] = f"{item['name'].replace(' ','_')}_{random.randint(1000,9999)}"
        if tag: item["category"] = tag
        if timer_hours:
            item["expires_at"] = (now + timedelta(hours=timer_hours)).isoformat()
        yield item

# ========================================================
#   [ SECTION 3: DISCORD BOT SETUP ]
# ========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ========================================================
#   [ SECTION 4: CURRENCY / LEDGER ]
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
#   [ SECTION 5: INVENTORY SYSTEM ]
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

# --- Inventory UI: Paginated Inventory View ---
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
#   [ SECTION 6: SHOP ROTATION & FLASH DEAL LOGIC ]
# ========================================================

def get_shop_items(): return loadj(SHOP_FILE, [])
def set_shop_items(items): dumpj(SHOP_FILE, items)

def rotate_shop_items():
    # 3 new main shop items, resets timers for 4 hours
    new_items = list(random_items_from_shop_pool(3, timer_hours=4))
    set_shop_items(new_items)

def add_flash_deal():
    # Adds a flash deal to the shop for 1 hour, [Flash] tag
    pool = loadj(SHOP_POOL_FILE, [])
    if not pool: return
    item = random.choice(pool).copy()
    item["id"] = f"{item['name'].replace(' ','_')}_flash_{random.randint(1000,9999)}"
    item["category"] = "Flash"
    item["expires_at"] = (utcnow() + timedelta(hours=1)).isoformat()
    items = get_shop_items()
    items = [i for i in items if i.get("category") != "Flash"]  # Remove old flash
    items = [item] + items
    set_shop_items(items[:4])

def cleanup_expired_shop_items():
    now = utcnow()
    items = get_shop_items()
    items = [i for i in items if not i.get("expires_at") or parse_dt(i["expires_at"]) > now]
    set_shop_items(items)
    if not items:
        rotate_shop_items()

# ========================================================
#   [ SECTION 7: SHOP UI, BUTTONS, PAGINATOR ]
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

class ShopPaginatorView(ui.View):
    def __init__(self, user, total_pages, current_page, callback):
        super().__init__(timeout=90)
        self.user = user
        self.total_pages = total_pages
        self.current_page = current_page
        self.callback = callback
        self.prev_btn = ui.Button(label="⬅️ Previous", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 1))
        self.prev_btn.callback = self.go_prev
        self.add_item(self.prev_btn)
        self.page_btn = ui.Button(label=f"Page {self.current_page}/{self.total_pages}", style=discord.ButtonStyle.gray, disabled=True)
        self.add_item(self.page_btn)
        self.next_btn = ui.Button(label="Next ➡️", style=discord.ButtonStyle.secondary, disabled=(self.current_page == self.total_pages))
        self.next_btn.callback = self.go_next
        self.add_item(self.next_btn)
    async def go_prev(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Not your shop!", ephemeral=True)
            return
        await self.callback(interaction, self.current_page - 1)
    async def go_next(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Not your shop!", ephemeral=True)
            return
        await self.callback(interaction, self.current_page + 1)

# ========================================================
#   [ SECTION 8: SHOP/FLASH/BIN COMMANDS ]
# ========================================================

@bot.tree.command(name="shop", description="Browse the Rewardius Shop (rotates every 4h + flash deals).")
@app_commands.guilds(GUILD_ID)
async def shop(interaction: discord.Interaction, page: int = 1):
    user_id = str(interaction.user.id)
    cleanup_expired_shop_items()
    items = sorted(get_shop_items(), key=lambda i: parse_dt(i.get("expires_at")) or utcnow())
    per_page = 3
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start, end = (page - 1) * per_page, page * per_page
    display_items = items[start:end]
    balance = get_balance(user_id)
    async def page_callback(inter, target_page):
        await shop(inter, page=target_page)
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
    if interaction.response.is_done():
        await interaction.followup.send(
            content=f"**Your Balance:** `{balance:,.2f}pc`\n_Page {page}/{total_pages}_\n🕓 Shop rotates every 4 hours. Use `/flashdeal` for 1-hour flash deals!",
            ephemeral=False
        )
    else:
        await interaction.response.send_message(
            content=f"**Your Balance:** `{balance:,.2f}pc`\n_Page {page}/{total_pages}_\n🕓 Shop rotates every 4 hours. Use `/flashdeal` for 1-hour flash deals!",
            ephemeral=False
        )
    for item in display_items:
        embed = shop_item_embed(item, show_timer=True)
        view = ShopItemView(interaction.user, item, buy_callback, inspect_callback)
        await interaction.channel.send(embed=embed, view=view)
    paginator_view = ShopPaginatorView(interaction.user, total_pages, page, page_callback)
    await interaction.channel.send(view=paginator_view)

@bot.tree.command(name="flashdeal", description="Add a 1-hour [Flash] deal to the top of the shop.")
@app_commands.guilds(GUILD_ID)
async def flashdeal(interaction: discord.Interaction):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    add_flash_deal()
    await interaction.response.send_message("⚡ Flash deal added! Check `/shop`.", ephemeral=True)

# ========================================================
#   [ SECTION 9: PLAYER-TO-PLAYER TRADING ]
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
#   [ SECTION 10: ADMIN SHOP COMMANDS ]
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

# -- Add shopedit, shopremove, etc here as needed! --

# ========================================================
#   [ SECTION 11: MINTING SYSTEM (DROP-IN) ]
#   [ SECTION 11: MINTING SYSTEM — FULL BLOCK ]
# ========================================================

def analyze_float_and_roll(float_value):
    """Analyze float value for float_title and roll_grade."""
    s = float_value.replace(".", "")
    # Float Title logic (edit to add new tiers)
    f = float(float_value)
    if float_value == "13.37":
        float_title = "Perfect"
    elif f < 1:
        float_title = "Scratched"
    elif f < 2:
        float_title = "Scuffed"
    elif f < 3:
        float_title = "Worn"
    elif f < 4:
        float_title = "Tarnished"
    elif f < 5:
        float_title = "Polished"
    elif f < 6:
        float_title = "Gleaming"
    elif f < 7:
        float_title = "Refined"
    elif f < 8:
        float_title = "Pristine"
    elif f < 9:
        float_title = "Radiant"
    elif f < 10:
        float_title = "Luminous"
    elif f < 12:
        float_title = "Celestial"
    else:
        float_title = "Normal"

    # Roll Grade logic (edit for more combos if you want)
    roll_grade = ""
    is_mirror = (s == s[::-1] and s[0]!=s[1])  # Mirror Match (not all same digit)
    digit_counts = [s.count(d) for d in set(s)]
    if float_value == "13.37":
        roll_grade = "Perfect"
    elif is_mirror:
        roll_grade = "Mirror"
    elif 4 in digit_counts:
        roll_grade = "Quad+++"
    elif 3 in digit_counts:
        roll_grade = "Triplet++"
    elif 2 in digit_counts:
        roll_grade = "Twin+"
    else:
        roll_grade = "Simple"
    return float_title, roll_grade

def generate_float():
    """Produce a random float string 00.00–13.37."""
    # 13.37 is ultra-rare (1 in 1337 chance)
    if random.randint(1, 1337) == 1:
        return "13.37"
    main = random.randint(0, 13)
    sub = random.randint(0, 99)
    return f"{main:02}.{sub:02}"

def next_item_id(name):
    return f"{name.replace(' ','_')}_{random.randint(1000,9999)}_{random.randint(1000,9999)}"

def mint_item(name, user_id, rarity=None, season="GEN_1"):
    """Generates a unique item dict, ready to be added to inventory."""
    float_value = generate_float()
    float_title, roll_grade = analyze_float_and_roll(float_value)
    # Rarity assignment (weighted, edit as desired)
    rarity = rarity or random.choices(
        ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"],
        [45, 28, 13, 8, 5, 1]
    )[0]
    base_val = {
        "Common": 100, "Uncommon": 220, "Rare": 500, "Epic": 1100,
        "Legendary": 2200, "Mythic": 4500
    }[rarity]
    value = int(base_val * (1.4 if "Mirror" in roll_grade else 1.0) * (1.7 if float_title=="Perfect" else 1.0))
    return {
        "id": next_item_id(name),
        "name": name,
        "rarity": rarity,
        "season": season,
        "roll_grade": roll_grade,
        "float": float_value,
        "float_title": float_title,
        "pitch_value": value,
        "owner": str(user_id),
        "mint_date": utcnow().isoformat()
    }

# ========== [ MINTING COMMANDS ] ==========

@bot.tree.command(name="mint", description="(ADMIN) Mint a new reward item for yourself or another user.")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(name="Item name", user="Recipient")
async def mint(interaction: discord.Interaction, name: str, user: discord.Member = None):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    user = user or interaction.user
    item = mint_item(name, user.id)
    add_inventory_item(item, user.id)
    embed = discord.Embed(
        title=f"🪄 New Mint: {item['name']}",
        description=f"**Rarity:** {item['rarity']} {RARITY_GLYPHS.get(item['rarity'],'')}\n"
                    f"**Float:** `{item['float']}` (**{item['float_title']}**)\n"
                    f"**Roll Grade:** `{item['roll_grade']}`\n"
                    f"**Pitch Value:** `{item['pitch_value']:,}pc`",
        color=RARITY_COLORS.get(item['rarity'], discord.Color.gold())
    )
    embed.set_footer(text=f"Minted for {user.display_name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    log_mint(interaction.user, item, "mint")
    await announce_mint_to_channel(interaction.client, interaction.user, item, "mint")
    

@bot.tree.command(name="mintrandom", description="Mint a random reward item (for fun/testing, not admin-only).")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(name="Item name")
async def mintrandom(interaction: discord.Interaction, name: str):
    item = mint_item(name, interaction.user.id)
    add_inventory_item(item, interaction.user.id)
    embed = discord.Embed(
        title=f"🎲 You minted: {item['name']}",
        description=f"**Rarity:** {item['rarity']} {RARITY_GLYPHS.get(item['rarity'],'')}\n"
                    f"**Float:** `{item['float']}` (**{item['float_title']}**)\n"
                    f"**Roll Grade:** `{item['roll_grade']}`\n"
                    f"**Pitch Value:** `{item['pitch_value']:,}pc`",
        color=RARITY_COLORS.get(item['rarity'], discord.Color.gold())
    )

    log_mint(interaction.user, item, "mintrandom")
    await announce_mint_to_channel(interaction.client, interaction.user, item, "mintrandom")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="mintfor", description="(ADMIN) Mint repeatedly until target rarity/float/roll hit.")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(name="Item name", float_title="Target float title", roll_grade="Target roll grade", max_attempts="Attempts cap (default 1000)", user="Recipient")
async def mintfor(interaction: discord.Interaction, name: str, float_title: str = None, roll_grade: str = None, max_attempts: int = 1000, user: discord.Member = None):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    user = user or interaction.user
    result = None
    for attempt in range(max_attempts):
        item = mint_item(name, user.id)
        if (not float_title or item["float_title"].lower() == float_title.lower()) and \
           (not roll_grade or item["roll_grade"].lower() == roll_grade.lower()):
            result = item
            break
    if result:
        add_inventory_item(result, user.id)
        embed = discord.Embed(
            title=f"🌟 Special Mint: {result['name']}",
            description=f"**Rarity:** {result['rarity']} {RARITY_GLYPHS.get(result['rarity'],'')}\n"
                        f"**Float:** `{result['float']}` (**{result['float_title']}**)\n"
                        f"**Roll Grade:** `{result['roll_grade']}`\n"
                        f"**Pitch Value:** `{result['pitch_value']:,}pc`\n"
                        f"**Attempts:** {attempt+1}",
            color=RARITY_COLORS.get(result['rarity'], discord.Color.gold())
        )
        embed.set_footer(text=f"Minted for {user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("❌ No mint with those criteria after attempts.", ephemeral=True)

# ========== END OF MINTING SYSTEM BLOCK ==========

# ========================================================
#   [ SECTION 12: BOT EVENT LOOP AND TASKS ]
# ========================================================

@tasks.loop(hours=4)
async def shop_rotation_task():
    rotate_shop_items()
    cleanup_expired_shop_items()

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
#   [ SECTION 13: BOT TOKEN (PASTE TOKEN BELOW) ]
# ========================================================

bot.run("")

# ========================================================
#       [ END OF REWARDIUS v8.3 — ALL SYSTEMS MERGED ]
# ========================================================
