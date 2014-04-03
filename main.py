# -*- coding: utf-8 -*-
from api import BfApi
from tui import Window

import sys
import json
from datetime import datetime, timedelta
from dateutil.parser import parse
from dateutil import tz
import re
import getpass
import time
import threading
import curses


class Main(object):
    def __init__(self, screen, stdscr):
        self.screen = screen
        self.stdscr = stdscr
        self.sessionToken = False
        self.size = False
        self.start_balance = 0

    def to_dict(self, func):
        '''
        Ковертирует json в dict
        '''
        return json.loads(func)

    def date_convert(self, date, timezone):
        '''
        Смена времени по указаному часовому поясу
        '''
        GMT = tz.gettz(timezone)
        d = parse(date)
        return d.astimezone(GMT).strftime('%Y-%m-%d %H:%M:%S')

    def get_ratio(self, ratio, tic):
        '''
        Повышает коэффициент на указанный тик

        Тик – это шаг изменения коэффициента в том или ином диапазоне.
        В диапазоне от 1.01 до 2-х шаг изменения коэффициента 0.01,
        от 2-х до 3-х – 0.02, от 3-х до 4-х – 0.05 и так далее.
        '''
        result = ratio
        for x in xrange(tic):
            if ratio < 2:
                result += 0.01
            if ratio >= 2 and ratio < 3:
                result += 0.02
            if ratio >= 3 and ratio < 4:
                result += 0.05
            if ratio >= 4 and ratio < 6:
                result += 0.1
            if ratio >= 6 and ratio < 10:
                result += 0.2
            if ratio >= 10 and ratio < 20:
                result += 0.5
            if ratio >= 20 and ratio < 30:
                result += 1
            if ratio >= 30 and ratio < 50:
                result += 2
            if ratio >= 50 and ratio < 100:
                result += 5
            if ratio >= 100 and ratio < 1000:
                result += 10

        return result

    def user(self, account):
        '''
        Выводим имя и фамилию пользователя
        '''
        return '%s %s' % (account['firstName'], account['lastName'])

    def money(self):
        '''
        Доступный баланс пользователя
        '''
        account_funds = self.to_dict(BfApi().get_account_funds(self.sessionToken))['result']
        return account_funds['availableToBetBalance']

    def now(self):
        '''
        Текущее время
        '''
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def account_detail(self):
        '''
        Информация аккаунта (имя, фамилия, часовой пояс...)
        '''
        return self.to_dict((BfApi().get_account_details(self.sessionToken)))['result']

    def active_runners(self, market_book_result):
        '''
        Нужное или нет кол-во жокеев в забеге
        '''
        if market_book_result[0]['numberOfActiveRunners'] > 4:
            return True
        return False

    def market_name(self, marketCatalougeResult):
        '''
        Название забега
        '''
        marketName = BfApi().getMarketName(marketCatalougeResult)
        return marketName

    def market_status(self, market_book_result):
        '''
        Проверяем или забег открыт и ещё не в инплее
        '''
        if market_book_result[0]['status'] == 'OPEN' and not market_book_result[0]['inplay']:
            return True
        return False

    def current_order(self, marketid):
        '''
        Проверяем или у нас ещё нет ставок в текущем рынке
        '''
        if not BfApi().getCurrentOrder(self.sessionToken, marketid):
            return True
        return False

    def get_distance(self, marketName):
        '''
        Получаем дистанцию забега из названия
        '''
        try:
            distance = re.findall("[0-9][0-9mf]+", marketName)[0]
            if 'm' in distance:
                return float(distance.replace('m', '.').replace('f', ''))
        except IndexError:
            pass
        return 0

    def get_start_time(self, marketCatalougeResult, account):
        '''
        Время начала забега
        '''
        start = self.date_convert(BfApi().getMarketStartTime(marketCatalougeResult),
                                  account['timezone'])
        return start

    def market_book_result(self, marketid):
        '''
        Информация по предстоящей скачке
        '''
        market_book_result = BfApi().getMarketBook(self.sessionToken, marketid)
        self.screen.content(u'Кол-во жокеев: %s' % market_book_result[0]['numberOfActiveRunners'])
        return market_book_result

    def lay_order(self, favorite, marketid):
        '''
        Делаем ставку ПРОТИВ фаворита
        '''
        if (favorite[1]['lay'][0]['price'] * 5 - 5) < self.money():
            selectionId = favorite[1]['SelectionId']
            side = 'LAY'
            price = favorite[1]['lay'][0]['price']
            res = BfApi().placeOrders(self.sessionToken, marketid,
                                      selectionId, side, self.size, price)

            self.screen.content(u'Ставка ПРОТИВ сумма %s коэффициент %s' % (self.size, price))

            if res['result']['status'] == 'FAILURE':
                self.screen.content(u'Не удалось поставить ПРОТИВ')
                return False

            data = res['result']['instructionReports'][0]['averagePriceMatched']

            while float(data) < 1.01:
                betId = res['result']['instructionReports'][0]['betId']
                current = BfApi().getCurrentOrder(self.sessionToken, betId=betId)
                data = current[0]['priceSize']['price']
            return data
        else:
            self.screen.content(u'Недостаточно денег для обязательства')
            return False

    def back_order(self, favorite, marketid, price):
        '''
        Делаем ставку ЗА с коэффициентом выше на 4 тика
        '''
        first_price = price
        second_price = self.get_ratio(price, 4)

        selectionId = favorite[1]['SelectionId']
        side = 'BACK'
        size = '%0.2f' % float(self.size * first_price / second_price)
        if size < 4:
            size = 4

        res = BfApi().placeOrders(self.sessionToken, marketid,
                                  selectionId, side, size, second_price)

        self.screen.content(u'Ставка ЗА сумма %s коэффициент %s' % (size, second_price))
        while res['result']['status'] == 'FAILURE':
            self.screen.content(u'Не удалось поставить ЗА')
            res = BfApi().placeOrders(self.sessionToken, marketid,
                                      selectionId, side, size, second_price)

        return res['result']['instructionReports'][0]['averagePriceMatched']

    def main(self):
        marketCatalougeResult = BfApi().getMarketCatalouge(self.sessionToken, 7)
        self.screen.content(self.market_name(marketCatalougeResult))

        marketid = BfApi().getMarketId(marketCatalougeResult)
        market_book_result = self.market_book_result(marketid)

        if self.active_runners(market_book_result):
            if self.market_status(market_book_result):
                if self.current_order(marketid):
                    runners = {}

                    for runner in BfApi().printPriceInfo(market_book_result):
                        runners[runner['back'][0]['price']] = runner

                    runners = sorted(runners.items())[:2]

                    if (runners[1][0] - runners[0][0]) < 3:

                        if self.get_distance(self.market_name(marketCatalougeResult)) > 1.5:

                            if runners[0][0] < 4:

                                price = self.lay_order(runners[0], marketid)
                                if price:
                                    self.back_order(runners[0], marketid, price)
                            else:
                                self.screen.content(u'Коэффициент фаворита превышает допущенный')
                        else:
                            self.screen.content(u'Дистанция забега слишком мала')
                    else:
                        self.screen.content(u'Слишком большой интервал между фаворитом и преследователем')
                else:
                    self.screen.content(u'Ставка на этом рынке уже была произведена')
            else:
                self.screen.content(u'Рынок закрыт или в инплее')
        else:
            self.screen.content(u'На этом рынке слишком мало жокеев')

    def start(self):
        self.screen.footer()
        account_detail = self.account_detail()
        self.start_balance = self.money()

        while True:
            user = self.user(account_detail)
            money = self.money()

            marketCatalougeResult = BfApi().getMarketCatalouge(self.sessionToken, 7)
            market = self.market_name(marketCatalougeResult)

            start = self.get_start_time(marketCatalougeResult, account_detail)

            while (parse(start) - parse(self.now())) > timedelta(seconds=2):
                time.sleep(1)
                delta = parse(start) - parse(self.now())
                self.screen.sidebar(user, money, self.size, market, start,
                                    self.now(), delta, self.start_balance)

            self.main()
            time.sleep(10)

    def live(self):
        th = threading.Thread(target=self.start)
        th.daemon = True
        th.start()

        while True:
            c = self.stdscr.getch()
            if c == ord('r'):
                return 'restart'
            elif c == ord('c'):
                self.screen.clear_content()
            elif c == ord('q'):
                self.screen.content('Quit')
                return 'quit'
            time.sleep(0.1)


def keep_alive(sessionToken):
    response = BfApi().keep_alive(sessionToken)
    if response['status'] == 'FAIL':
        print response['error']
        sys.exit(0)


def logout(sessionToken, t, curses, stdscr):
    BfApi().logout(sessionToken)
    t.cancel()
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()


if __name__ == '__main__':
    username = raw_input('Username: ')
    password = getpass.getpass('Password: ')
    size = float(raw_input('Bet Size: '))

    sessionToken = BfApi().login(username, password)
    if not sessionToken:
        print 'Login incorrect'
        sys.exit(0)

    try:
        t = threading.Timer(1080.0, keep_alive, args=(sessionToken,))
        t.start()

        stdscr = curses.initscr()
        curses.curs_set(0)
        curses.noecho()
        screen = Window(stdscr)
        stdscr.refresh()

        var = Main(screen, stdscr)
        var.sessionToken = sessionToken
        var.size = size

        while True:
            if var.live() == 'restart':
                var.live()
            else:
                break

        logout(sessionToken, t, curses, stdscr)

    except KeyboardInterrupt:
        logout(sessionToken, t, curses, stdscr)
