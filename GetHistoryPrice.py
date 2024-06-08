import csv
import zipfile
import os
import requests
import asyncio
from datetime import datetime, timedelta

def readCSV(file_path, data_arr, delay = 1800, start_timestamp = -1): #delay - шаг в секундах 
    min_price = max_price = -1
    number_of_dots = 0
    with open(file_path, 'r') as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=',')
        for row in csvreader:
            timestamp = int(row['timestamp']) // 1000  # преобразуем миллисекунды в секунды
            if(start_timestamp == - 1):
                start_timestamp = timestamp
            if (timestamp - start_timestamp < 60):
                if (min_price == -1):
                    min_price = max_price = float(row['price'])
                    continue
                cur_price = float(row['price'])
                max_price = max(cur_price, max_price)
                min_price = min(cur_price, min_price)
            else:
                data_arr.append((max_price + min_price) / 2) 
                number_of_dots+=1
                start_timestamp += delay
                min_price = max_price = float(row['price'])
    return number_of_dots


def extract_files(folder_path, destination_folder):
    if not os.path.exists(folder_path):
        print(f"Папка '{folder_path}' не существует.")
        return
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path):
            if item.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(item_path, 'r') as zip_ref:
                        zip_ref.extractall(destination_folder)
                    print(f"Файлы из архива '{item}' успешно извлечены.")
                except Exception as e:
                    print(f"Ошибка при извлечении файлов из архива '{item}': {e}")
    print("Все архивы были обработаны.")
    return

def make_data(folder_path):
    price_array = []
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        readCSV(item_path, price_array, 60)
    return price_array


def download_files(start_date = '20230101', download_folder = '...', base_url = r'https://img.bitgetimg.com/online/trades/SPBL/ETHUSDT/ETHUSDT_SPBL'):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    
    current_date = datetime.strptime(start_date, "%Y%m%d")  # Преобразуем строку в формат даты

    while True:
        file_number = 1
        while True:
            
            file_date = current_date.strftime("%Y%m%d")#формируем URL файла
            file_url = f"{base_url}_{file_date}_{str(file_number).zfill(3)}.zip"
            #print(file_date, file_url)
            response = requests.get(file_url)
            if response.status_code == 200:
                filename = os.path.join(download_folder, os.path.basename(file_url))
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded {filename}")
                file_number += 1
            else:
                print(f"No more files found for {file_date}")
                break
            current_date += timedelta(days=1)
            








