import telegram
from telegram.ext import Updater
import logging
import math
from math import radians, sin, cos, acos
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
import sqlite3
from sqlite3 import Error
import random
import datetime

bot = telegram.Bot(token ='token')

updater = Updater(token ='token')
dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

#Clase en la que almaceno la informacion de los 3 cajeros mas cercanos
class cajero:
		idCajero = 0
		dist = 500
		banco = None
		direccion = None
		latitud = 0
		longitud = 0

def start(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="Voy a ayudarte a encontrar los cajeros mas cercanos. Por favor, escriba /link o /banelco para mostrar los respectivos cajeros")

def help(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="Escriba /link o /banelco para buscar los cajeros a menos de 500 metros de usted")

def link(bot, update, chat_data):
	chat_data["red"] = "LINK"
	bot.send_message(chat_id=update.message.chat_id, text="Se mostraran los bancos Link mas cercanos")
	pedirUbicacion(bot, update)
	
def banelco(bot, update, chat_data):
	chat_data["red"] = "BANELCO"
	bot.send_message(chat_id=update.message.chat_id, text="Se mostraran los bancos Banelco mas cercanos")
	pedirUbicacion(bot, update)

def pedirUbicacion(bot, update):
	reply_markup = telegram.ReplyKeyboardMarkup([[telegram.KeyboardButton('Compartir ubicacion', request_location=True)]])
	bot.send_message(chat_id=update.message.chat_id, text="¿Podrias compartirme tu ubicacion?", reply_markup=reply_markup)

def unknown(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="No reconozco ese comando, escriba un comando correcto o /help para obtener ayuda")

def location(bot, update, chat_data):
	#Pregunta si pasaron las 8 am y si aun no hay sido cargados los cajeros. Si corresponde, se hace antes de que se efectue la extraccion
    f = open("recargas.txt", "r+")
    fecha = f.read()
    red = chat_data["red"]
    hora = datetime.datetime.now().hour
    diaSem = datetime.datetime.today().weekday()
    hoy = datetime.datetime.now().date()
    global recarga
    if hora > 8 and fecha != hoy and diaSem < 5:
    	f.seek(0)
    	f.write(str(hoy))
    	cargarCajeros(bot, update)

    f.close()

    latitud = update.message.location.latitude
    longitud = update.message.location.longitude
    mostrarCajeros(latitud, longitud, red, update)

def mostrarCajeros(latUser,longUser,red, update):
	#Funcion que toma los datos del usuario y busca los cajeros mas cercanos
	db = sqlite3.connect('cajeros.db')
	cursor = db.cursor()
	aux = None

	imagen = "https://maps.googleapis.com/maps/api/staticmap?size=500x400&markers=color:blue|label:P|"+str(latUser)+","+str(longUser)+"&"
	cajeroList = [cajero(),cajero(),cajero()]
	cursor.execute('''SELECT id, latitud, longitud, banco, direccion FROM cajeros WHERE red=? and extracciones>0''',(red,))
	datos = cursor.fetchall()
	
	#Se recorren los datos extraidos de la base de datos y calculo los 3 mas cercanos
	for row in datos:
		distancia = calcularDist(latUser,longUser,row[1],row[2])
		aux = 3
		if distancia < cajeroList[0].dist:
			aux=0
		elif distancia < cajeroList[1].dist:
			aux=1
		elif distancia < cajeroList[2].dist:
			aux=2
		if aux != 3:
			cajeroList[aux].idcajero = row[0]
			cajeroList[aux].dist = distancia
			cajeroList[aux].direccion = row[4]
			cajeroList[aux].banco = row[3]
			cajeroList[aux].latitud = str(row[1])
			cajeroList[aux].longitud = str(row[2])

	hayCajero = False
	#Por cada cajero encontrado a menos de 500 metros muestro su direccion y banco al usuario, y los concateno al link de la imagen
	for j in range(1,4):
		if cajeroList[j-1].banco != None:
			bot.send_message(chat_id=update.message.chat_id, text=str(j)+"° "+cajeroList[j-1].banco+" "+cajeroList[j-1].direccion)
			imagen = imagen+"markers=label:"+str(j)+"|"+cajeroList[j-1].latitud+","+cajeroList[j-1].longitud+"&"
			hayCajero = True

	imagen = imagen+"&key=key"

	#Pregunto si se encontro algun cajero, si lo hubo muestro la imagen
	if hayCajero:
		bot.send_photo(chat_id=update.message.chat_id, photo=imagen)
		#Array usado para calcular por probabilidades de que banco se extrajo dinero
		elementos = [0,0,0,0,0,0,1,1,2]
		pick = random.choice(elementos)
		cursor.execute('''UPDATE cajeros SET extracciones=extracciones-1 WHERE id = ? ''',(cajeroList[pick].idcajero,))
		db.commit()
	else:
		bot.send_message(chat_id=update.message.chat_id, text="Lo sentimos pero no hay cajeros a menos de 500 metros de usted")

	db.close()

def cargarCajeros(bot, update):
	#Funcion que setea las extracciones de todos los cajeros en 1000
	db = sqlite3.connect('cajeros.db')
	cursor = db.cursor()
	cursor.execute('''UPDATE cajeros SET extracciones=1000 WHERE extracciones<>1000''')
	db.commit()
	db.close()

def calcularDist(lat1, long1, lat2, long2):
	#Funcion que calcula la distancia en metros entre dos coordenadas
	slat = radians(lat1)
	slon = radians(long1)
	elat = radians(lat2)
	elon = radians(long2)
	dist = 6371010 * acos(sin(slat)*sin(elat) + cos(slat)*cos(elat)*cos(slon - elon))
	
	return dist


#Lista de comandos a escuchar
start_handler = CommandHandler('start',start)
dispatcher.add_handler(start_handler)
help_handler = CommandHandler('help',help)
dispatcher.add_handler(help_handler)
cargar_handler = CommandHandler('cargar',cargarCajeros)
dispatcher.add_handler(cargar_handler)
link_handler = CommandHandler('link',link, pass_chat_data=True)
dispatcher.add_handler(link_handler)
banelco_handler = CommandHandler('banelco',banelco, pass_chat_data=True)
dispatcher.add_handler(banelco_handler)
unknown_handler = MessageHandler(Filters.text | Filters.command, unknown)
dispatcher.add_handler(unknown_handler)
location_handler = MessageHandler(Filters.location, location, pass_chat_data=True)
dispatcher.add_handler(location_handler)

updater.start_polling()
updater.idle()