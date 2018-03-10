#10 mar 18
from telegram.ext import Updater, Dispatcher
from telegram.ext import CommandHandler
from telegram.ext import *
import urllib.request
import os
from bs4 import BeautifulSoup
import postgresql
import time

STRING_DB = os.environ['DATABASE_URL'].replace("postgres","pq")
url = "https://www.gearbest.com/3d-printers-3d-printer-kits/pp_779174.html"
urlPriceConversion = "https://order.gearbest.com/data-cache/currency_huilv.js?v=20180124153657"
urlTimeRemaining = "https://www.gearbest.com/3d-printers-3d-printer-kits/pp_779174.html?wid=21&act=get_promo_left"
TOKEN = os.environ['TOKEN']
updater = Updater(token=TOKEN)


def init_DB():
	global STRING_DB
	global url
	global urlPriceConversion
	timestamp = time.time()
	db = postgresql.open(STRING_DB)
	ps = db.prepare("CREATE TABLE IF NOT EXISTS priceTable (id serial PRIMARY KEY, priceUSD varchar(10), priceEUR varchar(10), USDtoEURconversion varchar(10), timestamp varchar(20) );")
	ps() 
	# ensure an initial price record is present
	priceUSD, currency = getPriceandCurrency(url)
	USDtoEURconversion = getPriceConversion(urlPriceConversion)
	priceEUR = round( price * USDtoEURconversion, 2)  
	ps = db.prepare("INSERT INTO priceTable (priceUSD, priceEUR, USDtoEURconversion, timestamp) VALUES ('{}','{}','{}','{}')".format(priceUSD, priceEUR, USDtoEURconversion , timestamp) )
	ps()       
	db.close()
init_DB()
	
def insertNewPrice(priceUSD,priceEUR, USDtoEURconversion):
	global STRING_DB
	timestamp = time.time()
	db = postgresql.open(STRING_DB)
	ps = db.prepare("INSERT INTO priceTable (priceUSD, priceEUR, pricetoEURconversion, timestamp) VALUES ('{}','{}','{}','{}')".format(priceUSD, priceEUR, USDtoEURconversion,  timestamp) )
	ps()
	db.close()

def getPriceandCurrency( url ):
	req = urllib.request.Request(
		url, 
		data=None, 
		headers={
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
		}
	)

	f = urllib.request.urlopen(req)
	
	html = f.read()
	#<meta property="og:price:amount" content="465.99" />
	price = float( BeautifulSoup( html , "html.parser").findAll("meta",{"property":"og:price:amount"})[0].attrs["content"] )
	#<meta property="og:price:currency" content="USD" />
	currency = BeautifulSoup( html , "html.parser").findAll("meta",{"property":"og:price:currency"})[0].attrs["content"]
	return price,currency

def getPriceConversion( url ):
	req = urllib.request.Request(
		url, 
		data=None, 
		headers={
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
		}
	)

	f = urllib.request.urlopen(req)
	html = str(f.read())
	conversion =  html.split('EUR":')[1].split(",")[0] 
	return float(conversion)
	
def getRemainingTimeOffer( url ):
	req = urllib.request.Request(
		url, 
		data=None, 
		headers={
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
		}
	)
	f = urllib.request.urlopen(req)
	html = f.read()
	return int(html)
	
def getHumanRemainingTimeOffer( timeRemaining ):
	hours = int(timeRemaining / 3600)
	minutes = int((timeRemaining - hours * 3600) / 60 )
	seconds = timeRemaining -hours * 3600 - minutes * 60
	return "{}h{}m{}s".format(hours,minutes,seconds)
	
def start(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="You'll get notifications on every price change of your favourite 3D printer.")

def askPrice(bot, update):
	global url
	bot.sendChatAction(chat_id=31923577,  action = "typing")
	price, currency = getPriceandCurrency(url)
	USDtoEURconversion = getPriceConversion(urlPriceConversion)
	priceEUR = round( price * USDtoEURconversion, 2)
	timeRemaining = getRemainingTimeOffer(urlTimeRemaining)
	humanTime = getHumanRemainingTimeOffer(timeRemaining)
	text = "User asked for price information.\nPrice is now {}$ = <b>{}€</b>\nMoney conversion: 1 USD = {} EUR\nTime Remaining is {}\n\nGo check {}".format( price, priceEUR, round(USDtoEURconversion, 3), humanTime, url ) 
	bot.send_message(disable_web_page_preview = True, chat_id=31923577,  text=text, parse_mode="Html")

def callback_minute(bot, job):
	global url
	currentPriceUSD, currency = getPriceandCurrency(url)
	USDtoEURconversion = getPriceConversion(urlPriceConversion)
	currentPriceEUR = round( currentPriceUSD * USDtoEURconversion, 2)
	timeRemaining = getRemainingTimeOffer(urlTimeRemaining)
	humanTime = getHumanRemainingTimeOffer(timeRemaining)
	#check if price changed
	ps = db.prepare("SELECT * FROM priceTable ORDER BY ID DESC LIMIT 1;")
	previousPriceUSD = float( [ item[1] for item in ps() ][0] )
	previousPriceEUR = float( [ item[2] for item in ps() ][0] )
	print(previousPriceUSD )
	print(previousPriceEUR )
	#if changed price send msg
	if ( abs(currentPriceUSD - previousPriceUSD) < 0.02 ): # grazie Giunta
		text = "<b>Price change detected.</b>\n\nPrice is now {}$ = <b>{}€</b>\nPrice was {}$ = <b></b>\nMoney conversion: 1 USD = {} EUR\nCurrent Time Remaining is {}\nGo check {}".format( currentPriceUSD, currentPriceEUR, previousPriceUSD, previousPriceEUR, round(USDtoEURconversion, 3), humanTime, url ) 
		bot.send_message(disable_web_page_preview = True, chat_id=31923577,  text=text, parse_mode="Html")
		insertNewPrice(currentPriceUSD, currentPriceEUR, USDtoEURconversion)

		
start_handler = CommandHandler('start', start)
start_handler = CommandHandler('prezzo', askPrice)
dispatcher = updater.dispatcher
dispatcher.add_handler(start_handler)

j = updater.job_queue
job_minute = j.run_repeating(callback_minute, interval=10, first=0)

updater.start_polling()
