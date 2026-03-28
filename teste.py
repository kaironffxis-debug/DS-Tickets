from dotenv import load_dotenv
import os

load_dotenv()
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PIX_KEY = os.getenv('PIX_KEY')
OWNER_ID = int(os.getenv('OWNER_ID'))  # ID do dono do bot
ALLOWED_USER_IDS = set(
    int(x.strip()) for x in os.getenv('ALLOWED_USER_IDS', '1337497318513053726') .split(',') if x.strip()
)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)


def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ALLOWED_USER_IDS


async def check_authorized(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message('Apenas usuários autorizados podem executar este comando.', ephemeral=True)
        return False
    return True

options = []  # SEM PRODUTO PADRÃO
carts = {}
tickets = {}

def parse_hex_color(value: str):
    if not value:
        return None
    v = value.strip().lstrip("#")
    if len(v) not in (6, 8):
        raise ValueError("Formato de cor inválido. Use #RRGGBB ou RRGGBB.")
    return int(v, 16)


def make_store_embed():
    return discord.Embed(
        title=store_settings["embed_title"],
        description=store_settings["embed_description"],
        color=store_settings["embed_color"]
    ).set_author(name=store_settings["server_name"]).set_footer(text=store_settings["footer"])


store_settings = {
    "server_name": "Ds Apostas",
    "embed_title": "Loja da DS Apostas",
    "embed_description": "Produtos por preços acessiveis e confiaveis. Escolha um produto e finalize sua compra no Pix.",
    "embed_color": 0x2ecc71,  # verde
    "cart_title": "Carrinho",
    "cart_description": "Confira os itens selecionados e finalize a compra.",
    "footer": "#DS Apostas"
}


# =========================
# CARRINHO
# =========================

class CartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Finalizar Compra", style=discord.ButtonStyle.success)
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Só o dono pode finalizar.", ephemeral=True)

        cart = carts.get(self.user_id, [])
        if not cart:
            return await interaction.response.send_message("Carrinho vazio.", ephemeral=True)

        await interaction.response.defer()

        thread = await interaction.channel.create_thread(
            name=f"compra-{interaction.user.name}",
            type=discord.ChannelType.private_thread
        )

        # Garantir que apenas o comprador e o dono tenham acesso ao canal/thread de compra
        try:
            await thread.add_user(interaction.user)
        except Exception:
            pass

        owner_member = interaction.guild.get_member(OWNER_ID)
        if owner_member:
            try:
                await thread.add_user(owner_member)
            except Exception:
                pass

        total = sum(i["price"] * i["qty"] for i in cart)

        tickets[thread.id] = {
            "user": interaction.user,
            "cart": cart.copy(),
            "total": total
        }

        embed = discord.Embed(title="Pagamento via Pix")
        embed.add_field(name="Total", value=f"R$ {total:.2f}")
        embed.add_field(name="Chave Pix", value=PIX_KEY)
        embed.set_footer(text="Após pagar, clique em 'Já paguei'")

        await thread.send(embed=embed, view=PaymentView(thread.id))

        carts[self.user_id] = []

        await interaction.followup.send(f"Ticket criado: {thread.mention}", ephemeral=True)


# =========================
# PAGAMENTO
# =========================

class PaymentView(discord.ui.View):
    def __init__(self, thread_id):
        super().__init__(timeout=None)
        self.thread_id = thread_id

    @discord.ui.button(label="Já paguei", style=discord.ButtonStyle.success)
    async def paid(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = tickets.get(self.thread_id)

        if not ticket:
            return await interaction.response.send_message("Erro no ticket.", ephemeral=True)

        if interaction.user.id != ticket["user"].id and interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("Você não tem permissão para marcar o pagamento desta compra.", ephemeral=True)

        await interaction.response.defer()

        # Apenas informar que o pagamento foi solicitado, aguardar confirmação do dono
        await interaction.followup.send("✅ Pagamento solicitado! Aguardando confirmação do dono.", ephemeral=True)

        # Não entregar ainda, nem fechar canal


# =========================
# PRODUTOS
# =========================

class ProductSelect(discord.ui.Select):
    def __init__(self):
        opts = [
            discord.SelectOption(label=p["name"], description=f"R$ {p['price']}")
            for p in options
        ]
        super().__init__(placeholder="Escolha um produto", options=opts)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        product = next(p for p in options if p["name"] == self.values[0])

        cart = carts.setdefault(interaction.user.id, [])

        found = next((i for i in cart if i["name"] == product["name"]), None)

        if found:
            found["qty"] += 1
        else:
            cart.append({"name": product["name"], "price": product["price"], "qty": 1})

        total = sum(i["price"] * i["qty"] for i in cart)

        embed = discord.Embed(
            title=store_settings.get('cart_title', 'Carrinho'),
            description=store_settings.get('cart_description', ''),
            color=store_settings.get('embed_color', 0x2ecc71)
        )
        embed.add_field(
            name="Itens",
            value="\n".join(f"{i['qty']}x {i['name']}" for i in cart)
        )
        embed.add_field(name="Total", value=f"R$ {total:.2f}")

        await interaction.followup.send(embed=embed, view=CartView(interaction.user.id), ephemeral=True)


class StoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ProductSelect())


# =========================
# COMANDOS
# =========================

@bot.tree.command(name="loja")
async def loja(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message('Apenas o dono pode executar este comando.', ephemeral=True)

    if not options:
        return await interaction.response.send_message("Sem produtos ainda.", ephemeral=True)

    await interaction.response.defer()
    embed = make_store_embed()
    embed.add_field(name="Produtos", value="Selecione o item abaixo no menu.", inline=False)
    await interaction.followup.send(embed=embed, view=StoreView())


@bot.tree.command(name="statusloja")
async def statusloja(interaction: discord.Interaction):
    if not await check_authorized(interaction):
        return
    
    text = (
        f"Server: {store_settings['server_name']}\n"
        f"Título: {store_settings['embed_title']}\n"
        f"Descrição: {store_settings['embed_description']}\n"
        f"Cor: #{store_settings['embed_color']:06X}\n"
    )
    await interaction.response.send_message(f"Configurações da loja:\n{text}", ephemeral=True)


@bot.tree.command(name="autorizar_usuario")
async def autorizar_usuario(interaction: discord.Interaction, usuario_id: int):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("Apenas o dono pode autorizar usuários.", ephemeral=True)

    ALLOWED_USER_IDS.add(usuario_id)
    await interaction.response.send_message(f"Usuário {usuario_id} autorizado.", ephemeral=True)


@bot.tree.command(name="desautorizar_usuario")
async def desautorizar_usuario(interaction: discord.Interaction, usuario_id: int):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("Apenas o dono pode desautorizar usuários.", ephemeral=True)

    ALLOWED_USER_IDS.discard(usuario_id)
    await interaction.response.send_message(f"Usuário {usuario_id} desautorizado.", ephemeral=True)


@bot.tree.command(name="customizar_loja")
async def customizar_loja(
    interaction: discord.Interaction,
    server_name: str = None,
    titulo: str = None,
    descricao: str = None,
    cor: str = None,
    footer: str = None
):
    if not await check_authorized(interaction):
        return
    
    if server_name:
        store_settings['server_name'] = server_name
    if titulo:
        store_settings['embed_title'] = titulo
    if descricao:
        store_settings['embed_description'] = descricao
    if cor:
        try:
            store_settings['embed_color'] = parse_hex_color(cor)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
    if footer:
        store_settings['footer'] = footer

    await interaction.response.send_message('Configurações atualizadas com sucesso!', ephemeral=True)


@bot.tree.command(name="addproduto")
async def addproduto(interaction: discord.Interaction, nome: str, preco: float, delivery: str, info: str):
    if not await check_authorized(interaction):
        return
    
    options.append({
        "name": nome,
        "price": preco,
        "delivery": delivery,
        "info": info
    })

    await interaction.response.send_message(f"Produto {nome} adicionado.")


@bot.tree.command(name="removerproduto")
async def removerproduto(interaction: discord.Interaction, nome: str):
    if not await check_authorized(interaction):
        return

    product = next((p for p in options if p["name"] == nome), None)
    if not product:
        return await interaction.response.send_message(f"Produto '{nome}' não encontrado.", ephemeral=True)

    options.remove(product)
    await interaction.response.send_message(f"Produto '{nome}' removido da loja.")


@bot.tree.command(name="confirmarpagamento")
async def confirmarpagamento(interaction: discord.Interaction, thread_id: str):
    try:
        thread_id_int = int(thread_id)
    except ValueError:
        return await interaction.response.send_message("ID do thread inválido.", ephemeral=True)

    ticket = tickets.get(thread_id_int)

    if not ticket:
        return await interaction.response.send_message("Ticket não encontrado.", ephemeral=True)

    # Verificar se o usuário é o dono do bot
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("Apenas o dono do bot pode confirmar pagamentos.", ephemeral=True)

    user = ticket["user"]

    delivery = ""

    for item in ticket["cart"]:
        product = next((p for p in options if p["name"] == item["name"]), None)
        if product:
            delivery += f"{product['delivery']}\n{product['info']}\n\n"

    # ENTREGA AUTOMÁTICA
    try:
        await user.send(f"✅ Pagamento confirmado!\n\n{delivery}")
    except discord.NotFound as e:
        print("Erro ao enviar DM ao usuário (canal privado fechado, usuário bloqueou o bot, etc.):", e)

    await interaction.response.send_message("✅ Pagamento confirmado e pedido enviado por DM.", ephemeral=True)

    # Excluir o canal/thread de pedido depois de finalizado
    try:
        channel = interaction.guild.get_thread(thread_id_int)
        if channel:
            await channel.delete(reason="Pedido concluído e canal removido")
    except Exception as e:
        print("Erro ao excluir thread de pedido:", e)

    tickets.pop(thread_id_int, None)


# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot online!")

bot.run("MTQ2OTcyMzI2MzUzNzI1NDU5NA.Gqk2ZU.uWwd2ZTy90NzPqUr8BDd8liIq0DxV5-5j9DYy8")
