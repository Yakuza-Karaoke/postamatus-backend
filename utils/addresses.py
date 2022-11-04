from curses.ascii import isdigit
import json
from dataset_worker import get_data
from geopy import geocoders

abbreviations = {
    #'д.': 'дом',
    'г.': '',
    'п': '',
    'п.': '',
    'мкр.': 'микрорайон ',
    'ул.': 'улица ',
    'пр-кт.': 'проспект ',
    'проспект.': 'проспект ',
    'б-р.': 'бульвар ',
    'пер.': 'переулок ',
    'проезд.': 'проезд ',
    'аллея.': 'аллея ',
    'линия.': 'линия ',
    'наб.': 'набережная ',
    'ш.': 'шоссе ',
    'Б.': 'большая ',
    'М.': 'малая ',
    'Ср.': 'Средняя ',
    'Нижн.': 'Нижняя ',
    'стр.': 'к',
    'корп.': 'к',
    'к.': 'к'
}

def change_address(address: str):
    new_address = ''
    flag = 0
    for word in address.split():
        if(word == 'д.'):
            flag = 1
            continue
        if(word in abbreviations):
                new_address += abbreviations[word]
        else:
            if(not flag):
                new_address += word
                new_address += ' '
            elif(word.isdigit()):
                new_address += word
            else:
                new_address += word[:len(word) - 1]                
    return new_address

def get_correct_addresses():
    correct_addresses = []
    for row in get_data():
        correct_addresses.append({'address' : change_address(row.address), 'population' : row.population})
    return correct_addresses


def test_address(addresses: list):
    geolocator = geocoders.Nominatim(user_agent="address")
    correct_res = []
    fault_res = []
    cnt = 0
    for address in addresses:
        try:
            full_address = geolocator.geocode("Москва " + str(address['address']))
        except Exception:
            cnt += 1
            print(str(address['address']))
            fault_res.append(address)
            continue
        if full_address:
            correct_res.append({
                'address' : address['address'],
                'population' : address['population'],
                'longitude': full_address.longitude,
                'latitude': full_address.latitude
            })
            continue
        fault_res.append(address)
    return correct_res, fault_res

def save_addresses():
    correct_res, fault_res = test_address(list(get_correct_addresses()))

    with open('correct_addresses.json', 'w') as outfile:
        json.dump(correct_res, outfile, ensure_ascii=False)

    with open('fault_addresses.json', 'w') as outfile:
        json.dump(fault_res, outfile, ensure_ascii=False)


def get_mfc_address():
    geolocator = geocoders.Nominatim(user_agent="mfc")
    with open('mfc.txt', 'r') as f:
        mfc = f.readlines()
    mfc_res = []
    for row in mfc:
        row = row.replace(',', '')
        begin_address = row.find('.') + 1
        end_address = row.find('md.mos.ru')
        mfc_address = change_address(row[begin_address:end_address])
        try:
            address = geolocator.geocode(mfc_address)
        except Exception:
            mfc_res.append({
                'address' : mfc_address,
                'longitude': None,
                'latitude': None
            })
            continue
        if address:
            mfc_res.append({
                'address' : mfc_address,
                'longitude': address.longitude,
                'latitude': address.latitude
            })
            continue
        mfc_res.append({
                'address' : mfc_address,
                'longitude': None,
                'latitude': None
            })
    
    with open('mfc_address.json', 'w') as outfile:
        json.dump(mfc_res, outfile, ensure_ascii=False)


if __name__ == "__main__":
    save_addresses()
