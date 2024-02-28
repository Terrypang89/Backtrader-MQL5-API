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
    def get_timestamp(self):
        timestamp = time.strftime("%Y-%m-%d %X")
        return timestamp

    def process_data_received(self, data:dict):
        log.info(f"on_data_received data = {data}\n")
        if not isinstance(data, dict):
            log.info(f"Incorrect data({data}) format received, SKIP.")
            return None
        try:
            # check if data ticker is 5m, 30m, 1 day
            self._new_data_received = True
            self._api_data = data
            
            if data["Period"] == "1":
                self._new_data_received_1m = True
                self._api_data_1m = data
                log.info(f"Detected new data {data['Symbol']} - {data['Period']}\n")
            elif data["Period"] == "5":
                self._new_data_received_5m = True
                self._api_data_5m = data
                log.info(f"Detected new data {data['Symbol']} - {data['Period']}\n")
            elif data["Period"] == "15":
                self._new_data_received_15m = True
                self._api_data_15m = data
                log.info(f"Detected new data {data['Symbol']} - {data['Period']}\n")
            elif data["Period"] == "30":
                self._new_data_received_30m = True
                self._api_data_30m = data
                log.info(f"Detected new data {data['Symbol']} - {data['Period']}\n")
            elif data["Period"] == "60":
                self._new_data_received_1h = True
                self._api_data_1h = data
                log.info(f"Detected new data {data['Symbol']} - {data['Period']}\n")
            if data["Period"] == "D":
                self._new_data_received_1d = True
                self._api_data_1d = data
                log.info(f"Detected new data {data['Symbol']} - {data['Period']}\n")
            # return data
        except Exception as err:
            log.error(f"Sent webhook failed, reason: {err}")
        
    def retrieve_data_received(self):
        if self._new_data_received_5m is True:
            self._new_data_received_5m = False
            return self._api_data_5m
        # elif 
        return None

    def __init__(self):
        self._new_data_received = False
        self._api_data = ""
        # self._prev_api_data = ""
        event_subscribe(API_REV, self.process_data_received)
    
        self.buy_order = []
        self.sell_order = []
        self.live_data = False
        self.buy_one = False
        self.sell_one = False

        # self.bb_param = (('period', 20), ('devfactor', 2.0), ('movav', "MODE_Simple"),)
        # self.bb = btind.BollingerBands(self.datas[0], period=20, devfactor=1.0, movav=btind.MovAv.Simple)
        # self.bb2 = btind.BollingerBands(self.datas[0], period=20, devfactor=2.0, movav=btind.MovAv.Simple)
        # self.stoch = btind.Stochastic()
        # self.sma = btind.MovingAverageSimple(self.datas[0])
        # self.stoch = btind.Stochastic(self.data[0], period=14, period_dfast=3, movav=btind.MovAv.Simple, upperband=80, lowerband=20.0, safediv=False, safezero=0.0)
        # self.stoch = btind.Stochastic(period=14, period_dfast=3, period_dslow=3, movav=btind.MovAv.Simple, upperband=80, lowerband=20.0, safediv=False, safezero=0.0)
        # self.rsi = btind.RSI()


        def addChart(chart, bb, bb2, stoch):
            indi0 = ChartIndicator(idx=0, shortname="Bollinger Bands")
            indi0.addline(
                bb.top,
                style={
                    "linelabel": "Top",
                    "color": "clrBlue",
                },
            )
            indi0.addline(
                bb.mid,
                style={
                    "linelabel": "Middle",
                    "color": "clrYellow",
                },
            )
            indi0.addline(
                bb.bot,
                style={
                    "linelabel": "Bottom",
                    "color": "clrBlue",
                },
            )

            chart.addchartindicator(indi0)
            indi1 = ChartIndicator(idx=1, shortname="stochastic oscillator")
            indi1.addline(
                stoch.percK,
                style={
                    "linelabel": "k",
                    "color": "clrYellow",
                },
            )

            indi1.addline(
                stoch.percD,
                style={
                    "linelabel": "D",
                    "color": "clrBlue",
                },
            )

            chart.addchartindicator(indi1)
            indi2 = ChartIndicator(idx=0, shortname="Bollinger Bands 2")

            indi2.addline(
                bb2.top,
                style={
                    "linelabel": "Top",
                    "color": "clrRed",
                },
            )
            indi2.addline(
                bb2.mid,
                style={
                    "linelabel": "Middle",
                    "color": "clrYellow",
                },
            )
            indi2.addline(
                bb2.bot,
                style={
                    "linelabel": "Bottom",
                    "color": "clrRed",
                },
            )

            chart.addchartindicator(indi2)

        # Instantiate a new chart window and plot
        # chart = MTraderChart(self.datas[0], realtime=True)
        # addChart(chart, self.bb, self.bb2, self.stoch)


    def next(self):

        updated_data = self.retrieve_data_received()
        # extract the data, check is there any opentrade, check buy/sell if yes, 

        log.info(f"UPDATED data = {updated_data}")
        if self.live_data:
            cash = self.broker.getcash()
        else:
            cash = "NA"
        
        if self.live_data == True:
            if updated_data == True:
                if updated_data["Type"] == "entry":
                    if updated_data["order"] == "long":
                        if self.buy_order is None:
                            self.buy_order = self.buy_bracket(limitprice=1916.13, stopprice=1915.10, size=0.01, exectype=bt.Order.Market)

                    if updated_data["order"] == "short":
                        if self.sell_order is None:
                            self.sell_order = self.sell_bracket(limitprice=1916.13, stopprice=1915.10, size=0.01, exectype=bt.Order.Market)
                if updated_data["Type"] == "exit":
                    if self.buy_order is not None:
                        if updated_data["order"] == "short":
                            self.cancel(self.buy_order[0])
                    elif self.sell_order is not None:
                        if updated_data["order"] == "long":
                            self.cancel(self.sell_order[0])
                print(f"data from api = {updated_data} \n")
            
            cur_close = self.datas[0].close[0]
            cur_open = self.datas[0].open[0]
            limit_buy = cur_open + 1
            stop_buy = cur_open - 2
            limit_sell = cur_close -1
            stop_sell = cur_close + 2
            log.info(f"detect live, cur_close= {cur_close}, cur_open = {cur_open}, limit_buy={limit_buy}, stop_buy={stop_buy}\n")
              
        else:
            cash = 'NA'

        for data in self.datas:
            str_data = str(vars(data))
            json_data = json.dumps(str_data, indent=12)
            log.info(f'id:{data._id} | tf:{data._timeframe} | com:{data._compression} | {data.datetime.datetime() - timedelta(hours=8)} - {data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]}')

    def notify_store(self, msg, *args, **kwargs):
        log.info('*' * 5, 'STORE NOTIF notify_store:', msg)

    def notify_order(self, order):
        if order.status in [order.Completed, order.Cancelled, order.Rejected]:
            self.order = None

        log.info('-' * 50, 'ORDER BEGIN notify_order', datetime.now())
        log.info(order)
        log.info('-' * 50, 'ORDER END')

    def notify_trade(self, trade):
        log.info('-' * 50, 'TRADE BEGIN notify_trade', datetime.now())
        log.info(trade)
        log.info('-' * 50, 'TRADE END')

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = f'Data Status: {data._getstatusname(status)}'
        log.info(str(dt) + dn + msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

def main():
    # run flash server
    thread = StoppableThread(target=api_server_start, args=(API_PORT, API_REV))
    thread.start()
    thread.join()   

    host = "localhost"
    store = MTraderStore(host=host, debug=True, datatimeout=10)

    # comment next 2 lines to use backbroker for backtesting with MTraderStore
    cerebro = bt.Cerebro()
    
    cerebro.addstrategy(SmaCross)

    broker = store.getbroker(use_positions=True)
    cerebro.setbroker(broker)

    start_date = datetime.now() - timedelta(minutes=2)

    data = store.getdata(
        dataname="BTCUSD", 
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
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