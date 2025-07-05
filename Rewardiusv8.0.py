# ========================================================
#  Rewardius v8.0 "Market Mayhem" — Ultra Complete Edition
#  Last updated: 2025-07-05
#  Line count: ~2000+ (full inventory + shop + admin + animated UI)
# ========================================================

REWARDIUS_VERSION = "v8.0"

import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import json, os, math, asyncio, random
from datetime import datetime, timedelta, timezone

# --- File paths ---
ITEMS_FILE = "items.json"
COIN_FILE = "coins.json"
SHOP_FILE = "shop.json"
SECONDHAND_FILE = "secondhand.json"
SHOPLOG_FILE = "shoplog.json"
RUNETRADER_FILE = "runetrader.json"

GUILD_ID = discord.Object(id=1389242255969091584)
ADMIN_ROLE = "Admin"  # Name of admin role for admin commands

def utcnow(): return datetime.now(timezone.utc)
def ensure_file(fp, val):
    if not os.path.exists(fp):
        with open(fp, "w", encoding="utf-8") as f: json.dump(val, f, indent=2, ensure_ascii=False)
def loadj(fp, default):
    ensure_file(fp, default)
    with open(fp, "r", encoding="utf-8") as f: return json.load(f)
def dumpj(fp, val):
    with open(fp, "w", encoding="utf-8") as f: json.dump(val, f, indent=2, ensure_ascii=False)
def user_is_admin(member): return member.guild_permissions.administrator or any(r.name == ADMIN_ROLE for r in member.roles)
def shoplog(event):  # log event to file
    logs = loadj(SHOPLOG_FILE, [])
    logs.append(event)
    dumpj(SHOPLOG_FILE, logs)
def parse_dt(dt_str): return datetime.fromisoformat(dt_str) if dt_str else None
def dt_to_hms(dt):
    if not dt: return ""
    delta = dt - utcnow()
    s = max(int(delta.total_seconds()), 0)
    h, m, s = s//3600, (s%3600)//60, s%60
    return f"{h} Hours {m} Minutes {s} Seconds" if h+m+s > 0 else "Expired!"
def random_items_from_list(l, n): return random.sample(l, min(n, len(l)))

RARITY_ORDER = {"Common":0,"Uncommon":1,"Rare":2,"Epic":3,"Legendary":4,"Mythic":5,"Unknown":-1}
RARITY_GLYPHS = {"Common":"⚪️","Uncommon":"🟢","Rare":"🔵","Epic":"🟣","Legendary":"🟠","Mythic":"🔴"}
RARITY_COLORS = {
    "Common": discord.Color.light_grey(), "Uncommon": discord.Color.green(), "Rare": discord.Color.blue(),
    "Epic": discord.Color.purple(), "Legendary": discord.Color.orange(), "Mythic": discord.Color.red()
}
CATEGORY_EMOJIS = {
    "Trophy": "🏆", "Cosmetic": "🎨", "Powerup": "⚡", "Bundle": "🎁", "Collectible": "📦", "Rune": "🔮",
    "Special": "✨", "Holiday": "🎄", "Sale": "💸"
}

# --- Bot setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

# --- Currency/ledger ---
def get_balance(user_id):
    ledger = loadj(COIN_FILE, {})
    return float(ledger.get(str(user_id), 0.0))
def set_balance(user_id, amt):
    ledger = loadj(COIN_FILE, {})
    ledger[str(user_id)] = round(float(amt),2)
    dumpj(COIN_FILE, ledger)
def add_coins(user_id, amt): set_balance(user_id, get_balance(user_id)+amt)
def subtract_coins(user_id, amt): set_balance(user_id, max(0.0, get_balance(user_id)-amt))

# --- Shop core functions ---
def get_shop_items(): return loadj(SHOP_FILE, [])
def set_shop_items(items): dumpj(SHOP_FILE, items)
def get_secondhand_items(): return loadj(SECONDHAND_FILE, [])
def set_secondhand_items(items): dumpj(SECONDHAND_FILE, items)
def get_shoplog(): return loadj(SHOPLOG_FILE, [])
def get_categories(items=None):
    items = items if items is not None else get_shop_items()
    cats = set()
    for i in items:
        if "category" in i and i["category"]: cats.add(i["category"])
    return sorted(list(cats))
def get_shop_by_category(cat):
    items = get_shop_items()
    return [i for i in items if i.get("category")==cat] if cat else items
def rotate_secondhand_bin():
    all_items = get_secondhand_items()
    display_items = []
    now = utcnow()
    # Select 3 items at random, update their 'expires_at'
    choices = random_items_from_list(all_items, 3)
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
    # Auto refresh if any slots expired
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

# --- Inventory ---
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

# --- Inventory Paginator & Display ---
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

# --- Minting System (float + roll grades + animation delete, mintrandom, mintfor, etc) ---
def analyze_float_and_roll(float_value):
    roll_grade = "Simple"
    float_title = "Normal"
    digits = list(float_value.replace('.', ''))
    counts = {d: digits.count(d) for d in set(digits)}
    most_common = max(counts.values(), default=0)
    is_mirror = float_value == float_value[::-1]
    if float_value == "13.37": float_title = "Perfect"
    elif float_value.startswith("0"): float_title = "Scratched"
    elif float_value.startswith("1"): float_title = "Scuffed"
    elif float_value.startswith("2"): float_title = "Worn"
    elif float_value.startswith("3"): float_title = "Tarnished"
    elif float_value.startswith("4"): float_title = "Polished"
    elif float_value.startswith("5"): float_title = "Gleaming"
    elif float_value.startswith("6"): float_title = "Refined"
    elif float_value.startswith("7"): float_title = "Pristine"
    elif float_value.startswith("8"): float_title = "Radiant"
    elif float_value.startswith("09"): float_title = "Luminous"
    elif float_value.startswith("10"): float_title = "Celestial"
    if float_value == "13.37": roll_grade = "Perfect"
    elif is_mirror: roll_grade = "Mirror"
    elif most_common == 4: roll_grade = "Quad+++"
    elif most_common == 3: roll_grade = "Triplet++"
    elif most_common == 2: roll_grade = "Twin+"
    return float_title, roll_grade
def generate_float():
    return f"{random.randint(0, 13):02}.{random.randint(0, 99):02}"
async def generate_mint(name, season="GEN_1", rarity=None):
    float_value = generate_float()
    float_title, roll_grade = analyze_float_and_roll(float_value)
    digits = list(float_value.replace('.', ''))
    counts = {d: digits.count(d) for d in set(digits)}
    most_common = max(counts.values(), default=0)
    multiplier = 5.0 if float_title == "Perfect" else (most_common + int(most_common) / 10 if most_common >= 2 else 1.0)
    value = int(500 * multiplier)
    return {
        "id": f"GEN_{random.randint(1000, 9999)}_{float_value}",
        "name": name,
        "rarity": rarity or random.choice(list(RARITY_ORDER.keys())[:-1]),
        "season": season,
        "roll_grade": roll_grade,
        "float": float_value,
        "float_title": float_title,
        "pitch_value": value,
        "owner": None
    }
class ConfirmMintView(ui.View):
    def __init__(self, user, item):
        super().__init__(timeout=60)
        self.user = user
        self.item = item
        self.item_saved = False
    @ui.button(label="Confirm Mint", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your mint to confirm.", ephemeral=True)
            return
        if not self.item_saved:
            self.save_item(interaction.user)
            self.item_saved = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="✅ Mint confirmed and saved!", view=self)
    @ui.button(label="Add to Inventory", style=discord.ButtonStyle.primary)
    async def add_to_inventory(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your mint to add.", ephemeral=True)
            return
        self.save_item(interaction.user)
        await interaction.response.send_message("✅ Item added to inventory!", ephemeral=True)
    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You cannot delete this mint.", ephemeral=True)
            return
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.animate_embed_exponential_wipe(interaction)
    async def animate_embed_exponential_wipe(self, interaction):
        message = await interaction.original_response()
        embed = message.embeds[0] if message.embeds else None
        if not embed:
            await message.edit(content="🗑️ Mint Deleted!", embed=None)
            return
        delay_per_tick = 0.09
        while True:
            desc = embed.description or ""
            lines = desc.split('\n')
            deletable_positions = []
            line_positions = []
            for i, line in enumerate(lines):
                line_indices = []
                for j, c in enumerate(line):
                    if not c.isspace():
                        deletable_positions.append((i, j))
                        line_indices.append(j)
                line_positions.append(line_indices)
            if not deletable_positions: break
            delete_indices = set()
            offset = 0
            for i, indices in enumerate(line_positions):
                n = len(indices)
                if n == 0: continue
                elif n < 3:
                    for k, idx in enumerate(indices):
                        if random.random() < 0.9:
                            delete_indices.add(offset + k)
                else:
                    line_delete_count = max(1, n // 2)
                    delete_in_line = set(random.sample(indices, line_delete_count))
                    for k, idx in enumerate(indices):
                        if idx in delete_in_line: delete_indices.add(offset + k)
                offset += n
            new_lines = []
            global_pos = 0
            for i, line in enumerate(lines):
                chars = list(line)
                for j, c in enumerate(chars):
                    if not c.isspace():
                        if global_pos in delete_indices:
                            chars[j] = ''
                        global_pos += 1
                new_lines.append(''.join(chars))
            embed.description = '\n'.join(new_lines)
            await message.edit(embed=embed)
            await asyncio.sleep(delay_per_tick)
        embed.description = "🗑️ Mint Deleted!"
        await message.edit(embed=embed)
    def save_item(self, user):
        self.item["owner"] = str(user.id)
        self.item["mint_date"] = utcnow().isoformat()
        if os.path.exists(ITEMS_FILE):
            with open(ITEMS_FILE, "r", encoding="utf-8") as f: items = json.load(f)
        else:
            items = []
        item_copy = self.item.copy()
        item_copy["id"] = f"GEN_{random.randint(1000, 9999)}_{item_copy['float']}"
        items.append(item_copy)
        with open(ITEMS_FILE, "w", encoding="utf-8") as f: json.dump(items, f, indent=2)

@bot.tree.command(name="mint", description="Rolls a mint with stats and optionally adds it to your inventory.")
@app_commands.describe(name="Name of the item to mint", season="Label for the item season", rarity="Item rarity")
@app_commands.choices(rarity=[app_commands.Choice(name=r, value=r) for r in RARITY_ORDER if r != "Unknown"])
@app_commands.guilds(GUILD_ID)
async def mint(interaction: discord.Interaction, name: str, season: str = "GEN_1", rarity: app_commands.Choice[str] = None):
    await interaction.response.defer(thinking=False)
    item = await generate_mint(name, season=season, rarity=rarity.value if rarity else None)
    glyph = RARITY_GLYPHS.get(item['rarity'], '')
    embed = discord.Embed(
        title=f"🎯 Float and stat roll in progress for {name}...",
        description=f"🎯 Float: {item['float_title']} `{item['float']}`\n📊 Roll Grade: `{item['roll_grade']}`\n💎 Rarity: {glyph} {item['rarity']}\n📆 Season: {item['season']}\n💰 Value: {item['pitch_value']} pc",
        color=discord.Color.red()
    )
    view = ConfirmMintView(interaction.user, item)
    await interaction.followup.send(embed=embed, view=view, ephemeral=False)

# --- Animated additive text reveal for /mintrandom ---
async def animate_mintrandom_additive(interaction, embed, view):
    flicker_emojis = ['💥', '🕳️', '🦴', '✂️', '😵‍💫', '🧹', '⚡', '💨', '📦', '_']
    desc = embed.description or ""
    lines = [list(line) for line in desc.split('\n')]
    mask = [[False if not c.isspace() else True for c in line] for line in lines]
    total_text_chars = sum(not c.isspace() for line in lines for c in line)
    revealed = set()
    delay_per_tick = 0.09
    async def render():
        display_lines = []
        for i, line in enumerate(lines):
            display_line = []
            for j, c in enumerate(line):
                if mask[i][j]:
                    display_line.append(c)
                elif (i, j) in revealed:
                    display_line.append(c)
                else:
                    display_line.append(random.choice(flicker_emojis))
            display_lines.append(''.join(display_line))
        embed.description = '\n'.join(display_lines)
        await message.edit(embed=embed)
    for i, line in enumerate(mask):
        for j in range(len(line)):
            if not line[j]: lines[i][j] = lines[i][j]
    embed.description = '\n'.join([''.join([c if m else ' ' for c, m in zip(line, maskline)]) for line, maskline in zip(lines, mask)])
    message = await interaction.followup.send(embed=embed, ephemeral=False)
    await asyncio.sleep(delay_per_tick)
    chars_to_reveal = {(i, j) for i, line in enumerate(mask) for j, m in enumerate(line) if not m}
    while True:
        remaining = list(chars_to_reveal - revealed)
        if not remaining: break
        percent_visible = (len(revealed) / total_text_chars) if total_text_chars else 1.0
        if percent_visible < 0.75: burst = max(1, len(remaining) // 2)
        else: burst = len(remaining)
        to_add = set(random.sample(remaining, burst))
        revealed |= to_add
        await render()
        await asyncio.sleep(delay_per_tick)
    embed.description = desc
    await message.edit(embed=embed, view=view)

@bot.tree.command(name="mintrandom", description="Generates a randomized item mint with a random name.")
@app_commands.guilds(GUILD_ID)
async def mintrandom(interaction: discord.Interaction):
    await interaction.response.defer(thinking=False)
    random_names = ["Worn Token", "Ancient Coin", "Mystery Relic", "Twilight Charm", "Ghost Medal", "Echo Fragment"]
    name = random.choice(random_names)
    item = await generate_mint(name)
    glyph = RARITY_GLYPHS.get(item['rarity'], '')
    embed = discord.Embed(
        title=f"🎲 Random Mint: {name}",
        description=f"🎯 Float: {item['float_title']} `{item['float']}`\n📊 Roll Grade: `{item['roll_grade']}`\n💎 Rarity: {glyph} {item['rarity']}\n📆 Season: {item['season']}\n💰 Value: {item['pitch_value']} pc",
        color=discord.Color.blue()
    )
    view = ConfirmMintView(interaction.user, item)
    await animate_mintrandom_additive(interaction, embed, view)

@bot.tree.command(name="mintfor", description="Rolls until a float title or roll grade is matched.")
@app_commands.describe(target="What are you hunting for? (e.g., Pristine, Twin+)", name="Name for the item")
@app_commands.guilds(GUILD_ID)
async def mintfor(interaction: discord.Interaction, target: str, name: str = "CustomMint"):
    await interaction.response.defer(thinking=False)
    target = target.lower()
    count = 0
    msg = await interaction.followup.send("🔁 Starting roll attempt...", ephemeral=False)
    while True:
        item = await generate_mint(name)
        count += 1
        if count % 10 == 0:
            await msg.edit(content=f"🔁 Attempt {count}: `{item['float']}` {item['float_title']} / `{item['roll_grade']}`")
        if target in item["float_title"].lower() or target in item["roll_grade"].lower(): break
    glyph = RARITY_GLYPHS.get(item['rarity'], '')
    embed = discord.Embed(
        title=f"✅ Match found on attempt {count}!",
        description=f"🎯 Float: {item['float_title']} `{item['float']}`\n📊 Roll Grade: `{item['roll_grade']}`\n💎 Rarity: {glyph} {item['rarity']}\n📆 Season: {item['season']}\n💰 Value: {item['pitch_value']} pc",
        color=discord.Color.green()
    )
    view = ConfirmMintView(interaction.user, item)
    await msg.edit(content=None, embed=embed, view=view)

# === SHOP UI / INTERACTION ===

def shop_item_embed(item, show_timer=False, source="shop"):
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
    if source=="secondhand" and item.get("from_user"):
        desc += f"\n🛒 From: <@{item['from_user']}>"
    color = RARITY_COLORS.get(r, discord.Color.gold())
    return discord.Embed(title=title, description=desc, color=color)

class ShopView(ui.View):
    def __init__(self, user, items, page, total_pages, category, balance, buy_cb=None, inspect_cb=None):
        super().__init__(timeout=180)
        self.user = user
        self.items = items
        self.page = page
        self.total_pages = total_pages
        self.category = category
        self.balance = balance
        self.buy_cb = buy_cb
        self.inspect_cb = inspect_cb

        self.add_item(ui.Button(label="⬅️ Previous", style=discord.ButtonStyle.secondary, disabled=(self.page==1)))
        self.add_item(ui.Button(label=f"Page {self.page}/{self.total_pages}", style=discord.ButtonStyle.gray, disabled=True))
        self.add_item(ui.Button(label="Next ➡️", style=discord.ButtonStyle.secondary, disabled=(self.page==self.total_pages)))

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    @ui.button(label="⬅️ Previous", row=1)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        if self.page > 1:
            await self.buy_cb(interaction, self.page-1, self.category)
    @ui.button(label="Next ➡️", row=1)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if self.page < self.total_pages:
            await self.buy_cb(interaction, self.page+1, self.category)

# --- Shop Command ---
@bot.tree.command(name="shop", description="Browse the Rewardius Shop.")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(category="Filter by category")
async def shop(interaction: discord.Interaction, category: str = None, page: int = 1):
    user_id = str(interaction.user.id)
    all_items = get_shop_items()
    if category:
        items = [i for i in all_items if i.get("category")==category]
    else:
        items = all_items
    per_page = 3
    total_pages = max(1, math.ceil(len(items)/per_page))
    page = max(1, min(page, total_pages))
    start, end = (page-1)*per_page, page*per_page
    display_items = items[start:end]
    balance = get_balance(user_id)

    shop_embeds = []
    for item in display_items:
        embed = shop_item_embed(item, show_timer=True)
        shop_embeds.append(embed)

    await interaction.response.send_message(
        content=f"**Your Balance:** `{balance:,.2f}pc`",
        embeds=shop_embeds,
        view=ShopView(
            interaction.user, items, page, total_pages, category, balance,
            buy_cb=lambda i, p, c: shop(i, c, p),  # Reuse shop for pagination
            inspect_cb=None
        )
    )

# --- Bargain Bin Command (Second Hand Shop) ---
@bot.tree.command(name="bargainbin", description="Browse the Bargain Bin (second hand shop).")
@app_commands.guilds(GUILD_ID)
async def bargainbin(interaction: discord.Interaction):
    items = get_display_secondhand()
    embeds = []
    for item in items:
        embed = shop_item_embed(item, show_timer=True, source="secondhand")
        embeds.append(embed)
    await interaction.response.send_message(content="🛒 **The Bargain Bin**\nSecond hand treasures—rotates hourly!", embeds=embeds)

# --- Sell Command ---
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
    sale_price = int(item.get("pitch_value", 100) * 0.6)
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

# --- Player-to-player trading (simplified) ---
@bot.tree.command(name="trade", description="Propose a trade with another player.")
@app_commands.guilds(GUILD_ID)
@app_commands.describe(user="User to trade with", your_item="Your item id", their_item="Their item id (optional)", coins="Offer coins (optional)")
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
    view = ui.View(timeout=60)
    @ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
    async def accept_trade(_, btn):
        remove_inventory_item(str(user1.id), your_item)
        add_inventory_item(item1, str(user2.id))
        if item2:
            remove_inventory_item(str(user2.id), their_item)
            add_inventory_item(item2, str(user1.id))
        if coins>0:
            if get_balance(str(user1.id))<coins:
                await interaction.channel.send("Not enough coins to trade!", ephemeral=True)
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
        await interaction.followup.send(f"Trade complete! {user1.mention} ⇄ {user2.mention}")
    view.add_item(accept_trade)
    await interaction.response.send_message(
        f"{user2.mention}, do you accept this trade?\n"
        f"**{user1.display_name}** offers: `{item1['name']}`{' + ' + str(coins) + 'pc' if coins>0 else ''}"
        f"{f' for {item2['name']}' if item2 else ''}",
        view=view
    )

# --- Admin commands (add/edit/remove shop) ---
@bot.tree.command(name="shopadd", description="(Admin) Add a new item to the shop.")
@app_commands.guilds(GUILD_ID)
async def shopadd(interaction: discord.Interaction, name: str, price: int, emoji: str, description: str, stock: int = 1, category: str = "Trophy"):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    items = get_shop_items()
    new_item = {
        "id": f"{name.replace(' ','_')}_{random.randint(1000,9999)}",
        "name": name, "emoji": emoji, "description": description,
        "price": price, "stock": stock, "rarity": "Common", "category": category,
        "featured": False, "on_sale": False, "sale_price": None, "bundle": None, "expires_at": None
    }
    items.append(new_item)
    set_shop_items(items)
    shoplog({"timestamp": utcnow().isoformat(), "action": "admin_add", "user_id": str(interaction.user.id), "item_id": new_item["id"]})
    await interaction.response.send_message(f"Added **{name}** to the shop!")

@bot.tree.command(name="shopedit", description="(Admin) Edit a shop item field.")
@app_commands.guilds(GUILD_ID)
async def shopedit(interaction: discord.Interaction, item_id: str, field: str, value: str):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    items = get_shop_items()
    for i in items:
        if i["id"]==item_id:
            i[field] = value
    set_shop_items(items)
    shoplog({"timestamp": utcnow().isoformat(), "action": "admin_edit", "user_id": str(interaction.user.id), "item_id": item_id, "field": field, "value": value})
    await interaction.response.send_message(f"Updated `{item_id}`.")

@bot.tree.command(name="shopremove", description="(Admin) Remove a shop item by ID.")
@app_commands.guilds(GUILD_ID)
async def shopremove(interaction: discord.Interaction, item_id: str):
    if not user_is_admin(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return
    items = get_shop_items()
    items = [i for i in items if i["id"]!=item_id]
    set_shop_items(items)
    shoplog({"timestamp": utcnow().isoformat(), "action": "admin_remove", "user_id": str(interaction.user.id), "item_id": item_id})
    await interaction.response.send_message(f"Removed `{item_id}` from shop.")

# --- Bargain Bin auto-rotate ---
@tasks.loop(minutes=5)
async def secondhand_bin_autorefresh():
    items = get_secondhand_items()
    now = utcnow()
    changed = False
    for item in items:
        dt = parse_dt(item.get("expires_at"))
        if dt and dt < now:
            items.remove(item)
            changed = True
    if changed:
        set_secondhand_items(items)
        rotate_secondhand_bin()

@bot.event
async def on_ready():
    print(f"Rewardius {REWARDIUS_VERSION} loaded.")
    await bot.wait_until_ready()
    try:
        synced = await bot.tree.sync(guild=GUILD_ID)
        print(f"✅ Synced {len(synced)} slash command(s) to guild {GUILD_ID.id}.")
        secondhand_bin_autorefresh.start()
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

bot.run("#BOT_KEY")
