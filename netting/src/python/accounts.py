import math, random

from convention import marketConvention
from prices import getPrice, convertToMid, convertTo
from orders import FXOrder, Side

class Account:
    def __init__(self, name, base):
        self.name = name
        self.base = base
        self.targets = {}
        self.orders = {}

    def addTarget(self, ccy, ccyAmount, baseAmount):
        self.targets[ccy] = (ccyAmount, baseAmount)
        self.addOrder(ccy, ccyAmount, baseAmount)

    def getName(self): return self.name

    def getBase(self): return self.base

    def getTarget(self, ccy):
        return self.targets[ccy] if self.targets.has_key(ccy) else (0,0)

    def getOrders(self):
        return self.orders

    def addOrder(self, ccy, ccyAmount, baseAmount):
        pair, base, term = marketConvention(ccy, self.base)
        bid, ask = getPrice(pair)
        order = FXOrder()
        order.account = self.name
        order.base = base
        order.term = term
        order.dealtCurrency = ccy
        order.dealtAmount = math.fabs(ccyAmount)
        if ccy == base:
            if ccyAmount > 0:
                order.price = ask
                order.side = Side.BUY
            else:
                order.price = bid
                order.side = Side.SELL
            order.baseAmount = math.fabs(ccyAmount)
            order.termAmount = math.fabs(baseAmount)
        else:
            if ccyAmount > 0:
                order.price = bid
                order.side = Side.SELL
            else:
                order.price = ask
                order.side = Side.BUY
            order.baseAmount = math.fabs(baseAmount)
            order.termAmount = math.fabs(ccyAmount)
        self.orders[pair]=order


class Accounts:
    def __init__(self, currencies):
        """Construct the accounts holder over a list of currencies.

        @param currencies: List of currencies the accounts have targets for
        """
        self.accounts = {}
        self.currencies = currencies


    def initAccounts(self, accounts):
        """Initialise the account targets with random currency amounts.

        @param accounts: List of tuples for account name, and account base currency
        """
        for accountName, accountCcy in accounts: self.addAccount(accountName, accountCcy)

        for ccy in self.currencies:
            for accountName, accountCcy in accounts:
                if ccy == accountCcy: continue
                r = random.randint(-5,5)
                if (r > 2): target_amount = self.__roundup(convertToMid(ccy, accountCcy, 1000000*random.randint(1,10)))
                elif (r < -2): target_amount = self.__roundup(convertToMid(ccy, accountCcy, -1000000*random.randint(1,10)))
                else: continue
                if target_amount == 0: continue
                account_base_amount = convertTo(accountCcy, ccy, target_amount)
                self.addAccountTarget(accountName, ccy, target_amount, account_base_amount)


    def addAccount(self, name, base):
        """Add a new account with supplied name, and supplied base currency.

        @param name: The name of the account
        @param base: The account base currency
        """
        account = Account(name, base)
        self.accounts[name] = account
        return account


    def addAccountTarget(self, name, ccy, ccyAmount, baseAmount):
        """Add a currency target to an accout with supplied name.

        @param name: The name of the account
        @param ccy: The target currency
        @param ccyAmount: The target currency amount
        @param baseAmount: The amount in the account base currency
        """
        if self.accounts.has_key(name): self.accounts[name].addTarget(ccy, ccyAmount, baseAmount)


    def getAccount(self, name):
        """Retrieve an account using the account name.

        @param name: The name of the account
        @return: The account instance
        """
        if self.accounts.has_key(name): return self.accounts[name]
        return None


    def getAccountNames(self):
        """Return a list of the account names.

        @return: A list of the account names
        """
        names = self.accounts.keys()
        names.sort()
        return names


    def getAccountOrders(self):
        """Return a list of all orders to achieve the account target.

        @return: A list of the orders across all accounts
        """
        orders = []
        for name in self.getAccountNames():
            accountOrders = self.accounts[name].getOrders()
            keys = accountOrders.keys()
            keys.sort()
            for ccy in keys: orders.append(accountOrders[ccy])
        return orders


    def printAccountTargets(self):
        """Print out the account details.
        """
        header = self.__getHeader()
        print "Account Targets: \n"
        print "-"*len(header)
        print header
        print "-"*len(header)
        for ccy in self.currencies: print self.__getRow(ccy)
        print "-"*len(header)


    def printAccountOrders(self):
        """Print out the account orders.
        """
        print "\nIndividual FX Orders: \n"
        for order in self.getAccountOrders(): print order


    def __roundup(self, amount):
        return int(math.ceil(amount/1000000.0)) * 1000000


    def __getHeader(self):
        header = "| %-5s" % "CCY"
        for name in self.getAccountNames(): header = header + "| %12s (%s)" % (name, self.accounts[name].base)
        return header+"|"


    def __getRow(self, ccy):
        row = "| %-5s" % ccy
        for names in self.getAccountNames():
            row = row + "|%+19s" % self.__formatRowEntry(self.accounts[names].getTarget(ccy)[0])
        return row+"|"


    def __formatRowEntry(self, value):
        if (value == 0): return "%12s"%"0"
        return ("%12d"%value)
