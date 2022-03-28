from msilib.schema import Error
import requests
from bs4 import BeautifulSoup
import re

#get data for an url on immobiliare
def get_result_from_url_immobiliare(url):
    regex_prices = '\d{1,3}(\.\d{3})*'
    response = requests.get(url)
    html = BeautifulSoup(response.text, 'lxml')
    estate_html = html.body.find_all('li', class_=re.compile('nd-list__item in-realEstateResults__item'))
    estate_list = []
    try:
        for estate in estate_html:
            estate_to_append = {}
            estate_to_append['link'] = estate.contents[0].contents[1].contents[0].attrs['href']
            estate_to_append['title'] = estate.contents[0].contents[1].contents[0].attrs['title']
            estate_to_append['price'] = re.search(regex_prices, estate.contents[0].contents[1].contents[1].contents[0].text, flags=re.IGNORECASE).group(0)
            estate_list.append(estate_to_append)
        return estate_list
    except:
        return estate_list
    

#save data for each url on immobiliare
def get_list_from_url_immobiliare(url_list):   
    results_list = []
    for url in url_list:
        results_list.append(get_result_from_url_immobiliare(url))
    return results_list

def transform_label_link(string):
    result_string = string.replace(" ", "-")
    result_string = result_string.replace("'", "-")
    result_string = result_string.replace("à", "a")
    result_string = result_string.replace("ò", "o")
    result_string = result_string.replace("è", "e")
    result_string = result_string.replace("é", "e")
    result_string = result_string.replace("ù", "u")
    result_string = result_string.replace("ì", "i")
    return result_string

def get_data_from_immobiliare(user_data, number_of_results, num_page):
    user_data['index_search_list'] = number_of_results
    searches = []
    search_list = []
    global proxies

    if user_data['type'] == "Affittare":
        search_type = 'affitto-case'
    elif user_data['type'] == "Acquistare":
        search_type = 'vendita-case'
    
    if len(user_data['selected_zones']) > 0:
        for zone in user_data['selected_zones']:
            url = f"https://www.immobiliare.it/{search_type}/{transform_label_link(zone['label'])}/?criterio=dataModifica&ordine=desc&noAste=1"
            if user_data['min_price']:
                url += f"&prezzoMinimo={user_data['min_price']}"
            if user_data['max_price']:
                url += f"&prezzoMassimo={user_data['max_price']}"
            if user_data['min_surface']:
                url += f"&superficieMinima={user_data['min_surface']}"
            if user_data['max_surface']:
                url += f"&superficieMassima={user_data['max_surface']}"
            for neighbourhood in zone['neighbourhood']:
                url += f"&idQuartiere[]={neighbourhood['id']}"
            
            if len(list(filter(lambda x : x['city'] == zone['label'] and x['source'] == "Immobiliare", searches))) == 0:
                searches.append({
                    'city': zone['label'],
                    'url': url,
                    'source': 'Immobiliare'
                })

            for search in searches:
                search['results'] = get_result_from_url_immobiliare(search['url'])
            
        return searches
    else:
        raise Error

