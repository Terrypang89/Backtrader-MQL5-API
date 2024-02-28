import backtrader as bt
import backtrader.indicators as btind
# import backtrader.indicators.MovAv as MovAv
from backtradermql5.mt5store import MTraderStore
from backtradermql5.mt5indicator import getMTraderIndicator
from backtradermql5.mt5chart import MTraderChart, ChartIndicator
from backtradermql5.mt5broker import MTraderBroker
from backtradermql5.mt5data import MTraderData
from datetime import datetime, timedelta, timezone
import time
import json
import pprint as pprint
# from bson import json_util
import pandas as pd
import re
import json
import time
import os
from flask import Flask, request
from threading import Timer

# import config
from handler import *

from src import api_server_start
from src import event_subscribe, event_unsubscribe, event_post
from src import StoppableThread
from src import log , create_logger

TIMECALL = 60
API_PORT = "api-port"
API_REV = "api-rev"

class SmaCross(bt.SignalStrategy):

    params = dict(
        smaperiod=5,
        trade=True,
        stake=0.1,
        exectype=bt.Order.Market,
        stopafter=0,
        valid=True,
        cancel=0,
        usebracket=True,
        donotcounter=False,
        sell=True,
    )

    def get_timestamp(self):
        timestamp = time.strftime("%Y-%m-%d %X")
        return timestamp

    def process_data_received(self, data:dict):
        print(f"on_data_received data = {data}\n")
        if not isinstance(data, dict):
            print(f"Incorrect data({data}) format received, SKIP.")
            return None
        try:
            # check if data ticker is 5m, 30m, 1 day
            self._new_data_received = True
            self._api_data = data
            
            return data
        except Exception as err:
            log.error(f"Sent webhook failed, reason: {err}")
        
    def retrieve_data_received(self):
        if self._new_data_received is True:
            self._new_data_received = False
            return self._api_data
        # elif 
        return None

    def __init__(self):

        self.orderid = list()
        self.order = None

        self.counttostop = 0
        self.datastatus = 0

        self._new_data_received = False
        self._api_data = ""
        # self._prev_api_data = ""
        event_subscribe(API_REV, self.process_data_received)

    def next(self):

        # set data printing
        txt = list()
        if self.live_data:
            txt.append('LIVE :')
            cash = self.broker.getcash()
        else:
            txt.append('NOT LIVE :')
            cash = "NA"
        
        txt.append('Data0')
        txt.append('%04d' % len(self.data0))
        dtfmt = '%Y-%m-%dT%H:%M:%S.%f'
        txt.append('{:f}'.format(self.data.datetime[0]))
        txt.append('%s' % self.data.datetime.datetime(0).strftime(dtfmt))
        txt.append('{:f}'.format(self.data.open[0]))
        txt.append('{:f}'.format(self.data.high[0]))
        txt.append('{:f}'.format(self.data.low[0]))
        txt.append('{:f}'.format(self.data.close[0]))
        txt.append('{:6d}'.format(int(self.data.volume[0])))
        txt.append('{:d}'.format(int(self.data.openinterest[0])))
        print(', '.join(txt))

        # 
        if not self.p.trade:
            return
        
        if not self.live_data:
            return

        updated_data = self.retrieve_data_received()
        if updated_data is None:
            return
        
        print(f"UPDATED data = {updated_data}")
        print(f"PRECHECK datastatus = {self.datastatus}, position = {self.position}, orderid = {self.orderid}, order = {self.order}, usebracket = {self.p.usebracket}, donorcounter = {self.p.donotcounter}, valid = {self.p.valid}, stake = {self.p.stake}, exectype={self.p.exectype}")

        # check if order is in 
        if self.orderid:
            for extracted_order in self.orderid:
                if updated_data["Alert"] == "SUPER_BUY" or updated_data["Alert"] == "SUPER_SELL":
                    print(f"CANCELING order {extracted_order} with alert {updated_data['Alert']}")
                    self.cancel(extracted_order)
            self.orderid.clear()
            print(f"CHECKING orderid {self.orderid}, datastatus = {self.datastatus}, position = {self.position}")
            print("=============================================")

        # if self.datastatus and not self.position and make sure order is
        if self.datastatus:
            if not self.p.usebracket:
                print('USING WITHOUT BRACKET')
                if updated_data["Alert"] == "SUPER_BUY":
                    # price = round(self.data0.close[0] * 0.90, 2)
                    price = self.data0.close[0]
                    print(f"BUY ACTION on price {price}")
                    self.order = self.buy(size=self.p.stake,
                                          exectype=self.p.exectype,
                                          price=price,
                                          valid=self.p.valid)
                elif updated_data["Alert"] == "SUPER_SELL":
                    # price = round(self.data0.close[0] * 1.10, 4)
                    price = self.data0.close[0]
                    print(f"SELL ACTION on price {price}")
                    self.order = self.sell(size=self.p.stake,
                                           exectype=self.p.exectype,
                                           price=price,
                                           valid=self.p.valid)

            else:
                if updated_data["Alert"] == "SUPER_BUY":
                    
                    price = self.data0.close[0]
                    stopprice=price - 10.00
                    limitprice=price + 10.00
                    print(f'USING BUY BRACKET with price {price}, stopprice {stopprice}, limit price {limitprice}')
                    self.order, _, _ = self.buy_bracket(size=self.p.stake,
                                                        exectype=bt.Order.Market,
                                                        price=price,
                                                        stopprice=stopprice,
                                                        limitprice=limitprice,
                                                        valid=self.p.valid)
                elif updated_data["Alert"] == "SUPER_SELL":
                    price = self.data0.close[0]
                    stopprice=price + 10.00
                    limitprice=price - 10.00
                    print(f'USING SELL BRACKET with price {price}, stopprice {stopprice}, limit price {limitprice}')
                    self.order, _, _ = self.sell_bracket(size=self.p.stake,
                                                        exectype=bt.Order.Market,
                                                        price=price,
                                                        stopprice=stopprice,
                                                        limitprice=limitprice,
                                                        valid=self.p.valid)

            self.orderid.append(self.order)
        # elif self.position and not self.p.donotcounter:
        #     if self.order is None:
        #         if updated_data["Alert"] == "SUPER_SELL":
        #             print(f"SELL with POSITION at price {self.data0.close[0]}")
        #             self.order = self.sell(size=self.p.stake // 2,
        #                                    exectype=bt.Order.Market,
        #                                    price=self.data0.close[0])
        #         elif updated_data["Alert"] == "SUPER_BUY":
        #             print(f"BUY with POSITION at price {self.data0.close[0]}")
        #             self.order = self.buy(size=self.p.stake // 2,
        #                                   exectype=bt.Order.Market,
        #                                   price=self.data0.close[0])

        #     self.orderid.append(self.order)

        

        if self.datastatus:
            self.datastatus += 1
    def notify_store(self, msg, *args, **kwargs):
        print('*' * 5, 'STORE NOTIF notify_store:', msg)

    def notify_order(self, order):
        if order.status in [order.Completed, order.Submitted, order.Partial, order.Expired, order.Margin, order.Cancelled, order.Rejected]:
            self.order = None

        print('-' * 50, 'ORDER BEGIN notify_order', datetime.now())
        print(order)
        print('-' * 50, 'ORDER END')

    def notify_trade(self, trade):
        print('-' * 50, 'TRADE BEGIN notify_trade', datetime.now())
        print(trade)
        print(f"trade_data == {trade.data.__dict__}")
        # pprint(vars(trade.data))
        print('-' * 50, 'TRADE END')

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = f'Data Status: {data._getstatusname(status)}'
        print(str(dt) + dn + msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
            self.datastatus = 1
        else:
            self.live_data = False

def main():
    # run flash server
    thread = StoppableThread(target=api_server_start, args=(API_PORT, API_REV))
    thread.start()
    thread.join()   

    host = "localhost"
    store = MTraderStore(host=host, debug=False, datatimeout=10)

    # comment next 2 lines to use backbroker for backtesting with MTraderStore
    cerebro = bt.Cerebro()
    
    cerebro.addstrategy(SmaCross)

    broker = store.getbroker(use_positions=True)
    cerebro.setbroker(broker)

    start_date = datetime.now() - timedelta(minutes=2)

    data = store.getdata(
        dataname="BTCUSD", 
        timeframe=bt.TimeFrame.Minutes,
        compression=1,
        fromdate=start_date, 
        # historical=True,
        # useask=True,
    )
    
    # cerebro.resampledata(data,
    #                  timeframe=bt.TimeFrame.Minutes,
    #                  compression=5
    #                  )

    # data = store.getdata(dataname="XAUUSD.c", timeframe=bt.TimeFrame.Ticks, fromdate=start_date) #, useask=True, historical=True)
    #                 the parameter "useask" will request the ask price insetad if the default bid price

    cerebro.adddata(data)
    # cerebro.adddata(data2)

    cerebro.run(stdstats=False)
    # cerebro.plot(style='candlestick', volume=False)

if __name__ == "__main__":
    main()