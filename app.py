import ccxt
import json
from tqdm import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import mlab
import scipy as sp
import scipy.stats
import requests
#from slackclient import SlackClient
from time import sleep
#import csv

# Free Trial (1 opportunity (the best one) + blurred ones)
# 4,99€ subscription for full acess
# (100 seats – in percent?) 999€ lifetime but 'contact us'
# Opportunities: Discord, Telegram, Whatsapp, SMS (Twilio), Email, Slack
# Spread: Friends / Berlin, Telegram Chats, Twitter, betalist, hackernews, reddit, ProductHunt, Bitcointalk(Foren)

order_size = 0.01 # in BTC
volume_needed = order_size * 400
base_currency = 'BTC'

exchanges = ['okex',
            'hitbtc',
            'exmo',
            'gatecoin',
            'binance']
             
"""
            'yobit',
            'bittrex',
            'bitfinex',
            'gdax',
            'gatecoin',
            'poloniex',
            'kraken',
            'anxpro',
            'liqui',
            'bitflyer',
            'bitbay',
            'bitlish',
            'bitstamp',
            'cex',
            'dsx',
            'mixcoins',
            'quadrigacx',
            'southxchange',
            'wex',
            'coinsecure',
            'fybsg']
"""

e = [] # interim array
for exchange in exchanges:
    function = getattr(ccxt,exchange)()
    e.append([function, exchange])

exchanges = e

def get_ccxt(exchange):
    function = getattr(ccxt,exchange)()
    return function

def get_shared_pairs(exchanges):
    
    symbols = []
    for exchange in exchanges:
        
        pairs = []
        try:
            exchange[0].load_markets()
            pairs = list(exchange[0].markets.keys())
        except:
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
    
    
shared_pairs = get_shared_pairs(exchanges) 
symbols = dedup(shared_pairs)



def all_exchanges_for_symbol(symbols, shared_pairs):

    symbols_with_exchanges = []

    for symbol in symbols:
        thilo = []
        for pair in shared_pairs:
           
            if symbol == pair[0]:
                thilo.append(pair[1])

        symbols_with_exchanges.append([symbol,thilo])
    return symbols_with_exchanges
    
symbols_with_exchanges = all_exchanges_for_symbol(symbols,shared_pairs) 

def get_volume(coin, exchange):
    
    pair = coin + '/BTC'
    
    try:
        function = getattr(ccxt,exchange)()
        volume = function.fetch_ticker(pair)['baseVolume']
        btc_volume = volume 
        
        #print('volume for', coin, exchange, ':', btc_volume)
        
        return btc_volume
    
    except:
        print('volume for', coin, exchange, 'not found in API')
        return 0   

final_dict = {}
#symbols_with_exchanges = [['TRX/BTC', ['okex', 'hitbtc', 'gatecoin', 'binance']], ['OMG/BTC', ['okex', 'hitbtc', 'binance']]]
for i in range(len(symbols_with_exchanges)):
    pair = symbols_with_exchanges[i][0]
    print(pair)
    final_dict[pair] = {}
    final_dict[pair]["exchanges"] = {}
    for exchange in tqdm(symbols_with_exchanges[i][1]):
        final_dict[pair]["exchanges"][exchange] = {
                                "price": getattr(ccxt,exchange)().fetch_ticker(pair)['last'],
                                "volume": get_volume(symbols_with_exchanges[i][0].replace('/BTC', ''),exchange)
                                }
   
