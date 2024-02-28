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
    
    def data_info_print(self):
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
        txt.append('prev close {:f}'.format(self.data.close[-1]))


        print(', '.join(txt))
    
    def ind_info_print(self):
        ind_txt = list()
        ind_txt.append('BB1_TOP = {:f}'.format(self.bb1.top[0]))
        ind_txt.append('BB1_BOT = {:f}'.format(self.bb1.bot[0]))
        ind_txt.append('BB1_MID = {:f}'.format(self.bb1.mid[0]))
        ind_txt.append('BB2_TOP = {:f}'.format(self.bb2.top[0]))
        ind_txt.append('BB2_BOT = {:f}'.format(self.bb2.bot[0]))
        ind_txt.append('BB2_MID = {:f}'.format(self.bb2.mid[0]))
        ind_txt.append('BB3_TOP = {:f}'.format(self.bb3.top[0]))
        ind_txt.append('BB3_BOT = {:f}'.format(self.bb3.bot[0]))
        ind_txt.append('BB3_MID = {:f}'.format(self.bb3.mid[0]))

        ind_txt.append('MFI = {:f}'.format(self.mt5mfi.MFI[0]))
        ind_txt.append('rsi = {:f}'.format(self.rsi.rsi[0]))
        
        ind_txt.append('STOCH_MAIN = {:f}'.format(self.mt5stoch.Main[0]))
        ind_txt.append('STOCH_SIGNAL = {:f}'.format(self.mt5stoch.Signal[0]))

        ind_txt.append('MACD = {:f}'.format(self.macd.macd[0]))
        ind_txt.append('MACD_SIGNAL = {:f}'.format(self.macd.signal[0]))
        ind_txt.append('MACD_HISTO = {:f}'.format(self.macd.histo[0]))
        
        ind_txt.append('mt5triema = {:f}'.format(self.mt5triema.TEMA[0]))
        print(', '.join(ind_txt))
    
    def indicator_preset(self, store):

        self.mt5triema = getMTraderIndicator(
            store,
            self.datas[0],
            ("TEMA",),
            indicator="Examples/TEMA",
            params=[3, 0,],
        )()

        self.mt5mfi = getMTraderIndicator(
            store,
            self.datas[0],
            ("MFI",),
            indicator="Examples/MFI",
            params=[7],
        )()

        self.mt5rsi = getMTraderIndicator(
            store,
            self.datas[0],
            ("RSI",),
            indicator="Examples/RSI",
            params=[7,],
        )()

        self.mt5stoch = getMTraderIndicator(
            store,
            self.datas[0],
            ("Main","Signal",),
            indicator="Examples/Stochastic",
            params=[5, 3, 1],
        )()

        self.bb1 = btind.BollingerBands(self.datas[0], period=20, devfactor=1.0, movav=btind.MovAv.Simple)
        self.bb2 = btind.BollingerBands(self.datas[0], period=20, devfactor=2.0, movav=btind.MovAv.Simple)
        self.bb3 = btind.BollingerBands(self.datas[0], period=20, devfactor=3.0, movav=btind.MovAv.Simple)
        self.ema = btind.ExponentialMovingAverage(self.datas[0], period=5)
        self.macd = btind.MACDHisto(self.datas[0], period_me1=12, period_me2=26, period_signal=9, movav=btind.MovAv.Exponential)
        self.rsi = btind.RelativeStrengthIndex(self.datas[0], period=7, movav=btind.MovAv.Smoothed)

        def addChart(chart, ema, bb1, bb2, bb3, macd, rsi, mt5mfi, mt5stoch, mt5triema):

            ema_ind1 = ChartIndicator(idx=0, shortname="ema")
            ema_ind1.addline(
                ema.ema,
                style={
                    "linelabel": "EMA",
                    "color": "clrDarkViolet",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            chart.addchartindicator(ema_ind1)

            bb_indi1 = ChartIndicator(idx=0, shortname="Bollinger Bands")
            bb_indi2 = ChartIndicator(idx=0, shortname="Bollinger Bands")
            bb_indi3 = ChartIndicator(idx=0, shortname="Bollinger Bands")

            bb_indi1.addline(
                bb1.top,
                style={
                    "linelabel": "BB1_TOP",
                    "color": "clrBlue",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            bb_indi1.addline(
                bb1.mid,
                style={
                    "linelabel": "BB1_MID",
                    "color": "clrYellow",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            bb_indi1.addline(
                bb1.bot,
                style={
                    "linelabel": "BB1_BOT",
                    "color": "clrBlue",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )

            bb_indi2.addline(
                bb2.top,
                style={
                    "linelabel": "BB2_TOP",
                    "color": "clrCrimson",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            bb_indi2.addline(
                bb2.mid,
                style={
                    "linelabel": "BB2_MID",
                    "color": "clrDarkOrange",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            bb_indi2.addline(
                bb2.bot,
                style={
                    "linelabel": "BB2_BOT",
                    "color": "clrCrimson",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )

            bb_indi3.addline(
                bb3.top,
                style={
                    "linelabel": "BB3_TOP",
                    "color": "clrDarkGreen",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            bb_indi3.addline(
                bb3.mid,
                style={
                    "linelabel": "BB3_MID",
                    "color": "clrDarkOrange",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            bb_indi3.addline(
                bb3.bot,
                style={
                    "linelabel": "BB3_BOT",
                    "color": "clrDarkGreen",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )

            chart.addchartindicator(bb_indi1)
            chart.addchartindicator(bb_indi2)
            chart.addchartindicator(bb_indi3)

            mt5mfi_ind = ChartIndicator(idx=2, shortname="mt5mfi")
            mt5mfi_ind.addline(
                mt5mfi.MFI,
                style={"linelabel": "MFI", "color": "clrLightBlue", "linestyle": "STYLE_SOLID", "linewidth": 2},
            )
            chart.addchartindicator(mt5mfi_ind)

            rsi_ind = ChartIndicator(idx=2, shortname="RSI")
            rsi_ind.addline(
                rsi.rsi,
                style={"linelabel": "RSI", "color": "clrBlue", "linestyle": "STYLE_SOLID", "linewidth": 2},
            )
            chart.addchartindicator(rsi_ind)

            mt5stoch_ind = ChartIndicator(idx=3, shortname="mt5stoch")
            mt5stoch_ind.addline(
                mt5stoch.Main,
                style={
                    "linelabel": "STOCH_Main",
                    "color": "clrLightGreen",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            mt5stoch_ind.addline(
                mt5stoch.Signal,
                style={
                    "linelabel": "STOCH_Signal",
                    "color": "clrRed",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            chart.addchartindicator(mt5stoch_ind)

            macd1 = ChartIndicator(idx=4, shortname="Macd")
            macd1.addline(
                macd.macd,
                style={"linelabel": "MACD", "color": "clrBlue", "linestyle": "STYLE_SOLID", "linewidth": 2},
            )
            macd1.addline(
                macd.signal,
                style={"linelabel": "MACD_SIGNAL", "color": "clrRed", "linestyle": "STYLE_SOLID", "linewidth": 2},
            )
            macd1.addline(
                macd.histo,
                style={"linelabel": "MACD_HISTO", "color": "clrGreen", "linetype": "DRAW_HISTOGRAM", "linestyle":"STYLE_SOLID", "linewidth": 4},
            )
            chart.addchartindicator(macd1)

            mt5triema_ind = ChartIndicator(idx=0, shortname="mt5triema")
            mt5triema_ind.addline(
                mt5triema.TEMA,
                style={
                    "linelabel": "TEMA",
                    "color": "clrLightGreen",
                    "linestyle": "STYLE_SOLID",
                    "linewidth": 2
                },
            )
            chart.addchartindicator(mt5triema_ind)

        # Instantiate a new chart window and plot
        chart = MTraderChart(self.datas[0], realtime=False)
        addChart(chart, self.ema, self.bb1, self.bb2, self.bb3, self.macd, self.rsi, self.mt5mfi, self.mt5stoch, self.mt5triema)
        
    def cond1_trend_volatility(self):
        return None

    def cond2_momentum(self):
        return None
    
    def entry_with_no_trades(self):
        return None
    
    def entry_with_buy_sell_trades(self):
        return None
    
    def exit_buy_sell_trades(self):
        return None
    
    def __init__(self, store):

        self.orderid = 0
        self.orders = None
        self.live_data = None

        self.counttostop = 0
        self.datastatus = 0

        self._new_data_received = False
        self._api_data = ""

        self.buy_orders = list()
        self.sell_orders = list()
        
        self.cur_trade = None
        self.prev_trade = None
        self.cur_trend = None
        self.prev_trade = None
        self.trade_cond = None

        event_subscribe(API_REV, self.process_data_received)

        self.indicator_preset(store)

    def next(self):

        # data and indicator printing
        self.data_info_print()
        self.ind_info_print()

        if not self.p.trade:
            return
        
        if not self.live_data:
            return

        updated_data = self.retrieve_data_received()
        if updated_data is None:
            return
        
        print(f"UPDATED data = {updated_data}")
        print(f"PRECHECK datastatus = {self.datastatus}, position = {self.position}, orderid = {self.orderid}, order = {self.order}, usebracket = {self.p.usebracket}, donorcounter = {self.p.donotcounter}, valid = {self.p.valid}, stake = {self.p.stake}, exectype={self.p.exectype}")

        if self.trade_cond == "closed":
            if self.buy_orders is None and self.sell_orders is None:
                self.entry_with_no_trades()
            else:
                self.entry_with_buy_sell_trades()
            self.trade_cond = "open"

        elif self.trade_cond == "open":
            self.exit_buy_sell_trades()


        # checck if trade 
        # if self.orderid is not 0:
        #     for extracted_order in self.orderid:
        #         if updated_data["Alert"] == "SUPER_BUY" or updated_data["Alert"] == "SUPER_SELL":
        #             print(f"CANCELING order {extracted_order} with alert {updated_data['Alert']}")
        #             self.cancel(extracted_order)
        #     self.orderid.clear()
        #     print(f"CHECKING orderid {self.orderid}, datastatus = {self.datastatus}, position = {self.position}")
        #     print("=============================================")

        # # if self.datastatus and not self.position and len(self.orderid) < 1:
        # if self.datastatus and len(self.orderid) < 1:
        #     if not self.p.usebracket:
        #         print('USING WITHOUT BRACKET')
        #         if updated_data["Alert"] == "SUPER_BUY":
        #             # price = round(self.data0.close[0] * 0.90, 2)
        #             price = self.data0.close[0]
        #             print(f"BUY ACTION on price {price}")
        #             self.order = self.buy(size=self.p.stake,
        #                                   exectype=self.p.exectype,
        #                                   price=price,
        #                                   valid=self.p.valid)
        #         elif updated_data["Alert"] == "SUPER_SELL":
        #             # price = round(self.data0.close[0] * 1.10, 4)
        #             price = self.data0.close[0]
        #             print(f"SELL ACTION on price {price}")
        #             self.order = self.sell(size=self.p.stake,
        #                                    exectype=self.p.exectype,
        #                                    price=price,
        #                                    valid=self.p.valid)

        #     else:
        #         if updated_data["Alert"] == "SUPER_BUY":
                    
        #             price = self.data0.close[0]
        #             stopprice=price - 10.00
        #             limitprice=price + 10.00
        #             print(f'USING BUY BRACKET with price {price}, stopprice {stopprice}, limit price {limitprice}')
        #             self.order, _, _ = self.buy_bracket(size=self.p.stake,
        #                                                 exectype=bt.Order.Market,
        #                                                 price=price,
        #                                                 stopprice=stopprice,
        #                                                 limitprice=limitprice,
        #                                                 valid=self.p.valid)
        #         elif updated_data["Alert"] == "SUPER_SELL":
        #             price = self.data0.close[0]
        #             stopprice=price + 10.00
        #             limitprice=price - 10.00
        #             print(f'USING SELL BRACKET with price {price}, stopprice {stopprice}, limit price {limitprice}')
        #             self.order, _, _ = self.sell_bracket(size=self.p.stake,
        #                                                 exectype=bt.Order.Market,
        #                                                 price=price,
        #                                                 stopprice=stopprice,
        #                                                 limitprice=limitprice,
        #                                                 valid=self.p.valid)

        #     self.orderid.append(self.order)
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

        

        # if self.datastatus:
            # self.datastatus += 1


    def notify_store(self, msg, *args, **kwargs):
        print('*' * 5, 'STORE NOTIF notify_store:', msg)

    def notify_order(self, order):
        if order.status in [order.Completed, order.Cancelled, order.Rejected]:
            self.order = None

        print('-' * 50, 'ORDER BEGIN notify_order', datetime.now())
        print(order)
        print('-' * 50, 'ORDER END')

    def notify_trade(self, trade):
        print('-' * 50, 'TRADE BEGIN notify_trade', datetime.now())
        print(trade)
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
    
    cerebro.addstrategy(SmaCross, store)

    broker = store.getbroker(use_positions=True)
    cerebro.setbroker(broker)

    start_date = datetime.now() - timedelta(hours=60)

    data = store.getdata(
        dataname="XAUUSD.c", 
        timeframe=bt.TimeFrame.Minutes,
        compression=15,
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