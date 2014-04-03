# -*- coding: utf-8 -*-
import curses
import time
import locale

locale.setlocale(locale.LC_ALL, "")


class Window(object):
    def __init__(self, screen):
        self.screen = screen
        self.screen.border(0)
        self.screen.nodelay(1)
        self.y, self.x = self.screen.getmaxyx()
        self.lines = []

    def footer(self):
        box = curses.newwin(3, self.x, self.y - 3, 0)
        box.immedok(True)
        box.box()
        box.addstr(1, 1, 'Q to Exit / R to refresh / C to clear screen')
        self.screen.refresh()

    def sidebar(self, user, money, size, market, start, current, delta, profit):
        box = curses.newwin(self.y, 40, 0, self.x - 40)
        box.immedok(True)
        box.box()
        box.addstr(1, 1, user)
        box.addstr(2, 1, 'Balance: %s' % money)
        box.addstr(3, 1, 'Profit: %s' % str(money - profit))
        box.addstr(4, 1, 'Bet size: %s' % size)
        box.addstr(5, 1, 'Race: %s' % market)
        box.addstr(6, 1, 'Start: %s' % start)
        box.addstr(7, 1, 'Current time: %s' % current)
        box.addstr(8, 1, 'Delta: %s' % delta)
        self.screen.refresh()

    def content(self, msg):
        pad = curses.newpad(100, self.x - 40)
        self.lines.append('%s' % msg.encode('utf-8'))

        if len(self.lines) > 26:
            self.lines = self.lines[-26:len(self.lines)]

        for i, k in enumerate(self.lines):
            pad.addstr(i, 0, str(k))

        pad.refresh(0, 0, 1, 1, 26, 162)
        self.screen.refresh()

    def clear_content(self):
        pad = curses.newpad(100, self.x - 40)
        self.lines = []
        pad.refresh(0, 0, 1, 1, 26, 162)
        self.screen.refresh()
