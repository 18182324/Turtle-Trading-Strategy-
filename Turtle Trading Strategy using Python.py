from talib import ATR
from time import time

def initialize(context):
    """
    Initialize parameters.
    """
    context.is_test = True
    context.is_debug = False
    context.is_info = True
    
    if context.is_debug:
        start_time = time()

    # Data
    context.symbols = [
        'BP',
        'CD',
        'CL',
        'ED',
        'GC',
        'HG',
        'HO',
        'HU',
        'JY',
        'SB',
        'SF',
        'SP',
        'SV',
        'TB',
        'TY',
        'US'
    ]
    context.markets = map(
        lambda market: continuous_future(market),
        context.symbols
    )
    context.price = None
    context.prices = None
    context.contract = None
    context.contracts = None
    context.open_orders = None
    context.average_true_range = {}
    context.dollar_volatility = {}
    context.trade_size = {}
    
    # Signal
    context.twenty_day_breakout = 20
    context.fifty_five_day_breakout = 55
    context.twenty_day_high = {}
    context.twenty_day_low = {}
    context.fifty_five_day_high = {}
    context.fifty_five_day_low = {}
    
    # Risk
    context.price_threshold = 1
    context.capital = context.portfolio.starting_cash
    context.profit = 0
    context.capital_risk_per_trade = 0.01
    context.capital_multiplier = 2
    context.stop = {}
    context.has_stop = {}
    context.stop_multiplier = 2
    context.market_risk_limit = 4
    context.market_risk = {}
    context.direction_risk_limit = 12
    context.long_risk = 0
    context.short_risk = 0
    
    # Order
    context.orders = {}
    context.filled = 1
    context.canceled = 2
    context.rejected = 3
    context.long_direction = 'long'
    context.short_direction = 'short'
    
    for market in context.markets:
        context.orders[market] = []
        context.stop[market] = 0
        context.has_stop[market] = False
        context.market_risk[market] = 0

    schedule_function(
        func=clear_stops,
        time_rule=time_rules.market_open(minutes=1)
    )
    
    schedule_function(
        func=log_risks,
        time_rule=time_rules.market_close(minutes=1)
    )
    
    if context.is_test:
        assert(len(context.symbols) == 16)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def handle_data(context, data):
    """
    Process data every minute.
    """
    if context.is_debug:
        start_time = time()
        
    get_prices(context, data)
    validate_prices(context)
    context.prices = context.prices.transpose(2, 1, 0)
    context.prices = context.prices.reindex()
    compute_highs(context)
    compute_lows(context)
    get_contracts(context, data)
    context.open_orders = get_open_orders()
    compute_average_true_ranges(context)
    compute_dollar_volatilities(context)
    compute_trade_sizes(context)
    update_risks(context)
    place_stop_orders(context)
    detect_entry_signals(context)
    
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 8192)

def clear_stops(context, data):
    """
    Clear stops 1 minute after market open.
    """
    if context.is_debug:
        start_time = time()
        
    for market in context.markets:
        context.has_stop[market] = False
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def log_risks(context, data):
    """
    Log long and short risk 1 minute before market close.
    """
    record(
        long_risk = context.long_risk,
        short_risk = context.short_risk
    )

def get_prices(context, data):
    """
    Get high, low, and close prices.
    """
    if context.is_debug:
        start_time = time()
        
    fields = ['high', 'low', 'close']
    bars = 22
    frequency = '1d'
    
    context.prices = data.history(
        context.markets,
        fields,
        bars,
        frequency
    )
    
    if context.is_test:
        assert(context.prices.shape[0] == 3)
        assert(context.prices.shape[1] == 22)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 8192)

def validate_prices(context):
    """
    Drop markets with null prices.
    """
    if context.is_debug:
        start_time = time()
        
    context.prices.dropna(axis=2, inplace=True)
    
    validated_markets = map(
        lambda market: market.root_symbol,
        context.prices.axes[2]
    )
    
    markets = map(
        lambda market: market.root_symbol,
        context.markets
    )
    
    dropped_markets = list(
        set(markets) - set(validated_markets)
    )
    
    if context.is_debug and dropped_markets:
        log.debug(
            'Null prices for %s. Dropped.'
            % ', '.join(dropped_markets)
        )

    if context.is_test:
        assert(context.prices.shape[0] == 3)
        assert(context.prices.shape[1] == 22)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def compute_highs(context):
    """
    Compute 20 and 55 day high.
    """
    if context.is_debug:
        start_time = time()
        
    for market in context.prices.items:
        context.twenty_day_high[market] = context\
            .prices[market]\
            .high[-context.twenty_day_breakout-1:-1]\
            .max()
        context.fifty_five_day_high[market] = context\
            .prices[market]\
            .high[-context.fifty_five_day_breakout-1:-1]\
            .max()
            
    if context.is_test:
        assert(len(context.twenty_day_high) > 0)
        assert(len(context.fifty_five_day_high) > 0)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def compute_lows(context):
    """
    Compute 20 and 55 day low.
    """
    if context.is_debug:
        start_time = time()
        
    for market in context.prices.items:
        context.twenty_day_low[market] = context\
            .prices[market]\
            .low[-context.twenty_day_breakout-1:-1]\
            .min()
        context.fifty_five_day_low[market] = context\
            .prices[market]\
            .low[-context.fifty_five_day_breakout-1:-1]\
            .min()

    if context.is_test:
        assert(len(context.twenty_day_low) > 0)
        assert(len(context.fifty_five_day_low) > 0)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def get_contracts(context, data):
    """
    Get futures contracts.
    """
    if context.is_debug:
        start_time = time()
        
    fields = 'contract'
    
    context.contracts = data.current(
        context.markets,
        fields
    )
    
    if context.is_test:
        assert(context.contracts.shape[0] > 0)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def is_trade_allowed(context, market, direction):
    """
    Check if allowed to trade.
    """
    if context.is_debug:
        start_time = time()
        
    is_trade_allowed = True
    
    if context.portfolio.cash <= 0:
        is_trade_allowed = False
        
    if context.capital <= 0:
        is_trade_allowed = False
        
    if context.price < context.price_threshold:
        is_trade_allowed = False
        
    if context.open_orders:
        if context.contracts[market] in context.open_orders:
            is_trade_allowed = False
            
    if context.market_risk[market] > context.market_risk_limit:
        is_trade_allowed = False
        
    if direction == context.long_direction\
            and context.long_risk > context.direction_risk_limit:
        is_trade_allowed = False
        
    if direction == context.short_direction\
            and context.short_risk > context.direction_risk_limit:
        is_trade_allowed = False
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)
        
    return is_trade_allowed

def compute_average_true_ranges(context):
    """
    Compute average true ranges, or N.
    """
    if context.is_debug:
        start_time = time()
        
    rolling_window = 21
    moving_average = 20
    
    for market in context.prices.items:
        context.average_true_range[market] = ATR(
            context.prices[market].high[-rolling_window:],
            context.prices[market].low[-rolling_window:],
            context.prices[market].close[-rolling_window:],
            timeperiod=moving_average
        )[-1]
        
    if context.is_test:
        assert(len(context.average_true_range) > 0)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def compute_dollar_volatilities(context):
    """
    Compute dollar volatilities, or dollars per point.
    """
    if context.is_debug:
        start_time = time()
        
    for market in context.prices.items:
        context.contract = context.contracts[market]
        
        context.dollar_volatility[market] = context.contract.multiplier\
            * context.average_true_range[market]
            
    if context.is_test:
        assert(len(context.dollar_volatility) > 0)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def compute_trade_sizes(context):
    """
    Compute trade sizes, or amount per trade.
    """
    if context.is_debug:
        start_time = time()
        
    context.profit = context.portfolio.portfolio_value\
        - context.portfolio.starting_cash
        
    if context.profit < 0:
        context.capital = context.portfolio.starting_cash\
            + context.profit\
            * context.capital_multiplier

    if context.capital <= 0:
        for market in context.prices.items:
            context.trade_size[market] = 0
    else:
        for market in context.prices.items:
            context.trade_size[market] = int(context.capital\
                * context.capital_risk_per_trade\
                / context.dollar_volatility[market])

    if context.is_test:
        assert(len(context.trade_size) > 0)
        
    if context.is_debug:
        time_taken = (time() - start_time) * 1000
        log.debug('Executed in %f ms.' % time_taken)
        assert(time_taken < 1024)

def update_risks(context):
    """
    Update long, short, and market risks.
    """
    for market in context.orders:
        for order_identifier in context.orders[market]:
            a_order = get_order(order_identifier)
            
            if a_order.status == context.filled:
                if a_order.limit_reached:
                    context.market_risk[market] += 1
                    
                    if a_order.amount > 0:
                        context.long_risk += 1
                    if a_order.amount < 0:
                        context.short_risk += 1
                        
                if a_order.stop_reached:
                    context.market_risk[market] -= 1
                    
                    if a_order.amount > 0:
                        context.long_risk -= 1
                    if a_order.amount < 0:
                        context.short_risk -= 1
                        
                context.orders[market].remove(order_identifier)
                
            if a_order.status == context.canceled\
                    or a_order.status == context.rejected:
                context.orders[market].remove(order_identifier)

def place_stop_orders(context):
    """
    Place stop orders at 2 times average true range.
    """
    for position in context.portfolio.positions:
        market = continuous_future(position.root_symbol)
        amount = context.portfolio.positions[position].amount
        cost_basis = context.portfolio.positions[position].cost_basis
        
        try:
            context.price = context.prices[market].close[-1]
        except KeyError:
            context.price = 0

        if not context.has_stop[market]:
            if amount > 0 and context.price >= cost_basis:
                context.stop[market] = context.price\
                    - context.average_true_range[market]\
                    * context.stop_multiplier
            elif amount > 0 and context.price < cost_basis:
                context.stop[market] = cost_basis\
                    - context.average_true_range[market]\
                    * context.stop_multiplier
            elif amount > 0 and context.price == 0:
                context.stop[market] = cost_basis\
                    - context.average_true_range[market]\
                    * context.stop_multiplier
            elif amount < 0 and context.price >= cost_basis:
                context.stop[market] = cost_basis\
                    + context.average_true_range[market]\
                    * context.stop_multiplier
            elif amount < 0 and context.price < cost_basis:
                context.stop[market] = context.price\
                    + context.average_true_range[market]\
                    * context.stop_multiplier
            elif amount < 0 and context.price == 0:
                context.stop[market] = cost_basis\
                    + context.average_true_range[market]\
                    * context.stop_multiplier

            order_identifier = order_target(
                position,
                0,
                style=StopOrder(context.stop[market])
            )
            if order_identifier is not None:
                context.orders[market].append(order_identifier)
                context.has_stop[market] = True

            if context.is_info:
                log.info(
                    'Stop %s %.2f'
                    % (
                        market.root_symbol,
                        context.stop[market]
                    )
                )

def detect_entry_signals(context):
    """
    Place limit orders on 20 or 55 day breakout.
    """
    for market in context.prices.items:
        context.price = context.prices[market].close[-1]

        if context.price > context.twenty_day_high[market]\
                or context.price > context.fifty_five_day_high[market]:
            if is_trade_allowed(context, market, context.long_direction):
                order_identifier = order(
                    context.contract,
                    context.trade_size[market],
                    style=LimitOrder(context.price)
                )

                if order_identifier is not None:
                    context.orders[market].append(order_identifier)

                if context.is_info:
                    log.info(
                        'Long %s %i@%.2f'
                        % (
                            market.root_symbol,
                            context.trade_size[market],
                            context.price
                        )
                    )
        if context.price < context.twenty_day_low[market]\
                or context.price < context.fifty_five_day_low[market]:
            if is_trade_allowed(context, market, context.short_direction):
                order_identifier = order(
                    context.contract,
                    -context.trade_size[market],
                    style=LimitOrder(context.price)
                )
                if order_identifier is not None:
                    context.orders[market].append(order_identifier)

                if context.is_info:
                    log.info(
                        'Short %s %i@%.2f'
                        % (
                            market.root_symbol,
                            context.trade_size[market],
                            context.price
                        )
                    )