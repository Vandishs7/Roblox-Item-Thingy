import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from playwright.async_api import async_playwright
import asyncio
import os

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

cleanup_tracker = {}
IMAGE_FOLDER = "vv -+一二/vimgs"

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync failed: {e}")

@bot.tree.command(name="getitem", description="Fetches item details and takes a screenshot from Rolimons")
async def getitem(interaction: discord.Interaction, item_name: str):
    await interaction.response.send_message("finding imgs brah wait a sec lol...")  
    url = "https://www.rolimons.com/itemapi/itemdetails"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    await interaction.followup.send("Failed to fetch item data. Try again later.")
                    return
                
                data = await response.json()
                print(f"API Response: {data}")

                item_found = None
                for item_id, item_data in data.get('items', {}).items():
                    if item_data and isinstance(item_data, list):
                        item_name_from_api = item_data[0]
                        if item_name_from_api.lower() == item_name.lower():
                            item_found = (item_id, item_data)
                            break
                
                if not item_found:
                    await interaction.followup.send(f"Item '{item_name}' not found.")
                    return
                
                item_id, item_data = item_found
                item_url = f"https://www.rolimons.com/item/{item_id}"

                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(item_url, wait_until="networkidle")

                    try:
                        await page.wait_for_selector('text="You control your privacy"', timeout=5000)
                        await page.click('button:has-text("Accept")')
                        print("Privacy prompt accepted.")
                    except Exception as e:
                        print(f"Privacy prompt not found or already dismissed: {e}")

                    await asyncio.sleep(5)
                    screenshot_path = os.path.join(IMAGE_FOLDER, f"item_{item_id}.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    await browser.close()

                with open(screenshot_path, "rb") as f:
                    file = discord.File(f)
                    await interaction.followup.send(file=file)

                await interaction.followup.send("Found image, please type `/cleanup` in the next 10 seconds or you will be banned.") # change to the text you want it to have
                cleanup_tracker[interaction.user.id] = asyncio.create_task(ban_if_not_cleaned(interaction))

        except Exception as e:
            print(f"An error occurred: {e}")
            await interaction.followup.send("An error occurred while fetching item data.")

async def ban_if_not_cleaned(interaction):
    await asyncio.sleep(10)  # Chamge if you want the ban time to be different here.
    if interaction.user.id in cleanup_tracker:
        try:
            await interaction.guild.ban(interaction.user, reason="Failed to clean up images.")
            await interaction.followup.send(f"{interaction.user.mention} has been banned for not doing the command LOLLLLLL")
        except discord.Forbidden:
            await interaction.followup.send("Not high enough to ban ugh")
        except Exception as e:
            print(f"An error occurred while banning: {e}")
            await interaction.followup.send("An error occurred while banning the user.")
        finally:
            cleanup_tracker.pop(interaction.user.id, None)

@bot.tree.command(name="cleanup", description="Deletes all item images to save storage")
async def cleanup(interaction: discord.Interaction):
    try:
        files = os.listdir(IMAGE_FOLDER)
        image_files = [f for f in files if f.startswith("item_") and f.endswith(".png")]

        if not image_files:
            await interaction.response.send_message("No images to delete.")
            return

        for image_file in image_files:
            os.remove(os.path.join(IMAGE_FOLDER, image_file))
            print(f"Deleted {image_file}")

        await interaction.response.send_message(f"Deleted {len(image_files)} images.")

        if interaction.user.id in cleanup_tracker:
            cleanup_tracker[interaction.user.id].cancel()
            cleanup_tracker.pop(interaction.user.id, None)
            await interaction.followup.send(f"{interaction.user.mention}, you have been spared. Images cleaned up.")

    except Exception as e:
        print(f"An error occurred during cleanup: {e}")
        await interaction.response.send_message("An error occurred while deleting images.")

bot.run("tkn here")