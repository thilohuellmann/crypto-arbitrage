import ccxt
import json
from tqdm import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import mlab
import scipy as sp
import scipy.stats
import requests
import csv

binance = ccxt.binance() # USDT

#CSV input
path = '/Users/alexanderreichhardt/Desktop/ExchangesPairs.csv'
with open(path,'r') as file:
    reader = csv.reader(file, delimiter=',')
    header = next(reader)
    final =  [] 
    exchanges = [] 
    usd = []
    usdt = []
    
    for row in reader: 
        data = []       
        for i in range(2,len(row)):
            row[i] = int(row[i])
            if row[i] == 1:
                data.append(header[i])           
        final.append([row[0],data])
          
        if row[1] == 'usd':
            usd.append(row[0])
        elif row[1] == 'usdt':
            usdt.append(row[0])
        
        formula = getattr(ccxt,row[0])()
        name = row[0]
        exchanges.append([formula,name])

def check_vola(exchange, coin, opportunity):

    r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym=' + coin + '&tsym=BTC&limit=101&e=' + exchange)
    response = r.json()
    exchange_price_data = response['Data']

    r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym=' + coin + '&tsym=BTC&limit=101&e=Binance')
    response = r.json()
    binance_price_data = response['Data']
    
    ex_avg = []
    for ex in exchange_price_data:
        ex_avg.append((ex['high']+ex['low']) / 2)
    
    bi_avg = []
    for bi in binance_price_data:
        bi_avg.append((bi['high']+bi['low']) / 2)
        
    ex_change = []
    for i in range(len(ex_avg)-1):
        yesterday = ex_avg[i]
        today = ex_avg[i + 1]
        ex_change.append(((today - yesterday) / yesterday) * 100)
    
    bi_change = []
    for i in range(len(bi_avg)-1):
        yesterday = bi_avg[i]
        today = bi_avg[i + 1]
        bi_change.append(((today - yesterday) / yesterday) * 100)
        
        
    #########################################
    
    
    if opportunity < 0: # negative percentages ; buy on binance; check exchange price vola
        prices = ex_change
        buy_signal = 'buy on binance'
    else: # positive percentages
        prices = bi_change
        buy_signal = 'buy on ' + exchange
        

    # select "receiving' exchange and check volatility 
    confidence = mean_confidence_interval(prices)
    confidence_left = confidence[0]
    confidence_right = confidence[1]
    
    if abs(opportunity) >= abs(confidence_left) and abs(opportunity) >= abs(confidence_right):
        if get_volume(coin, exchange) >= 3 and get_volume(coin, 'binance') >= 3:
            print()
            print(exchange, coin)
            print('Opportunity:', opportunity)
            print('Confidence:', confidence)
            print(buy_signal)
            plot_standard_dist(prices)
            print()
        
        else:
            print(coin, 'volume lower than 3 BTC/hour')
    else:
        print(coin, exchange, 'opportunity not in confidence interval')
    
def plot_standard_dist(change):
    plt.hist(change,99)
    plt.show()
    
def get_volume(coin, exchange):
    try:
        r = requests.get('https://min-api.cryptocompare.com/data/histohour?fsym=' + coin + '&tsym=BTC&limit=1&aggregate=1&e=' + exchange)
        response = r.json()
        return response['Data'][0]['volumeto']
    except:
        return 0
    
def get_fiat(exchange):
    
    if exchange in usd:
        fiat = 'USD'
    elif exchange in usdt:
        fiat = 'USDT'
    else:
        print(exchange, 'not found in get_fiat function')
        
    return fiat

def get_ticker(exchange):
    fiat = get_fiat(exchange[1])
    ticker = exchange[0].fetch_ticker('BTC/' + fiat)['last']
        
    return ticker

def get_pair(exchange, pair):
    pair = exchange.fetch_ticker(pair)['last']
    return pair

def get_pairs(exchange):
   
    btc_pairs = []
    for i in range(len(final)):
        if final[i][0].lower() == exchange:
            btc_pairs = final[i][1]
       
  
    return btc_pairs
    
def opportunities(exchange): # fiat = USD or USDT
    
    count = 0
    deltas = []
    pairs = []
    
    btc_pairs = get_pairs(exchange[1])
    
    for pair in tqdm(btc_pairs):

        if count == 0:
            binance_usd = binance.fetch_ticker('BTC/USDT')['last']
            exchange_usd = get_ticker(exchange)
            count += 1

        binance_pair = binance.fetch_ticker(pair)['last']

        try:
            exchange_pair = get_pair(exchange[0], pair)
            
        except Exception as e:
            continue

        delta = ((binance_pair / exchange_pair) - 1) * 100
        deltas.append(delta)
        pairs.append(pair)
    
    for final_delta, pair in zip(deltas, pairs):
        if abs(final_delta) >= 2:
            coin = pair.replace('/BTC', '')
            check_vola(exchange[1], coin, final_delta)
        else:
            print(pair, exchange[1], 'no opp: lower than 2%')

def mean_confidence_interval(data):
    a = 1.0*np.array(data)
    n = len(a)
    std = np.std(a)
    m = np.mean(a)
    h = std * 1.68
    return m-h, m+h
            
for exchange in exchanges:
    print('EXCHANGE:', exchange[1])
    opportunities(exchange)
    print('DONE')
