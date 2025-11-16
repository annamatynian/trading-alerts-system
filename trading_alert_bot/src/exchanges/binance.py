"""Binance exchange adapter using ccxt library."""
import logging
from typing import List, Optional
import ccxt.async_support as ccxt

from exchanges.base import ExchangeBase
from models.price import PriceData
from models.alert import ExchangeType

logger = logging.getLogger(__name__)

class BinanceExchange(ExchangeBase):
    @property
    def exchange_type(self) -> ExchangeType:
        return ExchangeType.BINANCE

    async def connect(self) -> bool:
        """Initializes the ccxt Binance client."""
        try:
            self._client = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'options': {
                    'defaultType': 'spot',
                },
            })
            if self.testnet:
                self._client.set_sandbox_mode(True)
            
            # Test connection by fetching markets
            await self._client.load_markets()
            logger.info(f"Connected to Binance {'testnet' if self.testnet else 'mainnet'}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Binance: {e}")
            if self._client:
                await self._client.close()
            return False

    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Fetches the current price for a single symbol from Binance."""
        if not self._client:
            return None
        try:
            # CCXT uses format like 'BTC/USDT'
            ccxt_symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            ticker = await self._client.fetch_ticker(ccxt_symbol)
            return PriceData(
                exchange=self.exchange_type,
                symbol=symbol,
                price=float(ticker['last']),
                volume_24h=float(ticker.get('baseVolume', 0)),
                high_24h=float(ticker.get('high', 0)),
                low_24h=float(ticker.get('low', 0)),
                raw_data=ticker
            )
        except Exception as e:
            logger.error(f"Error fetching price for {symbol} from Binance: {e}")
            return None

    async def get_multiple_prices(self, symbols: List[str]) -> List[PriceData]:
        """Fetches current prices for multiple symbols from Binance."""
        if not self._client:
            return []
        
        results = []
        try:
            ccxt_symbols = [f"{s[:-4]}/{s[-4:]}" for s in symbols]
            tickers = await self._client.fetch_tickers(ccxt_symbols)
            for symbol, ticker in tickers.items():
                original_symbol = symbol.replace('/', '')
                results.append(PriceData(
                    exchange=self.exchange_type,
                    symbol=original_symbol,
                    price=float(ticker['last']),
                    volume_24h=float(ticker.get('baseVolume', 0)),
                    high_24h=float(ticker.get('high', 0)),
                    low_24h=float(ticker.get('low', 0)),
                    raw_data=ticker
                ))
            return results
        except Exception as e:
            logger.error(f"Error fetching multiple prices from Binance: {e}")
            return []

    async def is_symbol_valid(self, symbol: str) -> bool:
        """Checks if a trading symbol is valid on Binance."""
        if not self._client or not self._client.markets:
            await self.connect()
        
        ccxt_symbol = f"{symbol[:-4]}/{symbol[-4:]}"
        return ccxt_symbol in self._client.markets
