import ccxt
import json
from tqdm import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import mlab
import scipy as sp
import scipy.stats
import requests
#import csv

exchanges = ['binance', 'okex', 'bittrex', 'huobi']
e = [] # interim array
for exchange in exchanges:
    function = getattr(ccxt,exchange)()
    e.append([function, exchange])

exchanges = e

########### FIND PAIRS THAT ARE ON 2+ EXCHANGES #############

symbols_all = []

for exchange in exchanges:
    exchange[0].load_markets()
    pairs = list(exchange[0].markets.keys())
    
    symbols_single = []
    
    for pair in pairs:
        if '/BTC' in pair:
            symbols_single.append(pair)
            
    symbols_all.append([list(set(symbols_single)), exchange[1]])

full = []
for s in symbols_all:
    
    for i in s[0]:
        full.append(i)
        

final = [] # all pairs that are listed on 2+ exchanges
for symbol in full:
    if full.count(symbol) > 1:
        final.append(symbol)

final = list(set(final))

symbols_all_final = [] ######## !!!!!!! <<<<<<<

for exchange in symbols_all:
    alex = []
    for i in exchange[0]:
        if i in final:
            alex.append(i)
            
    symbols_all_final.append([alex, exchange[1]])

#print(symbols_all_final)

########### PRICES ############

# RESULT: pairs_with_prices = [[['LTC/BTC', 100], ['ETH/BTC', 200]], 'binance']


pairs_with_prices_and_exchange = []

for exchange, pairs in zip(exchanges, symbols_all_final):
    
    pairs_with_prices = []
    for pair in tqdm(pairs[0]):

        price = exchange[0].fetch_ticker(pair)['last']
        pairs_with_prices.append([pair, price])
            
    
    pairs_with_prices_and_exchange.append(([pairs_with_prices, exchange[1]]))

#print(pairs_with_prices_and_exchange)


########### PRICE DELTAS ###########

opportunity_pairs = []

for pair in final:
    prices = []
    ex = []
    for i in range(len(pairs_with_prices_and_exchange)):
        for j in range(len(pairs_with_prices_and_exchange[i][0])):
            if pair == pairs_with_prices_and_exchange[i][0][j][0]:
                prices.append(pairs_with_prices_and_exchange[i][0][j][1])
                ex.append(pairs_with_prices_and_exchange[i][1])
                
    moon = [pair, prices, ex]
    min_price = min(moon[1])
    max_price = max(moon[1])
    delta = (min_price / max_price - 1) * 100
    
    min_index = moon[1].index(min(moon[1]))
    max_index = moon[1].index(max(moon[1]))
    sending_exchange = moon[2][min_index]
    receiving_exchange = moon[2][max_index]
    
    if abs(delta) > 2:
        opportunity_pairs.append([pair, abs(delta), [min_price, sending_exchange], [max_price, receiving_exchange]])
    
#print(opportunity_pairs)

######### VOLATILITY #########


def get_volume(coin, exchange):
    try:
        r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym=' + coin + '&tsym=BTC&limit=1&aggregate=1&e=' + exchange)
        response = r.json()
        return response['Data'][0]['volumeto']
    except:
        return 0

volume_cleaned = []
for pair in opportunity_pairs:
    coin = pair[0].replace('/BTC', '')
    volume_min = get_volume(coin, pair[2][1])
    volume_max = get_volume(coin, pair[3][1])
    
    if volume_min >= 0.01 and volume_max >= 0.01:
        volume_cleaned.append(pair)
        
for i in range(len(volume_cleaned)):
    check_vola(volume_cleaned[i][0], volume_cleaned[i][1], volume_cleaned[i][2][1], volume_cleaned[i][3][1]) 
        
        
def mean_confidence_interval(data):
    a = 1.0*np.array(data)
    n = len(a)
    std = np.std(a)
    m = np.mean(a)
    h = std * 1.68
    return m-h, m+h

def plot_standard_dist(change):
    plt.hist(change,99)
    plt.show()

def check_vola(coin, delta, sending_exchange, receiving_exchange):

    r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym=' + coin + '&tsym=BTC&limit=101&e=' + sending_exchange)
    response = r.json()
    sending_price_data = response['Data']

    r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym=' + coin + '&tsym=BTC&limit=101&e=' + receiving_exchange)
    response = r.json()
    receiving_price_data = response['Data']
    
    sending_avg = []
    for ex1 in sending_price_data:
        sending_avg.append((ex1['high']+ex1['low']) / 2)
    
    receiving_avg = []
    for ex2 in receiving_price_data:
        receiving_avg.append((ex2['high']+ex2['low']) / 2)
        
    sending_change = []
    for i in range(len(sending_avg)-1):
        yesterday = sending_avg[i]
        today = sending_avg[i + 1]
        sending_change.append(((today - yesterday) / yesterday) * 100)
    
    receiving_change = []
    for i in range(len(sending_avg)-1):
        yesterday = receiving_avg[i]
        today = receiving_avg[i + 1]
        receiving_change.append(((today - yesterday) / yesterday) * 100)
        
    prices = receiving_change # select "receiving' exchange and check volatility 
    
    confidence = mean_confidence_interval(prices)
    confidence_left = confidence[0]
    confidence_right = confidence[1]
    
    if delta >= abs(confidence_left) and delta >= abs(confidence_right):
        print()
        print(exchange, coin)
        print('Opportunity:', opportunity)
        print('Confidence:', confidence)
        print(buy_signal)
        plot_standard_dist(prices)
        print()
    else:
        print(coin, sending_exchange, receiving_exchange, 'opportunity not in confidence interval')        
