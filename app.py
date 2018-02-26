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
#import csv

order_size = 0.01 # in BTC
volume_needed = order_size * 400

def send_slack_message(message):
    slack_token = 'INSERT'
    sc = SlackClient(slack_token)

    sc.api_call(
      "chat.postMessage",
      channel="#tothemoon",
      text=str(message)
    )


def get_volume(coin, price, exchange):
    
    pair = coin + '/BTC'
    
    try:
        function = getattr(ccxt,exchange)()
        volume = function.fetch_ticker(pair)['baseVolume']
        btc_volume = volume * price
        
        #print('volume for', coin, exchange, ':', btc_volume)
        
        return btc_volume
    
    except:
        print('volume for', coin, exchange, 'not found in API')
        return 0
       
def mean_confidence_interval(data):
    a = 1.0*np.array(data)
    n = len(a)
    std = np.std(a)
    m = np.mean(a)
    h = std * 1
    return m-h, m+h

def plot_standard_dist(change):
    plt.hist(change,99)
    plt.show()

def check_vola(coin, delta, sending_exchange, receiving_exchange):
    
    coin = coin.replace('/BTC', '')
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
    print('confidence:',confidence)
    
    if delta >= abs(confidence_left) and delta >= abs(confidence_right):
        print()
        print('Buy', coin, 'on', sending_exchange)
        print('Send to', receiving_exchange)
        print('Opportunity:', delta)
        print('Confidence:', confidence)
        plot_standard_dist(prices)
        print()
        
        message = 'Buy ' + coin + ' on: ' + sending_exchange + '\nSend to: ' + receiving_exchange + '\nOpportunity: ' + str(delta) + '\nConfidence interval: ' + str(confidence) 
        send_slack_message(message)
        
        return True
    else:
        print(coin, sending_exchange, receiving_exchange, 'opportunity not in confidence interval')
        plot_standard_dist(prices)
        
        
    
########################
    
    
exchanges = ['okex', # 'exmo','gatecoin', 'yobit'
            'hitbtc',
            'binance',
            'bittrex',
            #'bitfinex',
            'gdax',
            'gatecoin',
            'poloniex',
            'kraken',
            #'anxpro',
            #'liqui',
            #'bitflyer',
            #'bitbay',
            #'bitlish',
            #'bitstamp',
            'cex',
            #'dsx',
            #'mixcoins',
            #'quadrigacx',
            'southxchange']
            #'wex',
            #'coinsecure',
            #'fybsg'

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


########### PRICE DELTAS ###########

opportunity_pairs = []

print()
print('CHECKING VOLUME AND PRICE DELTAS:')
print()

for pair in tqdm(final):
    prices = []
    ex = []
    for i in range(len(pairs_with_prices_and_exchange)):
        for j in range(len(pairs_with_prices_and_exchange[i][0])):
            if pair == pairs_with_prices_and_exchange[i][0][j][0]:
                prices.append(pairs_with_prices_and_exchange[i][0][j][1])
                ex.append(pairs_with_prices_and_exchange[i][1])
                
    moon = [[pair, prices, ex]] #['LTC/USD', [[3.23,232.3,23.3], ['binance', 'okex', 'bittrex']],..]
    
    prices = []
    ex = []
    
    for exchange, price in zip(moon[0][2], moon[0][1]):
        vol = get_volume(pair.replace('/BTC', ''), price, exchange)
        
        if vol > volume_needed:
            prices.append(price)
            ex.append(exchange)

    jakob = [pair, prices, ex]

    if len(jakob[2]) > 2:
        moon = jakob
    else:
        continue
    
    min_price = min(moon[1])
    max_price = max(moon[1])
    delta = (min_price / max_price - 1) * 100
    
    min_index = moon[1].index(min(moon[1]))
    max_index = moon[1].index(max(moon[1]))
    sending_exchange = moon[2][min_index]
    receiving_exchange = moon[2][max_index]
    
    if abs(delta) > 2:
        opportunity_pairs.append([pair, abs(delta), [min_price, sending_exchange], [max_price, receiving_exchange]])

print('Length of opportunity_pairs', len(opportunity_pairs))

######### VOLATILITY #########

print('Checking volatility:')
if len(opportunity_pairs) < 2:
    print('Volume check left no opportunities :/ no moon today')
    
for pair in tqdm(opportunity_pairs):
    if check_vola(pair[0], pair[1], pair[2][1], pair[3][1]) == True: #if Opp exists
        print(pair[2][1], 'price:', pair[2][0])
        print(pair[3][1], 'price:', pair[3][0])
        
        prices_message = str(pair[2][1]) + ' price: ' + str(pair[2][0]) + '\n' + str(pair[3][1]) + ' price: ' + str(pair[3][0])
        
        send_slack_message(prices_message + '\n --------------- \n')
    
    print()
    print('--------------------------- NEXT ----------------------------')
    print()
