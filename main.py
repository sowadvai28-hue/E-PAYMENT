import logging
import asyncio
from datetime import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

BOT_TOKEN = "8980248168:AAEFAGNA850ZaWiv7MYoqLaaoH3KBVsymM4"
ADMIN_CHAT_ID = 7702408295

PAYMENT_NUMBER = "01863-062759"
WHATSAPP_NUMBER = "01863-062759"
TELEGRAM_SUPPORT = "https://t.me/YourOfficialAdminUsername"
PROFIT_MARGIN_BDT = 4.0

def get_live_crypto_rate():
    try:
        res = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        base = res.json()['rates']['BDT']
        return base + PROFIT_MARGIN_BDT
    except:
        return 126.0

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define clean states
USD_INPUT, PAY_METHOD_STATE, SENDER_STATE, TRX_STATE, PHOTO_STATE, WALLET_STATE = range(6)
ACTIVE_ORDERS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💎 ক্রিপ্টো কিনুন (ইন্সট্যান্ট গেটওয়ে)", callback_data='start_buy')],
        [InlineKeyboardButton("📊 লাইভ এক্সচেঞ্জ রেট", callback_data='show_rates')],
        [InlineKeyboardButton("📞 এডমিন সাপোর্ট (হোয়াটসঅ্যাপ/টেলিগ্রাম)", callback_data='show_supp')]
    ]
    await update.message.reply_text(
        "👑 *অভিজাত স্বয়ংক্রিয় ক্রিপ্টো গেটওয়ে*\n\n"
        "আস-সালামু আলাইকুম! আপনি বিকাশ বা নগদের মাধ্যমে স্বয়ংক্রিয় উপায়ে ক্রিপ্টো (USDT, BTC, TRX, BNB, ETH) ক্রয় করতে পারবেন।\n\n"
        "শুরু করতে নিচের বাটনে ক্লিক করুন:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='Markdown'
    )

async def main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_buy':
        kb = [
            [InlineKeyboardButton("USDT (TRC20)", callback_data='net_USDT_TRC20'), InlineKeyboardButton("USDT (BEP20)", callback_data='net_USDT_BEP20')],
            [InlineKeyboardButton("TRON (TRX)", callback_data='net_TRX'), InlineKeyboardButton("BNB Chain", callback_data='net_BNB')],
            [InlineKeyboardButton("Bitcoin (BTC)", callback_data='net_BTC'), InlineKeyboardButton("Ethereum (ETH)", callback_data='net_ETH')]
        ]
        await query.edit_message_text("🌐 *আপনার কাঙ্ক্ষিত ক্রিপ্টো নেটওয়ার্ক বা কয়েন নির্বাচন করুন:*", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        
    elif query.data == 'show_rates':
        rate = get_live_crypto_rate()
        await query.edit_message_text(f"📊 *লাইভ বিক্রয় মূল্য:* ১ USD = ৳{rate:.2f} BDT\n\nপ্রধান মেনুতে ফিরে যেতে /start লিখুন।", parse_mode='Markdown')
        
    elif query.data == 'show_supp':
        await query.edit_message_text(f"📞 হোয়াটসঅ্যাপ এডমিন: `{WHATSAPP_NUMBER}`\n💬 টেলিগ্রাম সাপোর্ট: {TELEGRAM_SUPPORT}", parse_mode='Markdown')

async def net_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    net = query.data.replace('net_', '')
    context.user_data['net'] = net
    
    rate = get_live_crypto_rate()
    context.user_data['rate'] = rate
    
    await query.edit_message_text(
        f"💎 নির্বাচিত নেটওয়ার্ক: *{net}*\n"
        f"📈 বর্তমান মূল্য: *১ USD = ৳{rate:.2f} BDT*\n\n"
        f"আপনি কত **ডলার ($ USD)** ক্রয় করতে চান তার সংখ্যা লিখুন (যেমন: ১০, ৫০):",
        parse_mode='Markdown'
    )
    return USD_INPUT

async def get_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        usd = float(update.message.text.strip())
        if usd <= 0: raise ValueError()
    except:
        await update.message.reply_text("❌ অনুগ্রহ করে সঠিক ডলারের সংখ্যাটি লিখুন:")
        return USD_INPUT

    rate = context.user_data['rate']
    total_bdt = round(usd * rate, 2)
    context.user_data['usd'] = usd
    context.user_data['bdt'] = total_bdt
    
    kb = [
        [InlineKeyboardButton("বিকাশ পেমেন্ট", callback_data='pay_bKash'), InlineKeyboardButton("নগদ পেমেন্ট", callback_data='pay_Nagad')]
    ]
    await update.message.reply_text(
        f"🔒 *অর্ডারের বিবরণ অপরিবর্তনীয়*\n"
        f"💵 ডলারের পরিমাণ: *${usd} USD* ({context.user_data['net']})\n"
        f"💰 মোট প্রদেয় টাকা: *৳{total_bdt:,.2f} BDT*\n\n"
        f"আপনার পেমেন্টের মাধ্যমটি নির্বাচন করুন:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='Markdown'
    )
    return PAY_METHOD_STATE

async def get_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace('pay_', '')
    context.user_data['method'] = method
    
    await query.edit_message_text(
        f"📲 *{method} সেন্ড মানি নির্দেশনা*\n\n"
        f"আমাদের নিচের নম্বরে ঠিক **৳{context.user_data['bdt']:,.2f} BDT** পাঠিয়া দিন:\n"
        f"📞 নম্বর: `{PAYMENT_NUMBER}`\n\n"
        f"পেমেন্ট সফলভাবে সম্পন্ন করে আপনি যে নম্বর থেকে টাকা পাঠিয়েছেন সেই **প্রেরক নম্বর (Sender Number)** টি লিখুন:",
        parse_mode='Markdown'
    )
    return SENDER_STATE

async def get_sender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sender'] = update.message.text.strip()
    await update.message.reply_text("🧾 পেমেন্টের **ট্রানজ্যাকশন আইডি (TrxID)** টি লিখুন:")
    return TRX_STATE

async def get_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['trx'] = update.message.text.strip()
    await update.message.reply_text("📸 পেমেন্টের **স্ক্রিনশট (Screenshot)** ফটো আকারে আপলোড করুন:")
    return PHOTO_STATE

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ অনুগ্রহ করে স্পষ্ট পেমেন্টের স্ক্রিনশট ফটো আপলোড করুন:")
        return PHOTO_STATE
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text(f"📬 আপনার **{context.user_data['net']} ওয়ালেট এড্রেস** টি প্রদান করুন:")
    return WALLET_STATE

async def get_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text.strip()
    user = update.effective_user
    data = context.user_data
    
    order_id = f"ORD_{int(datetime.now().timestamp())}"
    order_info = {
        'id': order_id, 'user_id': user.id, 'username': user.username or user.first_name,
        'net': data['net'], 'usd': data['usd'], 'bdt': data['bdt'],
        'method': data['method'], 'sender': data['sender'], 'trx': data['trx'],
        'photo': data['photo'], 'wallet': wallet, 'status': 'pending'
    }
    ACTIVE_ORDERS[order_id] = order_info
    
    await update.message.reply_text(
        f"🎉 *অর্ডার সফলভাবে জমা নেওয়া হয়েছে!*\n"
        f"🆔 আই ডি: `{order_id}` | ডলার: `${data['usd']}` | মোট প্রদেয়: `৳{data['bdt']}`\n\n"
        f"⏳ *১০ মিনিটের সময় গণনা শুরু হয়েছে।* এডমিন ভেরিফিকেশন চলমান রয়েছে...",
        parse_mode='Markdown'
    )
    
    admin_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ নিশ্চিত করুন ও ডলার পাঠান", callback_data=f"adm_ok_{order_id}"),
        InlineKeyboardButton("❌ বাতিল করুন", callback_data=f"adm_no_{order_id}")
    ]])
    admin_caption = (
        f"🚨 *নতুন অর্ডার পেন্ডিং রয়েছে*\n"
        f"👤 ব্যবহারকারী: @{user.username} (`{user.id}`)\n"
        f"🌐 নেটওয়ার্ক: `{data['net']}` | ডলার: `${data['usd']}` (৳{data['bdt']})\n"
        f"💳 মাধ্যম: `{data['method']}` | প্রেরক নম্বর: `{data['sender']}`\n"
        f"🧾 ট্রানজেকশন আইডি: `{data['trx']}`\n"
        f"📬 ওয়ালেট এড্রেস:\n`{wallet}`"
    )
    try:
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=data['photo'], caption=admin_caption, reply_markup=admin_kb, parse_mode='Markdown')
    except Exception as e:
        print(e)
        
    asyncio.create_task(order_timeout(context, order_id, user.id))
    return ConversationHandler.END

async def order_timeout(context, order_id, user_id):
    await asyncio.sleep(600) # 10 minutes
    if order_id in ACTIVE_ORDERS and ACTIVE_ORDERS[order_id]['status'] == 'pending':
        ACTIVE_ORDERS[order_id]['status'] = 'expired'
        try:
            supp_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 হোয়াটসঅ্যাপ এডমিন", url=f"https://wa.me/{WHATSAPP_NUMBER.replace('-', '')}")],
                [InlineKeyboardButton("🔗 টেলিগ্রাম সাপোর্ট", url=TELEGRAM_SUPPORT)]
            ])
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⏰ *অর্ডারের মেয়াদ শেষ (১০ মিনিট)*\n\n"
                     f"এডমিন ১০ মিনিটের মধ্যে অর্ডারটি নিশ্চিত করতে পারেনি। অনুগ্রহ করে পুনরায় অর্ডার করুন অথবা সরাসরি এডমিনের সাথে যোগাযোগ করুন:",
                reply_markup=supp_kb,
                parse_mode='Markdown'
            )
        except:
            pass

async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("adm_ok_"):
        oid = data.replace("adm_ok_", "")
        if oid in ACTIVE_ORDERS:
            ACTIVE_ORDERS[oid]['status'] = 'completed'
            ord_inf = ACTIVE_ORDERS[oid]
            try:
                await context.bot.send_message(chat_id=ord_inf['user_id'], text=f"✅ আপনার অর্ডার (`{oid}`) টি অনুমোদিত হয়েছে! `${ord_inf['usd']} USD` আপনার ওয়ালেটে পাঠিয়ে দেওয়া হয়েছে। ধন্যবাদ!")
            except: pass
            await query.edit_message_caption(caption=f"✅ অর্ডার `{oid}` টি সফলভাবে অনুমোদন করা হয়েছে!")
            
    elif data.startswith("adm_no_"):
        oid = data.replace("adm_no_", "")
        if oid in ACTIVE_ORDERS:
            ACTIVE_ORDERS[oid]['status'] = 'rejected'
            ord_inf = ACTIVE_ORDERS[oid]
            try:
                wa = f"https://wa.me/{WHATSAPP_NUMBER.replace('-', '')}"
                await context.bot.send_message(chat_id=ord_inf['user_id'], text=f"❌ আপনার অর্ডার (`{oid}`) টি বাতিল করা হয়েছে। প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("হোয়াটসঅ্যাপে চ্যাট করুন", url=wa)]]))
            except: pass
            await query.edit_message_caption(caption=f"❌ অর্ডার `{oid}` টি বাতিল করা হয়েছে।")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ প্রক্রিয়াটি বাতিল করা হয়েছে।")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(net_chosen, pattern="^net_")],
        states={
            USD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_usd)],
            PAY_METHOD_STATE: [CallbackQueryHandler(get_payment_method, pattern="^pay_")],
            SENDER_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sender)],
            TRX_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_trx)],
            PHOTO_STATE: [MessageHandler(filters.PHOTO, get_photo)],
            WALLET_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_wallet)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(main_buttons, pattern="^(start_buy|show_rates|show_supp)$"))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_cb, pattern="^adm_"))
    
    print("🚀 Elite Crypto Gateway Bot Running...")
    app.run_polling()

if __name__ == '__main__':
    main()
