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
from datetime import datetime as dt
from datetime import timedelta 
import sys
import time



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
            'hitbtc2',
            'binance',
            'bittrex',
            'bitfinex',
            'kucoin',
            'gdax',
            'poloniex',
            'kraken',
            'liqui',
            'bitstamp',
            'cryptopia',
            'huobi'
            ]
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
    slack_token = ##
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
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
            print('base_currency =', base_currency, exchange[1], 'connection not possible with ccxt')
            continue
        
        for pair in pairs:
            if '/' + base_currency in pair:
                if base_currency == 'USD' and 'USDT' in pair:
                    continue
                else:
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


def get_volume_final(exchange, general_price, volume_needed, pair):
    try:
        api_vol_data = []
        api_times = []
        
        function = getattr(ccxt,exchange)()
        
        now = time.time() 
        now_format = dt.fromtimestamp(now) 
        last_hour = now_format - timedelta(hours=1)
        last_hour_format = last_hour.timestamp() * 1000
        
        api_data = function.fetch_trades(pair,limit = 100)
        
        for data in api_data:
            if data['timestamp'] > last_hour_format:
                api_vol_data.append(data['amount'])
                api_times.append(data['timestamp']) 
                
        sum_api_vol = sum(api_vol_data) * general_price
        
        if sum_api_vol > volume_needed:
            return sum_api_vol
        else:
            return 0
    except Exception as e:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        print('exchange =', exchange, 'pair =', pair)
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
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        print('price not found in get_vola:', coin, base_currency, receiving_exchange)
        
    price_volatility = receiving_change
    
    return price_volatility


def confidence_check(delta, price_volatility):
    
    confidence = mean_confidence_interval(price_volatility)
    confidence_left = confidence[0]
    confidence_right = confidence[1]
    
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
    for symbol_with_exchange in tqdm(symbols_with_exchanges):
        pair = symbol_with_exchange[0]
        
        final_dict[pair] = {}
        final_dict[pair]["exchanges"] = {}
        
        try:
            r = requests.get('https://min-api.cryptocompare.com/data/price?fsym=' + pair.replace('/' + base_currency, '') + '&tsyms=' + base_currency)
            #print('https://min-api.cryptocompare.com/data/price?fsym=' + pair.replace('/' + base_currency, '') + '&tsyms=' + base_currency)
            response = r.json()
            general_price = response[base_currency]
        except Exception as e:
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
            print('general_price creation didnt work:', pair)
            continue

        try:
            for exchange in symbol_with_exchange[1]:
                    
                volume = get_volume_final(exchange, general_price, volume_needed, pair)
                #print('Exchange:', exchange, ', pair:', pair, ', volume:', volume, ', min volume needed:', volume_needed)

                if volume != 0:
                    final_dict[pair]["exchanges"][exchange] = {
                                            "price": getattr(ccxt,exchange)().fetch_ticker(pair)['last'],
                                            "volume": volume
                    }
                else:
                    continue
                    
        except Exception as e:
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
            print('Dict creation failed')
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
    
    order_size = 0.05 # in BTC
    volume_needed_btc = order_size * 400 / 24
    base_currencies = ['BTC', 'ETH', 'USDT', 'USD']
    
    for base_currency in base_currencies:
       
        volume_needed = volume_needed_btc / transfer_price(base_currency)
        
        
        symbols = get_shared_pairs(exchanges, base_currency)
        #print('base curr:', base_currency)
        #print(symbols)
        deduped_symbols = dedup(symbols)
        
        symbols_with_exchanges = all_exchanges_for_symbol(deduped_symbols, symbols)
        
        print('Creating dict:')
        symbols_dict = dict_creation(symbols_with_exchanges, base_currency, volume_needed)
        
        #print(len(symbols_dict), 'left')
        
        opportunity_pairs = opportunity(symbols_dict)
        
        #print(len(opportunity_pairs), 'left')
        
        print('Checking opportunities:')
        for opportunity_pair in tqdm(opportunity_pairs):
            price_volatility = get_vola(opportunity_pair[1], base_currency, opportunity_pair[3][0])
            confidence = confidence_check(opportunity_pair[0], price_volatility)
            
            if confidence != False:
                    
                prices_message = 'Buy '+ opportunity_pair[1] +' on: '+ opportunity_pair[2][0] +' ('+ str(opportunity_pair[2][1]) +')\nSend to: '+ opportunity_pair[3][0]+' ('+ str(opportunity_pair[3][1]) +')\nOpportunity: '+ str(opportunity_pair[0])+  '\nConfidence: ' + str(confidence)
                print(prices_message)
                send_slack_message(prices_message + '\n --------------- \n')
                 
                print(opportunity_pair, 'moon!')
            else:
                print('no moon')
                
main_function()
print('DONE')
