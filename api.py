# -*- coding: utf-8 -*-
import urllib
import urllib2
import datetime
import json
import re
from dateutil import tz

#curl -v -c cookies.txt -d "username=Username&password=password&login=true&redirectMethod=POST&product=home.betfair.int&url=https://www.betfair.com/" https://identitysso.betfair.com/api/login >out.txt 2>&1
#https://api-ng.betstores.com/account/

APP_KEY = 'kIaoqDlc9U16k17x'


class BfApi(object):
    appKey = APP_KEY
    req = {'jsonrpc': '2.0'}
    headers = {'X-Application': appKey, 'content-type': 'application/json'}

    betting_url = 'https://api.betfair.com/exchange/betting/json-rpc/v1'
    account_url = 'https://api.betfair.com/exchange/account/json-rpc/v1'

    def callAping(self, jsonrpc_req, url, headers):
        try:
            req = urllib2.Request(url, json.dumps(jsonrpc_req, ensure_ascii=False), headers)
            response = urllib2.urlopen(req)
            jsonResponse = response.read()
            return jsonResponse
        except urllib2.URLError, e:
            print e
            return 'Oops no service available at ' + str(url)
        except urllib2.HTTPError:
            return 'Oops not a valid operation from the service ' + str(url)

    def keep_alive(self, sessionToken):
        url = 'https://identitysso.betfair.com/api/keepAlive'
        headers = self.headers.copy()
        headers['Accept'] = 'application/json'
        headers['X-Authentication'] = sessionToken

        eventTypesResponse = self.callAping('', url, headers)
        eventTypeLoads = json.loads(eventTypesResponse)

        return eventTypeLoads

    def login(self, username, password):
        url = 'https://identitysso.betfair.com/api/login'
        data = {}
        data['username'] = str(username)
        data['password'] = str(password)
        data['login'] = 'true'
        data['redirectMethod'] = 'POST'
        data['product'] = 'home.betfair.int'
        data['url'] = 'https://www.betfair.com/'

        data = urllib.urlencode(data)
        request = urllib2.Request(url, data)
        resp = urllib2.urlopen(request)

        try:
            sessionToken = re.findall(r'ssoid=(.*?);', str(resp.headers))[0]
            return sessionToken
        except IndexError:
            return False

    def logout(self, sessionToken):
        url = 'https://identitysso.betfair.com/api/logout'
        headers = self.headers.copy()
        headers['Accept'] = 'application/json'
        headers['X-Authentication'] = sessionToken
        return self.callAping('', url, headers)

    def get_event_types(self, sessionToken):
        request = self.req.copy()
        request['method'] = 'SportsAPING/v1.0/listEventTypes'
        request['params'] = {"filter": {}}
        request['id'] = 1

        headers = self.headers.copy()
        headers['X-Authentication'] = sessionToken

        eventTypesResponse = self.callAping(request, self.betting_url, headers)
        eventTypeLoads = json.loads(eventTypesResponse)

        try:
            return eventTypeLoads['result']
        except:
            return 'Exception from API-NG' + str(eventTypeLoads['error'])

    def get_account_details(self, sessionToken):
        request = self.req.copy()
        request['method'] = 'AccountAPING/v1.0/getAccountDetails'

        headers = self.headers.copy()
        headers['X-Authentication'] = sessionToken

        return self.callAping(request, self.account_url, headers)

    def get_account_funds(self, sessionToken):
        request = self.req.copy()
        request['method'] = 'AccountAPING/v1.0/getAccountFunds'

        headers = self.headers.copy()
        headers['X-Authentication'] = sessionToken

        return self.callAping(request, self.account_url, headers)

    def getMarketCatalouge(self, sessionToken, eventTypeID):
        country = 'GB'  # FIXME: должно быть динамически
        now = datetime.datetime.utcnow().replace(tzinfo=tz.gettz(country))
        now = now.strftime('%Y-%m-%dT%H:%M:%SZ')

        request = self.req.copy()
        request['method'] = 'SportsAPING/v1.0/listMarketCatalogue'
        request['params'] = {'filter': {'eventTypeIds': [str(eventTypeID)],
                                        'marketCountries': [country],
                                        'marketTypeCodes': ['WIN'],
                                        'marketStartTime': {'from': str(now)},
                                        'inPlayOnly': 'false'},
                             'sort': 'FIRST_TO_START',
                             'maxResults': '1',
                             'marketProjection': ['EVENT', 'MARKET_START_TIME',
                                                  'RUNNER_METADATA']}
        request['id'] = 1

        headers = self.headers.copy()
        headers['X-Authentication'] = sessionToken

        market_catalogue_response = self.callAping(request, self.betting_url, headers)
        market_catalouge_loads = json.loads(market_catalogue_response)

        try:
            market_catalouge_results = market_catalouge_loads['result']
            return market_catalouge_results
        except:
            return 'Exception from API-NG' + str(market_catalouge_results['error'])

    def getMarketId(self, marketCatalougeResult):
        for market in marketCatalougeResult:
            return market['marketId']

    def getMarketName(self, marketCatalougeResult):
        for market in marketCatalougeResult:
            return market['marketName']

    def getSelectionId(self, marketCatalougeResult):
        for market in marketCatalougeResult:
            return market['runners'][0]['selectionId']

    def getMarketStartTime(self, marketCatalougeResult):
        for market in marketCatalougeResult:
            return market['marketStartTime']

    def getMarketBook(self, sessionToken, marketId):
        request = self.req.copy()
        request['method'] = 'SportsAPING/v1.0/listMarketBook'
        request['params'] = {'marketIds': [str(marketId)], 'priceProjection': {'priceData': ['EX_BEST_OFFERS']}}
        request['id'] = 1

        headers = self.headers.copy()
        headers['X-Authentication'] = sessionToken

        eventTypesResponse = self.callAping(request, self.betting_url, headers)
        eventTypeLoads = json.loads(eventTypesResponse)

        try:
            return eventTypeLoads['result']
        except:
            return 'Exception from API-NG' + str(eventTypeLoads['error'])

    def printPriceInfo(self, market_book_result):
        for marketBook in market_book_result:
            runners = marketBook['runners']
            result = []
            for runner in runners:
                res = {}
                if runner['status'] == 'ACTIVE':
                    res['back'] = runner['ex']['availableToBack']
                    res['lay'] = runner['ex']['availableToLay']
                    res['SelectionId'] = runner['selectionId']
                    result.append(res)
            return result

    def getCurrentOrder(self, sessionToken, marketId=False, betId=False):
        request = self.req.copy()
        request['method'] = 'SportsAPING/v1.0/listCurrentOrders'
        request['params'] = {'recordCount': 1}
        if marketId:
            request['params']['marketIds'] = [str(marketId)]
        if betId:
            request['params']['betId'] = [str(betId)]

        headers = self.headers.copy()
        headers['X-Authentication'] = sessionToken

        eventTypesResponse = self.callAping(request, self.betting_url, headers)
        eventTypeLoads = json.loads(eventTypesResponse)

        return eventTypeLoads['result']['currentOrders']

    def placeOrders(self, sessionToken, marketId, selectionId, side, size, price):
        request = self.req.copy()
        request['method'] = 'SportsAPING/v1.0/placeOrders'
        request['params'] = {"marketId": str(marketId),
                             "instructions": [{"selectionId": str(selectionId),
                                               "handicap": "0",
                                               "side": side,
                                               "orderType": "LIMIT",
                                               "limitOrder": {"size": str(size),
                                                              "price": str(price),
                                                              "persistenceType": "PERSIST"}}]}
        request['id'] = 1

        headers = self.headers.copy()
        headers['X-Authentication'] = sessionToken

        eventTypesResponse = self.callAping(request, self.betting_url, headers)
        eventTypeLoads = json.loads(eventTypesResponse)

        return eventTypeLoads
