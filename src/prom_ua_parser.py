# -*- coding: utf-8 -*-

# Importing libraries
from __future__ import unicode_literals
import sys
import os
import time
import json
from pprint import pprint
import re

import requests
from requests.exceptions import ConnectTimeout, ProxyError, ReadTimeout, TooManyRedirects
from bs4 import BeautifulSoup
from lxml.html import fromstring
from itertools import chain
from random import choice, randint, shuffle, randrange
from pandas import DataFrame, ExcelWriter
from openpyxl import Workbook
from proxy_collector import get_proxy_list

print()
print('Prom.ua parser started at', time.ctime())

# Main links
PAGE_CONSUMER, PAGE_B2B = 'https://prom.ua/ua/consumer-goods', 'https://prom.ua/ua/b2b'
TEST_PAGE = 'https://prom.ua/ua/Kupuj-ukrayinske'

# Excel preparations
EXCEL_FILE = 'prom_ua.xlsx'

if not os.path.isfile(EXCEL_FILE):
    wb = Workbook()
    wb.save(EXCEL_FILE)
    print('File created!')
else:
    print('File already exists!')

# User agent changer
with open('user_agents.txt') as file:
    useragents = file.read().split('\n')

# Sessions' specification
session = requests.Session()

# Headers' specification 
headers = {
            'User-Agent' : choice(useragents),
            'accept' : '*/*',
            'accept-encoding' : 'gzip, deflate, br',
            'accept-language' : 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
            }

print('Headers:')
pprint(headers)



# Proxy parameters:
proxies = get_proxy_list()
while not proxies:
    print('Proxy servers are unable. Please, wait for 10-20 minutes to automatic reload')
    time.sleep(randint(300,600))
    proxies = get_proxy_list()
else:
    print()
    print('Proxies loaded:')
    print()
    pprint(proxies)

proxy_pool = chain(proxies)
proxy = next(proxy_pool)
workProxyCounter = 0

# Soup maker function with proxy check and rotate
def get_htmlsoup(url, headers, session):
    global proxy, proxy_pool, proxies, workProxyCounter
    
    while True:
        print('')
        
        try:
            if workProxyCounter > 5:
                print(f"Call counter for proxy {proxy} exceeded 5 calls. Proxy will be changed.")
                raise Exception() 
            
            print('Trying fetching with proxy:', proxy)
            try:
                response = session.get(
                    url, 
                    headers=headers, 
                    proxies={"http": proxy, "https": proxy}, 
                    timeout=8, 
                    allow_redirects=False)
                print('Status code:',response.status_code)
                if response.status_code == 200:
                    print('Chosen proxy is {0}'.format(proxy)) 
                    html = response.text
                    workProxyCounter += 1
                    print('Soup boiled!')
                    return BeautifulSoup(html, 'html.parser')
                else:
                    raise Exception()
                    #raise Exception('Status code: {}'.format(response.status_code))
            except Exception as e:
                print('Connection error just happened by', type(e))
                raise
        
        except KeyboardInterrupt:
            raise
            
        except: #(ConnectTimeout, ProxyError, ReadTimeout):
            try:
                print("Getting new proxy.....")
                proxy = next(proxy_pool)
                time.sleep(randint(3,12))
                workProxyCounter = 0
            except StopIteration:
                print("Round of proxies finished. Refreshing proxies list")
                proxies = []
                time.sleep(randint(90,120))
                while len(proxies) == 0:
                    proxies = get_proxy_list()
                    shuffle(proxies)
                    if len(proxies) > 0:
                        print('Proxies reloaded:')
                        pprint(proxies)
                        proxy_pool = chain(proxies)
                        proxy = next(proxy_pool)
                        break
                    else:
                        print('Proxy servers now are unable to work with. Please, wait for 10-20 minutes to automatic reload.')
                        time.sleep(randint(300,600))


# Finding max page number of current category
def get_max_item_page_number(link):
    pages = link.find_all('a', attrs={'class' : 'x-pager__item'})
    page_numbers = []
    for page in pages:
        page_numbers.append(page['data-page'])
    #page_number = [page['data-page'] for page in pages]
    if page_numbers:
        return max([int(page) for page in page_numbers])

# Finding all urls from current page
def get_items(link):

    # Function returns all ulrs from page
    links = []
    def extrude_link(links):                                      
        urls = [] 
        for tag in links:
            url_json = tag.find('script', attrs={'type' : 'application/ld+json'}).get_text() 
            urldict = json.loads(url_json)
            url = urldict['url']
            urls.append(url)
        return urls
    """
    Items at the page devided by divs. There are X items at the not end page.
    Items devided by 2 separate classes, so we need to find both.
    """
    links1 = link.find_all('div', attrs={'class' : 'x-gallery-tile js-gallery-tile js-productad x-gallery-tile_type_click'})
    if len(links1) > 0:
        urls = extrude_link(links1)
        links.extend(urls)

    links2 = link.find_all('div', attrs={'class' : 'x-gallery-tile js-gallery-tile x-gallery-tile_type_click'})
    if len(links2) > 0:
        urls = extrude_link(links2)
        links.extend(urls)
    
    return links


# Iterating pages through current category and collects data
def scrap_controller(url, headers, session):
    CATEGORY_ITEMS = []
    max_number = 0
    while not max_number:
        print("Max number finder while loop...")
        link = get_htmlsoup(url, headers, session)
        max_number = get_max_item_page_number(link)
    
    if max_number:
        print('Max number pages at the current ceatogory is',max_number)

    for page in range(1, max_number+1):
        url_page = f'{url}?page={page}'
        page_link = get_htmlsoup(url_page, headers, session)   
        сurls = get_items(page_link)
        
        for i, curl in enumerate(сurls):
            start = time.time()
            item = get_item(curl, headers, session)
            end = time.time()
            CATEGORY_ITEMS.append(item)
            print('Current operation took', str(end - start))
            print('{} / {}'.format(i + 1,len(сurls)))
            break     #<---test to take 1 item from page
        print('All items at the page {} are collected.'.format(page))
        break         #<---test to take 1 page from category
    print('All items at the current category are collected.')         
    return CATEGORY_ITEMS


# Finding item title from html soup object "link"
def get_title(link):
    return link.find(class_='x-title').get_text()


# Finding item code from html soup object "link"
def get_itemcode(link):
    return link.find('div', attrs={'data-bazooka' : 'AdvertUrlTrackerMako'})['data-advert-url-tracker-mako-product-id']


# Finding item attributes from html soup object "link"
def get_attributes(link):
    
    attributes = ''
    attributes_vis = link.find_all('tr', attrs={'class' : 'x-attributes__row js-attributes'})
    attributes_unvis = link.find_all('tr', attrs={'class' : 'x-attributes__row js-attributes x-hidden'})

    for i, attribute in enumerate(attributes_vis):
        attribute = attribute.find('td', attrs={'class' : 'x-attributes__right'})
        if len(attribute.next_element.next_element.text) > 0:
            attribute = attribute.get_text()
            attributes += attribute.strip() + ';'
    
    for attribute in attributes_unvis:
        attribute = attribute.find('td', attrs={'class' : 'x-attributes__right'})
        if len(attribute.next_element.next_element.text) > 0:
            attribute = attribute.get_text()
            attributes += attribute.strip() + ';'   
        
    return attributes


# Finding item description from html soup object "link"
def get_description(link):
     description = link.find('div', {'data-extend' : 'FlexibleTable'}).get_text()
     return description.strip()


# Finding item image urls from html soup object "link"
def get_image_urls(link):
    images_json = link.find('div', {'data-bazooka' : 'ProductGallery'})['data-bazooka-props']
    images = json.loads(images_json)
    return [img['image_url_640x640'] for img in images["images"]]


# Compress item image links from html soup object "link", then got json conversed to dict of urls
def get_imagelinks(link):
    urls = get_image_urls(link)
    return ';'.join(urls)


# Save name of image by specific name wih path, from urls
def save_images(link, itemcode, imagedir):
    image_urls = get_image_urls(link)
    if not os.path.exists(imagedir):
        os.makedirs(imagedir)
    
    for i, img_url in enumerate(image_urls, 1):  
        response = requests.get(img_url)
        if response.status_code == 200:
            img_path = f'{imagedir}{itemcode}_{i}.jpg'
            with open(img_path, 'wb') as f:
                f.write(response.content)


# Function, that collect all information about item
def get_item(url, headers, session):
    link = get_htmlsoup(url, headers, session)
    title = get_title(link)
    itemcode = get_itemcode(link)
    attributes = get_attributes(link)
    description = get_description(link)
    imagelinks = get_imagelinks(link)
    #save_images(link, itemcode, DEFAULT_SAVE_IMG_PATH)

    print(time.ctime(), url, 'is collected succesfully!')
    return [url, title, itemcode, attributes, description, imagelinks]


# Function writes results to excel sheets
def xls_writer(data, sheet_name):
    
    global EXCEL_FILE
    df = DataFrame(data, columns=[
                                    'Ссылка на товар', 
                                    'Название', 
                                    'Код товара', 
                                    'Все характеристики', 
                                    'Описание товара',
                                    'Ссылки на фото'
                                    ])

    with ExcelWriter(EXCEL_FILE, mode='a', engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


# Routing by site and its categories and subcategories
def DFS(parent_link, headers, session, cat_name=None):
    
    categories = []
    categories_name = []
    print('Dealing with',parent_link)
    tag = get_htmlsoup(parent_link, headers, session)
    tags = tag.find_all('li', class_='x-category-tile__item')

    if cat_name:
        pos = cat_name.rfind('/')
        cat_name = cat_name[pos + 1: ]
        cat_name = cat_name[:31]

    if len(tags) > 0:
        print(time.ctime(),parent_link,'consists these categories:')
        items = []
        
        for item in tags:
            link = item.find('a')['href']
            
            if ('promo' in link and '=' in link) or ('promo' not in link and '=' not in link):
                categories.append('http://prom.ua'+link)
                categories_name.append(link)
                print("----",link)

        for cat, cat_name in zip(categories,categories_name):
            DFS(cat, headers, session, cat_name=cat_name)
        
    else:
        CATEGORY_ITEMS = scrap_controller(parent_link, headers, session)
        xls_writer(CATEGORY_ITEMS, cat_name)

#DFS(TEST_PAGE, headers, session)

# Getting consumer goods (to .xlsx)
DFS(PAGE_CONSUMER, headers, session)

# Getting b2b goods (to .xlsx)
DFS(PAGE_B2B, headers, session)


print('\n')
print(32 * '=','END',32 * '=')
print('\n')
