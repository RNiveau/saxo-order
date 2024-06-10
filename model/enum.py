from model.enum_with_get_value import EnumWithGetValue


class Strategy(EnumWithGetValue):
    IMP = "Bougie impulsive"
    BH = "Breakout haussier"
    C200 = "Cassure mm200"
    CRANGE = "Cassure de range"
    COMBO = "Combo"
    CONG = "Congestion"
    DIV = "Dividende"
    EH = "Engloblante haussière"
    INTRA = "Intraday"
    IVT = "IVT"
    FLUX = "Journée flux"
    R7 = "Rebond mm7"
    R20 = "Rebond mm20"
    R50 = "Rebond mm50"
    R200 = "Rebond mm200"
    RES = "Résultat d'entreprise"
    REVERSE = "Revere"
    ROULEMENT = "Roulement"
    SI = "Stratagème de l'impulsion"
    SCT = "Support court terme"
    SMT = "Support moyen terme"
    SLT = "Support long terme"
    TF = "Trendfollowing"
    VS = "Vente cassure de support"
    VR = "Vente de résistance"
    VB = "Vente plus bas"
    YOLO = "Yolo"


class Signal(EnumWithGetValue):
    BBB = "BBH"
    BBH = "BBB"
    BO15M = "Breakout 15m"
    BOH1 = "Breakout h1"
    BOH4 = "Breakout h4"
    BHD = "Breakout daily"
    BHW = "Breakout weekly"
    ENGLO = "Englobante"
    DOUBLE_TOP = "Double top"
    FIBO = "Fibo 50%"
    POL = "Polarité"
    RP = "Reprise de l'open"
    TMM7 = "Touchette mm7"
    TMM20 = "Touchette mm20"
    TMM50 = "Touchette mm50"
    TMM200 = "Touchette mm200"
    NONE = "No signal"


class Currency(EnumWithGetValue):
    EURO = "EUR"
    USD = "USD"
    JPY = "JPY"


class AssetType(EnumWithGetValue):
    WARRANT = "WarrantOpenEndKnockOut"
    WARRANT_KNOCK_OUT = "WarrantKnockOut"
    ETF = "Etf"
    TURBO = "MiniFuture"
    STOCK = "Stock"
    INDEX = "StockIndex"
    CFDINDEX = "CfdOnIndex"
    CFDFUTURE = "CfdOnFutures"
    CRYPTO = "Crypto"

    @staticmethod
    def all_saxo_values():
        values = filter(lambda x: x != AssetType.CRYPTO, AssetType)
        return ",".join(values)


class Direction(EnumWithGetValue):
    BUY = "Buy"
    SELL = "Sell"


class TriggerOrder(EnumWithGetValue):
    ABOVE = "above"
    BELLOW = "below"


class OrderType(EnumWithGetValue):
    LIMIT = "limit"
    STOP = "stop"
    OPEN_STOP = "open_stop"
    OCO = "oco"
    STOP_LIMIT = "stoplimit"
    MARKET = "market"
