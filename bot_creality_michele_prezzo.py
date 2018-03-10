#10 mar 18
from telegram.ext import Updater, Dispatcher
from telegram.ext import CommandHandler
from telegram.ext import *
import urllib.request
import os
from bs4 import BeautifulSoup
import postgresql
import time
import psycopg2
from urllib.parse import urlparse
import emoji

STRING_DB = os.environ['DATABASE_URL']

url = "https://www.gearbest.com/3d-printers-3d-printer-kits/pp_779174.html"
urlPriceConversion = "https://order.gearbest.com/data-cache/currency_huilv.js?v=20180124153657"
urlTimeRemaining = "https://www.gearbest.com/3d-printers-3d-printer-kits/pp_779174.html?wid=21&act=get_promo_left"
TOKEN = os.environ['TOKEN']

updater = Updater(token=TOKEN)


def insertNewPrice(priceUSD,priceEUR, USDtoEURconversion):
	global STRING_DB
	timestamp = int( time.time() )
	result = urlparse(STRING_DB)
	username = result.username
	password = result.password
	database = result.path[1:]
	hostname = result.hostname
	connection = psycopg2.connect(
								database = database,
								user = username,
								password = password,
								host = hostname
								)
	cur = connection.cursor()
	cur.execute('INSERT INTO pricetable (priceUSD, priceEUR, USDtoEURconversion, timestamp ) VALUES (%s, %s, %s, %s)', (priceUSD, priceEUR, USDtoEURconversion, timestamp) )
	connection.commit()
	connection.close()
	
	
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
	bot.send_message(chat_id=update.message.chat_id, text="You'll get fucking notifications on every price change of your favourite 3D printer.\nIf you are eager you can use /prezzo to view the price.\nA query to check price changes is done every 5 minutes")

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
	result = urlparse(STRING_DB)
	username = result.username
	password = result.password
	database = result.path[1:]
	hostname = result.hostname
	connection = psycopg2.connect(
								database = database,
								user = username,
								password = password,
								host = hostname
								)
	cur = connection.cursor()
	cur.execute("""SELECT * FROM pricetable ORDER BY ID DESC LIMIT 1""")
	rows = cur.fetchall()
	previousPriceUSD = float( rows[0][1] )
	previousPriceEUR = float( rows[0][2] )
	#print(previousPriceUSD )
	#print(previousPriceEUR )
	#if changed price send msg
	if ( abs(currentPriceUSD - previousPriceUSD) > 0.02 ): # grazie Giunta
		if currentPriceUSD > previousPriceUSD: #bad
			emojiCode = emoji.emojize(':thumbs_down: (increased)')
		else:
			emojiCode = emoji.emojize(':thumbs_up: (decreased)')
		print(emojiCode)
		text = "<b>Price change detected.</b>\n{}\n\nPrice is now {}$ = <b>{}€</b>\nPrice was {}$ = <b>{}€</b>\nMoney conversion: 1 USD = {} EUR\n\nCurrent Time Remaining is {}\nGo check {}".format( emojiCode, currentPriceUSD, currentPriceEUR, previousPriceUSD, previousPriceEUR, round(USDtoEURconversion, 3), humanTime, url ) 
		try:
			bot.send_message(disable_web_page_preview = True, chat_id=31923577,  text=text, parse_mode="Html")
			bot.send_message(disable_web_page_preview = True, chat_id=281082989,  text=text, parse_mode="Html")
		except Exception as e:
			print("error send msg ")
		insertNewPrice(currentPriceUSD, currentPriceEUR, USDtoEURconversion)
	connection.commit()
	connection.close()

def init_DB():
	timestamp = time.time()
	result = urlparse(STRING_DB)
	username = result.username
	password = result.password
	database = result.path[1:]
	hostname = result.hostname
	connection = psycopg2.connect(
								database = database,
								user = username,
								password = password,
								host = hostname
								)
	cur = connection.cursor()
	cur.execute("""CREATE TABLE IF NOT EXISTS pricetable (id serial PRIMARY KEY, priceUSD varchar(10), priceEUR varchar(10), USDtoEURconversion varchar(10), timestamp varchar(20) ) """)
	# ensure an initial price record is present
	priceUSD, currency = getPriceandCurrency(url)
	USDtoEURconversion = getPriceConversion(urlPriceConversion)
	priceEUR = round( priceUSD * USDtoEURconversion, 2)  
	print("initDB inizio")
	print(priceUSD, currency, USDtoEURconversion, priceEUR)
	print("fine")
	cur.execute('INSERT INTO pricetable (priceUSD, priceEUR, USDtoEURconversion, timestamp ) VALUES (%s, %s, %s, %s)', (priceUSD, priceEUR, USDtoEURconversion, timestamp))
	connection.commit()
	connection.close()
	
init_DB()
		
start_handler = CommandHandler('start', start)
prezzo_handler = CommandHandler('prezzo', askPrice)
dispatcher = updater.dispatcher
dispatcher.add_handler(start_handler)
dispatcher.add_handler(prezzo_handler)

j = updater.job_queue
job_minute = j.run_repeating(callback_minute, interval=300, first=0)

updater.start_polling()
