import random, math, copy

from orders import FXOrder, CrossFXOrder, Side
from accounts import Accounts
from prices import getPrice, printPrices, convertTo, convertToMid
from convention import marketConvention

#random.seed(4)  EUR cancel out completely
random.seed(120)

#ACCOUNTS = [('Account A','USD'),('Account B','USD'),('Account C','USD'),('Account D','USD')]
#CURRENCIES = ['AUD','CAD','CHF','CNH', 'EUR','GBP','HKD','JPY','NZD','PLN','USD']

ACCOUNTS = [('Account A','USD'),('Account B','EUR'),('Account C','USD'),('Account D','USD'),('Account E','EUR')]
CURRENCIES = ['AUD','CAD','CHF','GBP','EUR','HKD','JPY','NZD','PLN','USD']


def initAccounts():
    accounts = Accounts(CURRENCIES)
    for accountName, accountCcy in ACCOUNTS: accounts.addAccount(accountName, accountCcy)

    for ccy in CURRENCIES:
        for accountName, accountCcy in ACCOUNTS:
            if ccy == accountCcy: continue
            r = random.randint(-5,5)
            if (r > 2): target_amount = roundup(convertToMid(ccy, accountCcy, 1000000*random.randint(1,10)))
            elif (r < -2): target_amount = roundup(convertToMid(ccy, accountCcy, -1000000*random.randint(1,10)))
            else: continue
            if target_amount == 0: continue

            account_base_amount = convertTo(accountCcy, ccy, target_amount)
            accounts.addAccountTarget(accountName, ccy, target_amount, account_base_amount)
    return accounts

def roundup(amount):
    return int(math.ceil(amount/1000000.0)) * 1000000

def sortedKeys(dict):
    keys = dict.keys()
    keys.sort()
    return keys

def getTotals(accounts):
    aggregatedOrders = {}
    nettedOrders = {}
    shadowOrders = {}

    #aggregate orders within account of the same base (add buy and sell side)
    for ccy in accounts.currencies:
        for name in accounts.getAccountNames():
            account = accounts.getAccount(name)

            if (not aggregatedOrders.has_key(account.getBase())): aggregatedOrders[account.getBase()] = {}
            pair, base, term = marketConvention(ccy, account.getBase())

            if account.getOrders().has_key(pair):
                order = account.getOrders()[pair]

                if False and account.getBase() == 'EUR' and pair != 'EURUSD':
                    cross = CrossFXOrder(order)
                    cross.split('USD')

                    if not aggregatedOrders[account.getBase()].has_key(cross.left.base+cross.left.term):
                        buy = FXOrder.newBuyOrder("Aggregated", cross.left.base, cross.left.term, ccy)
                        sell = FXOrder.newSellOrder("Aggregated", cross.left.base, cross.left.term, ccy)
                        aggregatedOrders[account.getBase()][cross.left.base+cross.left.term] = (buy, sell)

                    if not aggregatedOrders[account.getBase()].has_key(cross.right.base+cross.right.term):
                        buy = FXOrder.newBuyOrder("Aggregated", cross.right.base, cross.right.term, ccy)
                        sell = FXOrder.newSellOrder("Aggregated", cross.right.base, cross.right.term, ccy)
                        aggregatedOrders[account.getBase()][cross.right.base+cross.right.term] = (buy, sell)

                    if order.isBuy():aggregatedOrders[account.getBase()][cross.left.base+cross.left.term][0].aggregate(cross.left)
                    else: aggregatedOrders[account.getBase()][cross.left.base+cross.left.term][1].aggregate(cross.left)

                    if order.isBuy():aggregatedOrders[account.getBase()][cross.right.base+cross.right.term][0].aggregate(cross.right)
                    else: aggregatedOrders[account.getBase()][cross.right.base+cross.right.term][1].aggregate(cross.right)

                else:

                    if not aggregatedOrders[account.getBase()].has_key(pair):
                        buy = FXOrder.newBuyOrder("Aggregated", base, term, ccy)
                        sell = FXOrder.newSellOrder("Aggregated", base, term, ccy)
                        aggregatedOrders[account.getBase()][pair] = (buy, sell)

                    if order.isBuy():aggregatedOrders[account.getBase()][pair][0].aggregate(order)
                    else: aggregatedOrders[account.getBase()][pair][1].aggregate(order)

    #net aggregates within accounts of the same base (add the buy and sell)
    for base in sortedKeys(aggregatedOrders):
        nettedOrders[base] = {}

        for pair in sortedKeys(aggregatedOrders[base]):
            bid, ask = getPrice(pair)

            order = FXOrder()
            order.account = "Netted"
            order.base = aggregatedOrders[base][pair][0].base
            order.term = aggregatedOrders[base][pair][0].term
            order.dealtCurrency = aggregatedOrders[base][pair][0].dealtCurrency

            buyAmount = aggregatedOrders[base][pair][0].dealtAmount
            sellAmount = aggregatedOrders[base][pair][1].dealtAmount

            if (buyAmount >= sellAmount):
                order.side = Side.BUY
                order.setAmounts(aggregatedOrders[base][pair][0].dealtAmount - aggregatedOrders[base][pair][1].dealtAmount)
                dealtSaved = aggregatedOrders[base][pair][1].dealtAmount
                if order.dealtCurrency == order.base:
                    order.setSaving(dealtSaved*ask - dealtSaved*bid)
                else:
                    order.setSaving(dealtSaved/bid - dealtSaved/ask)

            else:
                order.side = Side.SELL
                order.setAmounts(aggregatedOrders[base][pair][1].dealtAmount - aggregatedOrders[base][pair][0].dealtAmount)
                dealtSaved = aggregatedOrders[base][pair][0].dealtAmount
                if order.dealtCurrency == order.base:
                    order.setSaving(dealtSaved*ask - dealtSaved*bid)
                else:
                    order.setSaving(dealtSaved/bid - dealtSaved/ask)

            nettedOrders[base][pair] = order
            print "Condense %s " % order.__str__()

    #net across accounts (assume EUR and USD for now)
    for pair in sortedKeys(nettedOrders['USD']):
        order1 = nettedOrders['USD'][pair]

        if nettedOrders['EUR'].has_key(pair):
            order2 = nettedOrders['EUR'][pair]

            if order1.side != order2.side:
                buyOrder = order1 if order1.isBuy() else order2
                sellOrder = order2 if order1.isBuy() else order1

                if (buyOrder.baseAmount >= sellOrder.baseAmount):
                    buyOrder.net(sellOrder)
                    sellOrder.setInternal()

                    shadow = FXOrder.newBuyOrder("Shadow", buyOrder.base, buyOrder.term, buyOrder.dealtCurrency)
                    dealtAmount = sellOrder.baseAmount if sellOrder.dealtCurrency != sellOrder.base else sellOrder.termAmount
                    shadow.setAmounts(dealtAmount, True)
                    shadow.setInternal()
                else:
                    sellOrder.net(buyOrder)
                    buyOrder.setInternal()

                    shadow = FXOrder.newSellOrder("Shadow", sellOrder.base, sellOrder.term, sellOrder.dealtCurrency)
                    dealtAmount = buyOrder.baseAmount if buyOrder.dealtCurrency != buyOrder.base else buyOrder.termAmount
                    shadow.setAmounts(dealtAmount, True)
                    shadow.setInternal()

                if not shadowOrders.has_key(shadow.contraCurrency()): shadowOrders[shadow.contraCurrency()]={}
                shadowOrders[shadow.contraCurrency()][pair] = shadow

    return nettedOrders,shadowOrders

if __name__ == "__main__":
    total = 0
    count = 0
    totals = []
    for i in range(0,1):
        accounts = initAccounts()
        printPrices()
        accounts.printAccountTargets()
        accounts.printAccountOrders()
        netOrders, shadowOrders = getTotals(accounts)

        accountCCYTotal1 = 0
        for order in accounts.getAccountOrders():
            contraCCy = order.contraCurrency()
            contraAmount = order.contraAmount() if contraCCy=='USD' else convertToMid('USD',contraCCy, order.contraAmount())
            accountCCYTotal1 += contraAmount

        nettedCCYTotal2 = 0
        for base in sortedKeys(netOrders):
            for key in sortedKeys(netOrders[base]):
                order = netOrders[base][key]
                contraAmount = order.contraAmount() if base=='USD' else convertToMid('USD', base, order.contraAmount())
                nettedCCYTotal2 += contraAmount

        for base in sortedKeys(shadowOrders):
            for key in sortedKeys(shadowOrders[base]):
                order = shadowOrders[base][key]
                contraAmount = order.contraAmount() if base=='USD' else convertToMid('USD', base, order.contraAmount())
                nettedCCYTotal2 += contraAmount

        print ""
        totalSaved = 0
        for base in netOrders:
            for key in sortedKeys(netOrders[base]):
                order = netOrders[base][key]
                saved = order.getSaving()
                contraCurrency = order.base if order.dealtCurrency == order.term else order.term
                if (contraCurrency != 'USD'):
                    savedUSD = convertToMid('USD', contraCurrency, saved)
                    if (not order.internal):
                        print "%s (saving %8.2f %s, %8.2f USD)" % (order.__str__(), saved, contraCurrency, savedUSD)
                    saved = savedUSD
                else:
                    if (not order.internal):
                        print "%s (saving %8.2f %s)" % (order.__str__(), saved, contraCurrency)
                totalSaved += saved

        print "\nTotal USD amount saved across the accounts (using individual trades) %.2f" % totalSaved

        print "\nTotal USD amount saved across the accounts (using net account flow) %.2f" % (nettedCCYTotal2 - accountCCYTotal1)

        total += totalSaved
        count += 1
        totals.append(saved)
    print "Average = %f" % (total /count)

    #totals.sort()
    #hist, bin_edges = numpy.histogram(totals, 100)
    #for i in range(0, len(hist)):
    #    print int(bin_edges[i]), hist[i]
    #print totals

