import discord
import globaldata as gld
import sharedmethods as sm
import itemlist
from lilothdb import run_query as rqy

cost_list = {"Redeem": "Flowers", "Gold": "Gold Coins", "Diamond": "Diamond Coins"}
processing_embed = sm.easy_embed("Blue", "Processing", "Please wait...")


class ShopSelect(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user
        opt = [discord.SelectOption(emoji=gld.flower_icon, label="Flower Shop",description="Flower points redemption shop."),
               discord.SelectOption(emoji=gld.gold_icon, label="Gold Exclusives",description="Gold coin redemption shop."),
               discord.SelectOption(emoji=gld.diamond_icon, label="Diamond Exclusives",description="Diamond coin redemption shop.")]
        shop_menu = discord.ui.Select(placeholder="Subscriber Exclusive Shops", min_values=1, max_values=1, options=opt)
        shop_menu.callback = self.shop_callback
        self.add_item(shop_menu)

    async def shop_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        description = ""
        selection = interaction.data["values"][0].split()[0]
        cost_type = "pts" if selection == "Redeem" else f"{selection} Coins"
        title_list = {"Redeem": "Flower Shop", "Gold": "Gold Exclusive", "Diamond": "Diamond Exclusive"}
        for item_set in itemlist.shop_list[selection]:
            description += f"{item_set['emoji']} {item_set['name']} - {item_set['cost']:,}x {cost_type}\n"
        embed = sm.easy_embed("Purple", f"{title_list[selection]} Shop", description)
        await interaction.message.edit(embed=embed, view=ShopView(self.user, selection))


class ShopView(discord.ui.View):
    def __init__(self, user, selection):
        super().__init__(timeout=None)
        self.user, self.selection = user, selection
        options = []
        for idx, item_set in enumerate(itemlist.shop_list[selection]):
            options.append(discord.SelectOption(
                emoji=item_set["emoji"], label=item_set["name"], description=f"Cost: {item_set['cost']:,}", value=str(idx)))
        item_menu = discord.ui.Select(placeholder="Select an item to redeem!", min_values=1, max_values=1, options=options)
        item_menu.callback = self.item_callback
        self.add_item(item_menu)

    async def item_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        item_index = int(interaction.data["values"][0])
        item_set = itemlist.shop_list[self.selection][item_index]
        description = f"Cost: {gld.coin_icons_ref[cost_list[self.selection]]} {item_set['cost']:,}x {cost_list[self.selection]}"
        purchase_view = PurchaseView(self.user, self.selection, item_set, cost_list[self.selection])
        embed = sm.easy_embed("Purple", item_set["name"], description)
        await interaction.message.edit(embed=embed, view=purchase_view)


class PurchaseView(discord.ui.View):
    def __init__(self, user, selection, item_set, cost_type, can_afford=True):
        super().__init__(timeout=None)
        self.user, self.selection, self.item_set, self.cost_type = user, selection, item_set, cost_type
        self.embed = None
        if not can_afford:
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label == "Confirm":
                    child.disabled = True
                    child.style = discord.ButtonStyle.gray

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.user.id != self.user.id:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        guild = interaction.guild
        redemption_channel = guild.get_channel(gld.bot_redemptions_channel)
        if self.embed is not None:
            await interaction.message.edit(embed=self.embed, view=None)
            return
        self.embed = await buy_item(self.user, self.selection, self.item_set, self.cost_type)
        await interaction.message.edit(embed=self.embed, view=None)
        if redemption_channel is not None:
            role_ping = f"<@&1490035174157717535>"
            description = (f"{role_ping}\nUser: {self.user.mention}\n"
                           f"Item: {self.item_set['emoji']} **{self.item_set['name']}**\n"
                           f"Cost: {gld.coin_icons_ref[self.cost_type]} {self.item_set['cost']:,}x {self.cost_type}")
            redemption_embed = sm.easy_embed("Purple", "Redemption Request", description)
            redemption_view = RedemptionView(self.user, self.item_set, self.cost_type, redemption_embed)
            await redemption_channel.send(embed=redemption_embed, view=redemption_view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_callback(self, interaction: discord.Interaction, button: discord.Button):
        if interaction.user.id != self.user.id:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        self.embed = sm.easy_embed("Red", "Cancelled", "Redemption cancelled.")
        await interaction.message.edit(embed=self.embed, view=None)


class RedemptionView(discord.ui.View):
    def __init__(self, user, item_set, cost_type, redemption_embed):
        super().__init__(timeout=None)
        self.user, self.item_set, self.cost_type = user, item_set, cost_type
        self.redemption_embed = redemption_embed

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.user.id not in [gld.admins["Liloth"], gld.admins["Archael"]]:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        await interaction.message.edit(content=f"✅ Redemption Accepted", embed=self.redemption_embed, view=None)

    @discord.ui.button(label="Refund", style=discord.ButtonStyle.red)
    async def refund_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.user.id not in [gld.admins["Liloth"], gld.admins["Archael"]]:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        refund_response = await refund_coins(self.user, self.cost_type, self.item_set["cost"])
        await interaction.message.edit(content=refund_response, embed=self.redemption_embed, view=None)


async def buy_item(user, selection, item_set, cost_type):
    currency_columns = {"Redeem": "flower_points", "Gold": "gold_coins", "Diamond": "diamond_coins"}
    check_query = f"SELECT {currency_columns[selection]} FROM UserCoins WHERE discord_id = :user_id"
    params = {"user_id": str(user.id)}
    coin_data = await rqy(check_query, return_value=True, params=params)
    if coin_data is None or coin_data.empty:
        return sm.easy_embed("Red", "Redemption Failed!", f"Insufficient {cost_type}.")
    current_balance = coin_data[currency_columns[selection]].values[0]
    if current_balance < item_set["cost"]:
        description = f"Requires: {item_set['cost']:,}x {cost_type}\nOwned: {current_balance:,}x {cost_type}."
        return sm.easy_embed("Red", "Redemption Failed!", description)
    new_balance = current_balance - item_set["cost"]
    update_query = f"UPDATE UserCoins SET {currency_columns[selection]} = :new_balance WHERE discord_id = :user_id"
    params = {"new_balance": int(new_balance), "user_id": str(user.id)}
    await rqy(update_query, params=params)
    description = f"You redeemed **{item_set['name']}** for {item_set['cost']:,}x {cost_type}."
    description += f"\nRemaining Balance: {new_balance:,}"
    return sm.easy_embed("Green", "Success!", description)


async def refund_coins(user, cost_type, amount):
    currency_columns = {"Flowers": "flower_points", "Gold Coins": "gold_coins", "Diamond Coins": "diamond_coins"}
    check_query = f"SELECT {currency_columns[cost_type]} FROM UserCoins WHERE discord_id = :user_id"
    params = {"user_id": str(user.id)}
    coin_data = await rqy(check_query, return_value=True, params=params)
    if coin_data is None or coin_data.empty:
        return "❌ Refund Failed"
    current_balance = coin_data[currency_columns[cost_type]].values[0]
    new_balance = current_balance + amount
    update_query = f"UPDATE UserCoins SET {currency_columns[cost_type]} = :new_balance WHERE discord_id = :user_id"
    params = {"new_balance": int(new_balance), "user_id": str(user.id)}
    await rqy(update_query, params=params)
    return "↩️ Refunded"


class CoinSelect(discord.ui.View):
    def __init__(self, user, quantity, increase=True):
        super().__init__(timeout=None)
        self.user, self.quantity, self.increase = user, quantity, increase
        self.embed_msg = None

    @discord.ui.button(label="Flowers", style=discord.ButtonStyle.green, row=0, emoji=gld.flower_icon)
    async def points_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.user.id not in [gld.admins["Liloth"], gld.admins["Archael"]]:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        if self.embed_msg is not None:
            await interaction.message.edit(embed=self.embed_msg, view=None)
            return
        self.embed_msg = await edit_coin_embed(self.user, "Flowers", self.quantity, self.increase)
        await interaction.message.edit(embed=self.embed_msg, view=None)

    @discord.ui.button(label="VIP", style=discord.ButtonStyle.blurple, row=0, emoji=gld.vip_icon)
    async def vip_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.user.id not in [gld.admins["Liloth"], gld.admins["Archael"]]:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        if self.embed_msg is not None:
            await interaction.message.edit(embed=self.embed_msg, view=None)
            return
        self.embed_msg = await edit_coin_embed(self.user, "VIP Coins", self.quantity, self.increase)
        await interaction.message.edit(embed=self.embed_msg, view=None)

    @discord.ui.button(label="Silver", style=discord.ButtonStyle.blurple, row=0, emoji=gld.silver_icon)
    async def silver_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.user.id not in [gld.admins["Liloth"], gld.admins["Archael"]]:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        if self.embed_msg is not None:
            await interaction.message.edit(embed=self.embed_msg, view=None)
            return
        self.embed_msg = await edit_coin_embed(self.user, "Silver Coins", self.quantity, self.increase)
        await interaction.message.edit(embed=self.embed_msg, view=None)

    @discord.ui.button(label="Gold", style=discord.ButtonStyle.blurple, row=0, emoji=gld.gold_icon)
    async def gold_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.user.id not in [gld.admins["Liloth"], gld.admins["Archael"]]:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        if self.embed_msg is not None:
            await interaction.message.edit(embed=self.embed_msg, view=None)
            return
        self.embed_msg = await edit_coin_embed(self.user, "Gold Coins", self.quantity, self.increase)
        await interaction.message.edit(embed=self.embed_msg, view=None)

    @discord.ui.button(label="Diamond", style=discord.ButtonStyle.red, row=0, emoji=gld.diamond_icon)
    async def diamond_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.user.id not in [gld.admins["Liloth"], gld.admins["Archael"]]:
            return
        await interaction.response.edit_message(embed=processing_embed, view=None)
        if self.embed_msg is not None:
            await interaction.message.edit(embed=self.embed_msg, view=None)
            return
        self.embed_msg = await edit_coin_embed(self.user, "Diamond Coins", self.quantity, self.increase)
        await interaction.message.edit(embed=self.embed_msg, view=None)


async def edit_coin_embed(user, coin_type, quantity, increase=True):
    coin_dict = {"Flowers": "flower_points", "VIP Coins": "vip_coins", "Silver Coins": "silver_coins",
                 "Gold Coins": "gold_coins", "Diamond Coins": "diamond_coins"}
    point_dict = {"Flowers": 1, "VIP Coins": 2, "Silver Coins": 5, "Gold Coins": 25, "Diamond Coins": 100}
    is_proxy_coin = coin_type in ["VIP Coins", "Silver Coins"]
    check_query = f"SELECT * FROM UserCoins WHERE discord_id = :user_id"
    params = {"user_id": str(user.id)}
    coin_data = await rqy(check_query, return_value=True, params=params)
    colour, title, change_word = "Green", "Added", "received"
    if not increase:
        colour, title, change_word = "Red", "removed", "lost"
        quantity *= -1
    if coin_data is not None and not coin_data.empty:
        # Update if exists
        current_flowers = coin_data['flower_points'].values[0]
        current_coins = coin_data[coin_dict[coin_type]].values[0]
        tracked_coins = coin_data[f"{coin_dict[coin_type]}_total"].values[0]
        leaderboard_points = coin_data["leaderboard_points"].values[0]
        total_coins = max(0, current_coins + quantity)
        total_flowers = max(0, current_flowers + quantity * point_dict[coin_type])
        tracked_coins = max(0, tracked_coins + quantity)
        points_gain = quantity * point_dict[coin_type]
        leaderboard_points = max(0, leaderboard_points + points_gain)
        if not is_proxy_coin:
            change_query = (f"UPDATE UserCoins SET {coin_dict[coin_type]} = :coins, "
                            f"{coin_dict[coin_type]}_total = :t_coins, "
                            f"leaderboard_points = :leaderboard "
                            f"WHERE discord_id = :user_id")
            params = {"coins": int(total_coins), "t_coins": int(tracked_coins),
                      "leaderboard": int(leaderboard_points), "user_id": str(user.id)}
            new_total_msg = f"New Total: {total_coins}"
        else:
            change_query = (f"UPDATE UserCoins SET flower_points = :flowers, "
                            f"{coin_dict[coin_type]}_total = :t_coins, "
                            f"leaderboard_points = :leaderboard "
                            f"WHERE discord_id = :user_id")
            params = {"flowers": int(total_flowers), "t_coins": int(tracked_coins),
                      "leaderboard": int(leaderboard_points), "user_id": str(user.id)}
            new_total_msg = f"Converted to {gld.flower_icon} {points_gain}x Flowers"
        await rqy(change_query, params=params)
        description = f"{user.display_name} has {change_word} {gld.coin_icons_ref[coin_type]} {quantity}x {coin_type}\n{new_total_msg}"
        return sm.easy_embed(colour, title, description)
    # Insert if doesnt exist
    new_quantity = total_coins = max(0, quantity)
    leaderboard_points = max(0, quantity * point_dict[coin_type])
    if not is_proxy_coin:
        insert_query = (f"INSERT INTO UserCoins "
                        f"(discord_id, {coin_dict[coin_type]}, {coin_dict[coin_type]}_total, leaderboard_points) "
                        f"VALUES (:user_id, :coins, :t_coins, :leaderboard)")
        new_total_msg = f"New Total: {total_coins}"
    else:
        new_quantity = leaderboard_points
        insert_query = (f"INSERT INTO UserCoins "
                        f"(discord_id, flower_points, {coin_dict[coin_type]}_total, leaderboard_points) "
                        f"VALUES (:user_id, :coins, :t_coins, :leaderboard)")
        new_total_msg = f"Converted to {gld.flower_icon} {new_quantity}x Flowers"
    params = {"user_id": str(user.id), "coins": new_quantity, "t_coins": int(total_coins),
              "leaderboard": int(leaderboard_points)}
    await rqy(insert_query, params=params)
    description = f"{user.display_name} has {change_word} {gld.coin_icons_ref[coin_type]} {quantity}x {coin_type}\n{new_total_msg}"
    return sm.easy_embed(colour, title, description)


class LeaderboardView(discord.ui.View):
    def __init__(self, selected_type="Score"):
        super().__init__(timeout=None)
        self.selected_type = selected_type
        leaderboard_buttons = ["Score", "VIP", "Silver", "Gold", "Diamond"]
        for label in leaderboard_buttons:
            style = discord.ButtonStyle.red if label == selected_type else discord.ButtonStyle.blurple
            button = discord.ui.Button(label=label, style=style, custom_id=label)

            async def leaderboard_callback(interaction):
                await interaction.response.edit_message(embed=processing_embed, view=None)
                selection = str(interaction.data["custom_id"])
                embed = await build_leaderboard_embed(interaction.guild, selection)
                leaderboard_view = LeaderboardView(selection)
                await interaction.message.edit(embed=embed, view=leaderboard_view)

            button.callback = leaderboard_callback
            self.add_item(button)


async def build_leaderboard_embed(guild, board_type="Score"):
    leaderboard_data = {"Score": "leaderboard_points", "VIP": "vip_coins_total", "Silver": "silver_coins_total",
                        "Gold": "gold_coins_total", "Diamond": "diamond_coins_total"}
    column_name = leaderboard_data[board_type]
    rank_query = (f"SELECT discord_id, {column_name} FROM UserCoins WHERE {column_name} > 0 "
                  f"ORDER BY {column_name} DESC LIMIT 10")
    points_data = await rqy(rank_query, return_value=True)
    description = ""
    title_name = f"{board_type} Coins"
    unit_name = "coins"
    if board_type == "Score":
        title_name = "Score"
        unit_name = "flowers"
    if points_data is None or points_data.empty:
        description = "Rankings not currently available."
        return sm.easy_embed("White", f"🌸 Garden Leaderboard [{title_name}] 🌸", description)
    rank_hearts = {1: "<:SapphireHeart:1498698449900802068>", 2: "🤍", 3: "🤎"}
    for i, row in enumerate(points_data.itertuples(index=False), start=1):
        user_id = int(row.discord_id)
        points = getattr(row, column_name)
        user = guild.get_member(user_id)
        name = user.display_name if user else f"User {user_id}"
        heart = rank_hearts.get(i, "")
        description += f"{heart} **#{i}**. {name} — {points:,} {unit_name}\n"
    return sm.easy_embed("White", f"🌸 Garden Leaderboard [{title_name}] 🌸", description)
