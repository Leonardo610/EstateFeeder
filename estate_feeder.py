# mastrobot_example.py
from telegram.bot import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, PicklePersistence, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, replymarkup, Bot
import telegram
import logging
from typing import Dict
import requests
from bs4 import BeautifulSoup
import re
import json
import time
import emoji
from immobiliare_scraper import get_list_from_url_immobiliare, get_data_from_immobiliare, get_result_from_url_immobiliare
import config


TYPE = 1
QUERY_CITY = 2
QUERY_NEIGHBOURHOOD = 3
MACROZONE = 4
MIN_PRICE = 5
MAX_PRICE = 6
MIN_SURFACE = 7
MAX_SURFACE = 8
END = 9

RESULTS = 100

proxies = {
    'https': "https://93.145.17.218:8080"
}

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def preferences_to_str(user_data: Dict[str, str]) -> str:
    preferences = []
    try:
        if user_data['type']:
            preferences.append("*Tipo di ricerca:* " + user_data['type'])
        if user_data['min_price']:
            preferences.append("*Prezzo minimo:* " + user_data['min_price'])
        if user_data['max_price']:
            preferences.append("*Prezzo massimo:* " + user_data['max_price'])
        if user_data['min_surface']:
            preferences.append("*Superficie minima:* " + user_data['min_surface'])
        if user_data['max_surface']:
            preferences.append("*Superficie massima:* " + user_data['max_surface'])
        if user_data['notifications']:
            notifications = "Attive"
        else:
            notifications = "Non attive"
        preferences.append("*Notifiche:* " + notifications + "\n\n")

        preferences.append("*Preferenze di ricerca:*")
        zones = []
        for zone in user_data['selected_zones']:
            temp = zone['label']
            if len(zone['neighbourhood']) > 0:
                temp += " - " + ", ".join([neighbourhood['label'] for neighbourhood in zone['neighbourhood']])
            zones.append(temp)
        preferences.append("\n".join(zones))
    except:
        return "Errore nel recupero delle preferenze salvate."



    return "\n".join(preferences)

def estate_to_str(estate) -> str:
    string = ""

    string += f"*{estate['title']}*"
    string += "\n\n"
    string += f"{estate['price']} €"
    string += "\n"
    string += f"{estate['link']}"

    return string

def zones_to_str(selected_zones):
    zones_str = []
    for city in selected_zones:
        zone_str = ""
        zone_str += "*CITTÀ*\n" + city['label']
        if len(city['neighbourhood']) > 0:
            zone_str += "\n\n*QUARTIERI*\n"
            neighbourhood_str = []
            for neighbourhood in city['neighbourhood']:
                neighbourhood_str.append(neighbourhood['label'])
            
            zone_str += "\n".join(neighbourhood_str)
        zones_str.append(zone_str)
    return "\n\n".join(zones_str)

def get_all_zones(macrozones):
    zones_list = []
    for macrozone in macrozones:
        for children in macrozone['children']:
            zones_list.append(children)
    return zones_list

def get_containing_string_in_list(list, word):
    result = []
    for element in list:
        if word.lower() in element['label'].lower():
            result.append(element)
    return result

def ask_min_price(update, context): 
    if context.user_data['type'] == "Affittare":
        keyboard = [[300, 500], [700, 900], ["Skip"]]
    else:
        keyboard = [[50000, 70000], [90000, 100000], ["Skip"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True,resize_keyboard=True)

    update.message.reply_text(f"Quant'è il prezzo minimo della casa dei tuoi sogni?", reply_markup=reply_markup)
    context.user_data['conversational_state'] = MIN_PRICE  

def ask_max_price(update, context):
    if context.user_data['type'] == "Affittare":
        keyboard = [[800, 1000], [1200, 1500], ["Skip"]]
    else:
        keyboard = [[150000, 200000], [250000, 300000], ["Skip"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True,resize_keyboard=True)
    update.message.reply_text(f"Ok, {context.user_data['min_price']}. E il massimo?",reply_markup=reply_markup)
    context.user_data['conversational_state'] = MAX_PRICE

def ask_min_surface(update, context): 
    keyboard = [[40, 60], [80, 100], ["Skip"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True,resize_keyboard=True)

    update.message.reply_text(f"Quant'è la superficie minima?", reply_markup=reply_markup)
    context.user_data['conversational_state'] = MIN_SURFACE

def ask_max_surface(update, context): 
    keyboard = [[70, 90], [110, 130], ["Skip"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True,resize_keyboard=True)

    update.message.reply_text(f"Ok, {context.user_data['min_surface']}. E quella massima?", reply_markup=reply_markup)
    context.user_data['conversational_state'] = MAX_SURFACE

def create_data_model(context):
    context.user_data["min_price"] = None
    context.user_data["max_price"] = None
    context.user_data["min_surface"] = None
    context.user_data["max_surface"] = None

# function to handle the /start command
def start(update, context):
    first_name = update.message.chat.first_name

    if len(context.user_data) > 0:
        update.message.reply_text(f"Ciao {first_name}, bentornato!\n\nPer visualizzare i tuoi dati salvati digita /getpreferences.\n\nPer iniziare una nuova ricerca digita /startsearch.\n\nPer modificare le tue preferenze digita /editpreferences.")
    else:
        update.message.reply_text(f"Ciao {first_name}, piacere di conoscerti!")
        context.user_data['chat_id'] = update.message.chat.id
        create_data_model(context)
        start_search(update, context)

def start_search(update, context): 
    context.user_data['conversational_state'] = TYPE

    keyboard = [['Affittare', 'Acquistare']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    update.message.reply_text(f"Prima di tutto, ho bisogno di sapere se sei interessato ad affittare o ad acquistare casa.",reply_markup=reply_markup)

def get_search_type(update, context):
    context.user_data['selected_zones'] = []
    context.user_data['notifications'] = False

    context.user_data['type'] = update.message.text
    update.message.reply_text(f"Ok, quindi vorresti {context.user_data['type'].lower()}. In quale città vorresti vivere?")
    
    context.user_data['conversational_state'] = QUERY_CITY

def get_query_result_city(update, context):
    global proxies
    
    if update.message.text.lower() == 'done':
        ask_min_price(update, context)
        return


    url_zones_immobiliare = f"https://www.immobiliare.it/search/autocomplete?macrozones=1&proximity=41.903%2C12.496&microzones=1&min_level=9&query={update.message.text}"
    response = requests.get(url_zones_immobiliare)
    zones_immobiliare = json.loads(response.text)
    keyboard = []
    context.user_data['query_results'] = [x for x in zones_immobiliare if x['type'] == 2]

    for zone in context.user_data['query_results']:
        try:
            province = [x for x in zone['parents'] if x['type'] == 1][0]
        except:
            province['id'] = zone['id']
        finally:
            keyboard.append([InlineKeyboardButton(zone['label'] + " - " + province['id'], callback_data=str(zone['type']) + "," + zone['id'])])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Seleziona uno dei risultati seguenti:", reply_markup=reply_markup)

def set_city(update, context):
    callback_data = update.callback_query.data.split(",")
    context.user_data['temp'] = {}

    for zone in context.user_data['query_results']:
        if zone['id'] == callback_data[1]:

            try:
                temp_zone = {
                    'id': zone['id'],
                    'label': zone['label'],
                    'type': zone['type'],
                    'neighbourhood': get_all_zones(zone['macrozones'])
                }
            except:
                temp_zone = {
                    'id': zone['id'],
                    'label': zone['label'],
                    'type': zone['type'],
                    'neighbourhood': []
                }

            try:
                if len(list(filter(lambda x : x['id'] == zone['id'], context.user_data['selected_zones']))) == 0:
                    context.user_data['selected_zones'].append({
                        'id': zone['id'],
                        'label': zone['label'],
                        'type': zone['type'],
                        'neighbourhood': []
                    })
            except:
                context.user_data['selected_zones'].append({
                        'id': zone['id'],
                        'label': zone['label'],
                        'type': zone['type'],
                        'neighbourhood': []
                    })
            
            context.user_data['temp'] = temp_zone
            break
    
    update.callback_query.answer()
    if len(context.user_data['temp']['neighbourhood']) > 0:
        update.callback_query.edit_message_text(text=f"Hai selezionato {context.user_data['temp']['label']}. Digita un quartiere per una ricerca più dettagliata, altrimenti digita 'done'.")
        context.user_data['conversational_state'] = QUERY_NEIGHBOURHOOD
    else:
        update.callback_query.message.reply_text(f"Hai selezionato:\n\n{zones_to_str(context.user_data['selected_zones'])}\n\nSe vuoi aggiungere un'altra città alla ricerca digita 'back'. Se hai fatto, digita 'done'.",parse_mode=telegram.ParseMode.MARKDOWN)


def get_query_result_neighbourhood(update, context):
    if update.message.text.lower() == 'back':
        update.message.reply_text(f"Quale città vorresti aggiungere alla ricerca?")
        context.user_data['conversational_state'] = QUERY_CITY
        return
    
    if update.message.text.lower() == 'done':
        ask_min_price(update, context)
        return

    context.user_data['query_results'] = get_containing_string_in_list(context.user_data['temp']['neighbourhood'], update.message.text)
    keyboard = []

    for neighbourhood in context.user_data['query_results']:
        keyboard.append([InlineKeyboardButton(neighbourhood['label'], callback_data=str(neighbourhood['type']) + "," + neighbourhood['id'])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Seleziona uno dei risultati seguenti:", reply_markup=reply_markup)

def set_neighbourhood(update, context):
    callback_data = update.callback_query.data.split(",")
    father_id = context.user_data['temp']['id']

    for zone in context.user_data['query_results']:
        if zone['id'] == callback_data[1]:
            temp_zone = {
                'id': zone['id'],
                'label': zone['label'],
                'type': zone['type']
            }
            
            for city in context.user_data['selected_zones']:
                if city['id'] == father_id:

                    try:
                        if len(list(filter(lambda x : x['id'] == zone['id'], city['neighbourhood']))) == 0:
                            city['neighbourhood'].append(temp_zone)
                    except:
                        city['neighbourhood'].append(temp_zone)
                    break
            break
    
    update.callback_query.answer()
    update.callback_query.message.reply_text(f"Hai selezionato:\n\n{zones_to_str(context.user_data['selected_zones'])}\n\n Se vuoi aggiungere un quartiere digita il suo nome.\nSe vuoi aggiungere un'altra città digita 'back'.\nSe hai fatto digita 'done'.",parse_mode=telegram.ParseMode.MARKDOWN)

def get_min_price(update, context):
    del context.user_data['temp']
    context.user_data['min_price'] = update.message.text
    ask_max_price(update, context)

def get_max_price(update, context):
    context.user_data['max_price'] = update.message.text
    ask_min_surface(update, context)

def get_min_surface(update, context):
    context.user_data['min_surface'] = update.message.text
    ask_max_surface(update, context)


def get_max_surface(update, context):
    context.user_data['max_surface'] = update.message.text
    update.message.reply_text("Ok, ho salvato le tue preferenze. Se vuoi iniziare una nuova ricerca, semplicemente digita /startsearch.")
    context.user_data['conversational_state'] = END

def get_more_data(update, context):
    keyboard = [["Carica altri risultati"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)

    for search in context.user_data['searches']:
        try:
            update.message.reply_text(f"{estate_to_str(search['results'][context.user_data['index_search_list']])}", parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)
            context.user_data['index_search_list'] += 1
        except:
            try:
                #take last number of the string, it is the current num_page
                if "pag" in search['url']:
                    num_page = int(search['url'][search['url'].rindex("=")+1:])
                    url_new_page = search['url'].replace("pag=" + str(num_page), "pag=" + str(num_page + 1))
                else:
                    url_new_page = search['url'] + "&pag=2"

                update.message.reply_text("Sto recuperando altri dati...")
                
                new_results = get_result_from_url_immobiliare(url_new_page)
                #exit if no new results
                if len(new_results) == 0:
                    raise ValueError("Nessun risultato aggiuntivo")
                search['results'] += new_results
                update.message.reply_text(f"{estate_to_str(search['results'][context.user_data['index_search_list']])}", parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)
                context.user_data['index_search_list'] += 1
            except:
                update.message.reply_text(f"Non ci sono altri risultati da mostrarti per la ricerca su {context.user_data['selected_zones'][0]['label']}.")
                context.user_data['index_search_list'] -= 1

def delete_user_data(context):
    for key in list(context.user_data.keys()):
        del context.user_data[key]

# function to handle the /help command
def help(update, context):
    update.message.reply_text('/start -> start from the beginning\n/help -> shows the list of available commands\n/getpreferences -> get the stored search preferences')

def flushdata(update, context):
    delete_user_data(context)
    update.message.reply_text("I tuoi dati sono stati cancellati. Per ricominciare dall'inizio digita /start.")

def getpreferences(update, context):
    if (len(context.user_data) == 0):
        update.message.reply_text('Non ci sono preferenze salvate.')
    else:
        update.message.reply_text(f"{preferences_to_str(context.user_data)}", parse_mode=telegram.ParseMode.MARKDOWN)

def startsearch(update, context):
    update.message.reply_text("Di seguito i risultati per la tua ricerca:")
    keyboard = [["Carica altri risultati"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False,resize_keyboard=True)

    #store data in user context
    context.user_data['searches'] = get_data_from_immobiliare(context.user_data, 1, 1) #second param is the number of results for each load more data, third is for the page number of the results

    for search in context.user_data['searches']:
        if len(search['results']) == 0:
            update.message.reply_text(f"Non ci sono risultati per la ricerca su {search['city']}.")
            return

    for search in context.user_data['searches']:
        for i in range(context.user_data['index_search_list']):
            update.message.reply_text(f"{estate_to_str(search['results'][i])}", parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)

    context.user_data['conversational_state'] = RESULTS
    context.user_data["notifications"] = False

def getnotifications(update, context):
    if context.user_data["notifications"]:
        update.message.reply_text("Le notifiche sono già attive. Se vuoi fermarle digita /stopnotifications.")
        return

    context.user_data["notifications"] = True
    update.message.reply_text("Le notifiche sono attive. Se vuoi interrompere quest'operazione digita /stopnotifications")
    
    context.job_queue.run_repeating(notification, 7200, context=context, name=str(context.user_data['chat_id']))


def notification(context):
    job = context.job
    chat_id = job.context.user_data['chat_id']
    list_url = [search['url'] for search in job.context.user_data['searches']]
    saved_results = job.context.user_data['searches']
    new_results = get_list_from_url_immobiliare([search['url'] for search in job.context.user_data['searches']])

    for i in range(len(saved_results)):
        data_is_outdated = False
        if (saved_results[i]['results'][0]['link'] != new_results[i][0]['link']):
            notification = new_results[i][0]
            job.context.bot.send_message(chat_id=chat_id, text="C'è un nuovo appartamento di tuo interesse:\n\n" + estate_to_str(notification), parse_mode=telegram.ParseMode.MARKDOWN)
            data_is_outdated = True
        else:
            job.context.bot.send_message(chat_id=chat_id, text="Nessuna nuova notifica", parse_mode=telegram.ParseMode.MARKDOWN)
    
    if data_is_outdated:
        saved_results = new_results

def editpreferences(update, context):
    delete_user_data(context)
    create_data_model(context)
    start_search(update, context)

def stopnotifications(update, context):
    if len(context.job_queue.get_jobs_by_name(str(context.user_data['chat_id']))) > 0:
        context.job_queue.get_jobs_by_name(str(context.user_data['chat_id']))[0].job.remove()
        logger.info(f"Removed job with id {context.user_data['chat_id']}")

    update.message.reply_text("Le notifiche sono state disattivate. Se vuoi riattivarle digita /getnotifications")
    context.user_data["notifications"] = False
    

# function to handle errors occured in the dispatcher 
def error(update, context):
    update.message.reply_text('Qualcosa è andato storto')

def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

# function to handle normal text 
def text(update, context):
    conversation_state = context.user_data['conversational_state']

    if conversation_state == TYPE:
        if update.message.text != "Affittare" and update.message.text != "Acquistare":
            update.message.reply_text("gg retard, clicca su uno dei bottoni sottostanti, grazie.")
        else:
            return get_search_type(update, context)
    
    if conversation_state == QUERY_CITY:
        return get_query_result_city(update, context)

    if conversation_state == QUERY_NEIGHBOURHOOD:
        return get_query_result_neighbourhood(update, context)

    #allow skipping of params of search
    if update.message.text.lower() == "skip":
        conversation_state += 1

        update.message.text = None

    if conversation_state == MIN_PRICE:
        if update.message.text and not is_number(update.message.text):
            update.message.reply_text("Inserisci un numero intero, senza virgole e punti.")
        else:
            return get_min_price(update, context)

    if conversation_state == MAX_PRICE:
        if update.message.text and not is_number(update.message.text):
            update.message.reply_text("Inserisci un numero intero, senza virgole e punti.")
        else:
            return get_max_price(update, context)

    if conversation_state == MIN_SURFACE:
        if update.message.text and not is_number(update.message.text):
            update.message.reply_text("Inserisci un numero intero, senza virgole e punti.")
        else:
            return get_min_surface(update, context)

    if conversation_state == MAX_SURFACE:
        if update.message.text and not is_number(update.message.text):
            update.message.reply_text("Inserisci un numero intero, senza virgole e punti.")
        else:
            return get_max_surface(update, context)
    
    if conversation_state == END:
        update.message.reply_text("Se vuoi iniziare una ricerca con le preferenze salvate, digita /startsearch.")

    if conversation_state == RESULTS:
        return get_more_data(update, context)


    

def main():
    TOKEN = config.token

    persistence = PicklePersistence(filename='conversationbot')

    # create the updater, that will automatically create also a dispatcher and a queue to 
    # make them dialoge
    updater = Updater(TOKEN, use_context=True, persistence=persistence, workers=32)
    dispatcher = updater.dispatcher

    # add handlers for start and help commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("getpreferences", getpreferences))
    dispatcher.add_handler(CommandHandler("editpreferences", editpreferences))
    dispatcher.add_handler(CommandHandler("flushdata", flushdata))
    dispatcher.add_handler(CommandHandler("startsearch", startsearch, run_async=True))
    dispatcher.add_handler(CommandHandler("getnotifications", getnotifications))
    dispatcher.add_handler(CommandHandler("stopnotifications", stopnotifications))
    dispatcher.add_handler(CallbackQueryHandler(set_city, pattern=r'^2.*$'))
    dispatcher.add_handler(CallbackQueryHandler(set_neighbourhood, pattern=r'^6.*$'))

     # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states = {
            TYPE: [MessageHandler(Filters.text, text)],
            QUERY_CITY: [
                MessageHandler(Filters.text, text),
                CallbackQueryHandler(set_city, pattern=r'^set_city$')
                ],
            QUERY_NEIGHBOURHOOD: [MessageHandler(Filters.text, text)],
            MACROZONE: [MessageHandler(Filters.text, text)],
            MIN_PRICE: [MessageHandler(Filters.text, text)],
            MAX_PRICE: [MessageHandler(Filters.text, text)],
            MIN_SURFACE: [MessageHandler(Filters.text, text)],
            MAX_SURFACE: [MessageHandler(Filters.text, text)],
            END: [MessageHandler(Filters.text, text)],
            RESULTS: [MessageHandler(Filters.text, text)]
        },
        fallbacks=[MessageHandler(Filters.text, text)],
        name="my_conversation",
        persistent=True,
    )

    # add an handler for normal text (not commands)
    dispatcher.add_handler(MessageHandler(Filters.text, text))

    # add an handler for errors
    dispatcher.add_error_handler(error)

    # start your shiny new bot
    updater.start_polling()

    # run the bot until Ctrl-C
    updater.idle()



if __name__ == '__main__':
    main()
    
    
    
    
    #make it a daemon
    #pid = "/tmp/test.pid"

    #daemon = Daemonize(app="estate=feeder", pid=pid, action=main)
    #daemon.start()
