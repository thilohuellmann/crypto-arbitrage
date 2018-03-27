import ccxt
import json
from tqdm import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import mlab
import scipy as sp
import scipy.stats
import requests
from slackclient import SlackClient
from time import sleep
import csv
import datetime


# Free Trial (1 opportunity (the best one) + blurred ones)
# 4,99€ subscription for full acess
# (100 seats – in percent?) 999€ lifetime but 'contact us'
# Opportunities: Discord, Telegram, Whatsapp, SMS (Twilio), Email, Slack
# Spread: Friends / Berlin, Telegram Chats, Twitter, betalist, hackernews, reddit, ProductHunt, Bitcointalk(Foren)
# plot
# volatility within our or across hourly avg? baevillage

def transfer_price(base_currency):
    r = requests.get('https://min-api.cryptocompare.com/data/price?fsym=' + base_currency + '&tsyms=BTC')
    response = r.json()
    price = response['BTC']
    return price
        

exchanges = ['okex',
            'hitbtc',
            'binance',
            'bittrex',
            'bitfinex',
            'kucoin',
            'gdax',
            'poloniex',
            'kraken',
            'liqui',
            'bitstamp']
            #'bitflyer',
            #'anxpro',
            #'gatecoin',
            #'yobit',
            #'exmo',
            #'bitbay',
            #'bitlish',
            #'cex',
            #'dsx',
            #'mixcoins',
            #'quadrigacx',
            #'southxchange',
            #'wex',
            #'fybsg',
            #'coinsecure']


def send_slack_message(message):
    slack_token = 'xoxp-300307099735-299365271877-320690374373-01a01d6df8232b58efdafe0a33bb68f8'
    sc = SlackClient(slack_token)

    sc.api_call(
      "chat.postMessage",
      channel="#tothemoon",
      text=str(message)
    )
                      

def get_ccxt(exchange):
    function = getattr(ccxt,exchange)()
    return function

def get_shared_pairs(exchanges, base_currency):
    
    symbols = []
    for exchange in exchanges:
        
        pairs = []
        try:
            exchange[0].load_markets()
            pairs = list(exchange[0].markets.keys())
        except Exception as e:
            print(e)
            print(exchange[1], 'connection not possible with ccxt')
            continue
        
        for pair in pairs:
            if '/' + base_currency in pair:
                symbols.append([pair, exchange[1]])
                
            
    return symbols


def dedup(symbols):
    
    total = []
    for s in symbols:
        total.append(s[0])

    dedup = [] # all pairs that are listed on 2+ exchanges
    for symbol in total:
        if total.count(symbol) > 1:
            dedup.append(symbol)

    dedup = list(set(dedup))
    return dedup


def all_exchanges_for_symbol(symbols, shared_pairs):

    symbols_with_exchanges = []
    for symbol in symbols:
        
        helper_array = []
        for pair in shared_pairs:
            
            if symbol == pair[0]:
                helper_array.append(pair[1])

        symbols_with_exchanges.append([symbol, helper_array])
    
    return symbols_with_exchanges
      
def get_volume(coin,base_currency,exchange,volume_needed):
    try:
        coin = coin.replace('/' + base_currency, '')
        r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym='+ coin + '&tsym='+ base_currency + '&limit=1&aggregate=1&e=' + exchange)
        response = r.json()
        volume_in_base_currency = response['Data'][0]['volumeto']
        print(coin,exchange,', volume_api: ',volume_in_base_currency)
        print(coin,exchange,', volume_needed ',volume_needed)
        if volume_in_base_currency > volume_needed:
            return volume_in_base_currency
        else:
            return 0
    except Exception as e:
        print(e)
        return 0
    
def get_vola(coin, base_currency, receiving_exchange):
    
    coin = coin.replace('/' + base_currency, '')
    r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym=' + coin + '&tsym=' + base_currency + '&limit=101&e=' + receiving_exchange)
    response = r.json()
    receiving_price_data = response['Data']
    
    receiving_change = []
    try:
        for ex1 in receiving_price_data:
            receiving_change.append(abs((ex1['high'] - ex1['low']) / ex1['low']) * 100)
    except Exception as e:
        print(e)
        print('price not found')
        
    price_volatility = receiving_change
    
    return price_volatility


def confidence_check(delta, price_volatility):
    
    confidence = mean_confidence_interval(price_volatility)
    confidence_left = confidence[0]
    confidence_right = confidence[1]
    print(delta)
    print('confidence_left: ', abs(confidence_left))
    print('confidence_right: ', abs(confidence_right))
    if delta >= abs(confidence_left) and delta >= abs(confidence_right):
        return str(confidence_left) + ', ' + str(confidence_right)
    else:
        return False
    
def mean_confidence_interval(data):
    a = 1.0*np.array(data)
    n = len(a)
    std = np.std(a)
    m = np.mean(a)
    h = std * 1.68
    return m-h, m+h

def plot_standard_dist(change):
    hi = plt.hist(change,99)
    plt.show()
    return
        
def dict_creation(symbols_with_exchanges, base_currency, volume_needed):
    
    final_dict = {}
    for i in tqdm(range(len(symbols_with_exchanges))):#len(symbols_with_exchanges
        pair = symbols_with_exchanges[i][0]
        
        final_dict[pair] = {}
        final_dict[pair]["exchanges"] = {}
        
        r = requests.get('https://min-api.cryptocompare.com/data/price?fsym=' + pair.replace('/' + base_currency, '') + '&tsyms=' + base_currency)
        response = r.json()
        
        try:
            general_price = response[base_currency]
        except Exception as e:
            print(e)
            continue

        try:
            for exchange in symbols_with_exchanges[i][1]:
                volume = get_volume(pair, base_currency, exchange, volume_needed)

                if volume != 0:
                    final_dict[pair]["exchanges"][exchange] = {
                                            "price": getattr(ccxt,exchange)().fetch_ticker(pair)['last'],
                                            "volume": volume
                    }
                else:
                    continue
        except Exception as e:
            print(e)
            continue

    return final_dict

def opportunity(symbols_dict):
    
    opportunities = []
    for symbol in symbols_dict:
        
        if len(symbols_dict[symbol]['exchanges']) == 1:
            continue
            
        else:
            price_list = []
            for exchange in symbols_dict[symbol]['exchanges']:
                price_list.append([exchange, symbols_dict[symbol]['exchanges'][exchange]['price']])
            
            deltas = []
            for price in price_list:
                for price2 in price_list:
                    
                    if price[1] > price2[1]:
                        delta = abs(price[1] / price2[1] - 1) * 100
                            
                        if delta < 100 and delta > 2 and delta not in deltas:
                            deltas.append(delta)
                            opportunities.append([delta, symbol, [price2[0], price2[1]], [price[0], price[1]]])
                        else:
                            continue
                        
                    else:
                        delta = abs(price2[1] / price[1] - 1) * 100
                        
                        if delta < 100 and delta > 2 and delta not in deltas:
                            deltas.append(delta)
                            opportunities.append([delta, symbol, [price[0], price[1]], [price2[0], price2[1]]])
                        else:
                            continue
                
    return opportunities
            ##opportunities.append([delta, symbol, [price[0], price[1]], [price2[0], price2[1]]]) 


############################################################

e = [] # interim array
for exchange in exchanges:
    function = getattr(ccxt,exchange)()
    e.append([function, exchange])

exchanges = e

def main_function():
    
    order_size = 0.001 # in BTC
    volume_needed = order_size * 40
    base_currencies = ['BTC', 'ETH', 'USDT', 'USD']
    
    for base_currency in base_currencies:
        volume_needed = volume_needed / transfer_price(base_currency)
        print(volume_needed)
        print(base_currency)
        
        symbols = get_shared_pairs(exchanges, base_currency)
        deduped_symbols = dedup(symbols)
        
        symbols_with_exchanges = all_exchanges_for_symbol(deduped_symbols, symbols)
        
        print('Creating dict:')
        symbols_dict = dict_creation(symbols_with_exchanges, base_currency, volume_needed)

        opportunity_pairs = opportunity(symbols_dict)
        print(opportunity_pairs)
        
        print('Checking opportunities:')
        for opportunity_pair in tqdm(opportunity_pairs):
            price_volatility = get_vola(opportunity_pair[1], base_currency, opportunity_pair[3][0])
            confidence = confidence_check(opportunity_pair[0], price_volatility)
            
            if confidence != False:
                    
                prices_message = 'Buy '+ opportunity_pair[1] +' on: '+ opportunity_pair[2][0] +' ('+ str(opportunity_pair[2][1]) +')\nSend to: '+ opportunity_pair[3][0]+' ('+ str(opportunity_pair[3][1]) +')\nOpportunity: '+ str(opportunity_pair[0])+  '\nConfidence: ' + str(confidence)
                send_slack_message(prices_message + '\n --------------- \n')
                 
                print(opportunity_pair, 'moon!')
            else:
                print('no moon')
        

main_function()
print('DONE')
