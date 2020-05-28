# Steam Marketplace Web Scraper - CS:GO Knives

'''
----------------------------
    SCRIPT FUNCTIONALITY
----------------------------

This script extracts CS:GO knife information currently on the Steam Marketplace. It automatically goes page-to-page
via Selenium WebDriver.  The program extracts information about each knife, including:
- Knife type (e.g. Butterfly Knife, Bowie Knife)
- Knife skin (e.g. Doppler, Tiger Tooth)
- Knife skin quality (e.g. Minimal Wear, Battle-Scarred
- StatTrak™ (whether or not the knife can track kills made with it)
- Lowest current selling price of knife on Steam Marketplace
- Current quantity of knife on Steam Marketplace

-----------------------------
    IMPORTANT INFORMATION
-----------------------------

SQLite3:

The information is output to a SQL database. To access this database, ensure that SQLite3 is installed on your computer
and run SQLite3 via CMD from the working directory folder on the knives database. Make sure the path of SQLite3 is set
as well by running (through the specific user's folder):

C:/Users/Windows_User>set PATH=%PATH%;C:/sqlite

This assumes you have installed the necessary SQLite3 files in C:/sqlite.

Selenium:

This script requires Selenium WebDriver to go through the dynamic pages within the Steam Marketplace. Please download
the chromedriver.exe file through Selenium's website and put this file in the working directory for program.py if it is
not already there.
'''

import sqlite3
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import time

# Connect database to store data in.
conn = sqlite3.connect('knives.db')

# Create cursor object.
c = conn.cursor()

# Create table (if not made yet).
try:
    c.execute("CREATE TABLE knives ("
              "knife_type TEXT, "
              "knife_skin TEXT, "
              "knife_skin_quality TEXT, "
              "stattrak INTEGER, "
              "price_usd REAL, "
              "quantity INTEGER,"
              "CONSTRAINT knife_cons UNIQUE (knife_type, knife_skin, knife_skin_quality, stattrak))")
    conn.commit()
except:
    print('Table already made.')

# Initial page/ability to loop.
page_number = 1 # Begins on first page of search results.
able_to_loop = True

# Web scraper stops when no more knives are found on a loaded page.
while able_to_loop == True:

    page_loaded = False
    attempts = 0

    while page_loaded == False and attempts != 3:
        try:
            wd = webdriver.Chrome('chromedriver.exe')
            print(f"Attempting to scrape knives from page {page_number}.....")
            # appid represents the game id of CS:GO and it is querying the word "knife".
            url = 'https://steamcommunity.com/market/search?appid=730&q=knife#p' + str(page_number) + '_default_desc'
            wd.get(url)
            wait = WebDriverWait(wd, 30)

            # Waits until the element which shows a knife has been visually loaded on the page.
            # Without this, the WebDriver may not have enough time to extract the knives' information.
            wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'market_listing_row_link')))
            html_page = wd.page_source
            if html_page:
                page_loaded = True
            wd.quit()

        except:
            attempts += 1
            if attempts == 3:
                print(f'Max attempts reached. Quitting. \n')
                able_to_loop = False
            else:
                print(f'Unable to load page. Trying again. {attempts}/3 attempts.')
            wd.quit()

    if able_to_loop == False:
        break

    # Generates a soup object and finds all of the 'a' elements which store all information about each knife.
    soup = BeautifulSoup(html_page, "html.parser")
    knives = soup.find_all('a', class_='market_listing_row_link')
    actual_knives_added = len(knives)  # Will be lower if duplicates are found.
    for knife in knives:

        # Full name extraction follows this pattern:
        # "★ (is_stattrak) (knife_type) | (knife_skin) ((knife_skin_quality))"

        # Extracts full name by finding the specific class where the information is stored.
        full_name = knife.find(class_='market_listing_item_name').get_text()
        cut_name = full_name[2:] # Cuts "★ " off

        # Checks if knife is StatTrak™
        is_stattrak = 0
        if "StatTrak" in cut_name:
            is_stattrak = 1
            cut_name = cut_name[10:]

        knife_type = None
        knife_skin = None
        knife_skin_quality = None

        # Checks to see if the knife has a skin in the extracted string (through finding a '|').
        if '|' not in cut_name:
            knife_type = cut_name
            knife_skin = 'N/A'
            knife_skin_quality = 'N/A'
        else:
            # String manipulation to extract above values (if applicable)
            temp_word = ''
            for char in cut_name:
                temp_word += char
                if char == '|':
                    knife_type = temp_word[0:-2]
                    temp_word = ''
                if char == '(':
                    knife_skin = temp_word[1:-2]
                    temp_word = ''
                if char == ')':
                    knife_skin_quality = temp_word[:-1]
                    temp_word = ''

        # Extract price/quantity of knives through spans (check HTML for these locations via Inspect).
        price = knife.select('span.normal_price > span.normal_price')[0].get_text()
        price = price[1:]
        quantity = knife.select('span.market_listing_num_listings_qty')[0].get_text()

        # Uploads data to the SQL database.
        if knife_skin != None and knife_skin_quality != None: # Checks to see if entry follows format of knife
            try:
                data = (knife_type, knife_skin, knife_skin_quality, is_stattrak, price, quantity)
                query = f"INSERT INTO knives VALUES (?,?,?,?,?,?)"
                c.execute(query, data)
                conn.commit()
            except:
                actual_knives_added -= 1 # Duplicate found and therefore will not be added.

    delay = 30 # s
    if actual_knives_added == 0:
        print(f'No knives scraped on page {page_number} have been added to knives.db.')
        print(f'All scraped knives were found to be duplicates.')
    elif actual_knives_added == 1:
        print(f'1 knife scraped on page {page_number} has been added to knives.db.')
        print(f'{len(knives) - actual_knives_added} duplicate(s) found and not added.')
    elif actual_knives_added == len(knives):
        print(f'{actual_knives_added} knives scraped on page {page_number} have been added to knives.db.')
    else:
        print(f'{actual_knives_added} knives scraped on page {page_number} have been added to knives.db.')
        print(f'{len(knives) - actual_knives_added} duplicate(s) found and not added.')

    print(f'Waiting {delay} seconds before next request. \n')
    time.sleep(delay) # Delays requests to server to prevent temporary server blocking.
    page_number += 1 # Goes to the next page.

print('Web scraping completed.')
c.execute("SELECT COUNT(*) FROM knives")
conn.commit()

knives_in_database = c.fetchall()[0][0]
print(f'{knives_in_database} knives are now in knives.db.')
conn.close()