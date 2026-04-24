# src/utils/portfolio_manager.py
import json
import os
from datetime import datetime
import yfinance as yf

PORTFOLIO_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "portfolio.json"
)

# ── Default dummy portfolio ───────────────────────────────────────────────────
DEFAULT_PORTFOLIO = {
    "cash_balance": 10000.00,
    "holdings": {
        "AAPL": {
            "shares": 10,
            "avg_cost": 150.00,
            "total_invested": 1500.00
        },
        "MSFT": {
            "shares": 5,
            "avg_cost": 300.00,
            "total_invested": 1500.00
        },
        "NVDA": {
            "shares": 3,
            "avg_cost": 400.00,
            "total_invested": 1200.00
        },
        "SPY": {
            "shares": 4,
            "avg_cost": 420.00,
            "total_invested": 1680.00
        },
        "TSLA": {
            "shares": 8,
            "avg_cost": 200.00,
            "total_invested": 1600.00
        },
    },
    "transactions": [
        {
            "date": "2024-01-15",
            "type": "BUY",
            "ticker": "AAPL",
            "shares": 10,
            "price": 150.00,
            "total": 1500.00,
            "note": "Initial position"
        },
        {
            "date": "2024-01-15",
            "type": "BUY",
            "ticker": "MSFT",
            "shares": 5,
            "price": 300.00,
            "total": 1500.00,
            "note": "Initial position"
        },
        {
            "date": "2024-02-01",
            "type": "BUY",
            "ticker": "NVDA",
            "shares": 3,
            "price": 400.00,
            "total": 1200.00,
            "note": "Initial position"
        },
        {
            "date": "2024-02-15",
            "type": "BUY",
            "ticker": "SPY",
            "shares": 4,
            "price": 420.00,
            "total": 1680.00,
            "note": "Index fund allocation"
        },
        {
            "date": "2024-03-01",
            "type": "BUY",
            "ticker": "TSLA",
            "shares": 8,
            "price": 200.00,
            "total": 1600.00,
            "note": "Initial position"
        },
    ]
}


# ── File I/O ──────────────────────────────────────────────────────────────────
def load_portfolio() -> dict:
    """Loads portfolio from JSON. Creates default if not found."""
    filepath = os.path.abspath(PORTFOLIO_FILE)
    if not os.path.exists(filepath):
        save_portfolio(DEFAULT_PORTFOLIO)
        return DEFAULT_PORTFOLIO.copy()
    with open(filepath, "r") as f:
        return json.load(f)


def save_portfolio(portfolio: dict):
    """Saves portfolio to JSON file."""
    filepath = os.path.abspath(PORTFOLIO_FILE)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(portfolio, f, indent=2)


# ── Live price ────────────────────────────────────────────────────────────────
def get_live_price(ticker: str) -> float:
    """Gets current market price for a ticker."""
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period="2d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None


# ── Portfolio summary ─────────────────────────────────────────────────────────
def get_portfolio_summary() -> dict:
    """Returns full portfolio enriched with live prices and P&L."""
    portfolio = load_portfolio()
    holdings  = portfolio.get("holdings", {})
    cash      = portfolio.get("cash_balance", 0)

    enriched         = []
    total_mkt_value  = 0
    total_cost       = 0

    for ticker, data in holdings.items():
        shares         = data["shares"]
        avg_cost       = data["avg_cost"]
        total_invested = data["total_invested"]

        price = get_live_price(ticker) or avg_cost
        market_value  = round(price * shares, 2)
        gain_loss     = round(market_value - total_invested, 2)
        gain_loss_pct = round(
            (gain_loss / total_invested) * 100, 2
        ) if total_invested > 0 else 0

        enriched.append({
            "ticker":        ticker,
            "shares":        shares,
            "avg_cost":      avg_cost,
            "current_price": price,
            "market_value":  market_value,
            "total_invested": total_invested,
            "gain_loss":     gain_loss,
            "gain_loss_pct": gain_loss_pct,
        })

        total_mkt_value += market_value
        total_cost      += total_invested

    total_gain_loss     = round(total_mkt_value - total_cost, 2)
    total_gain_loss_pct = round(
        (total_gain_loss / total_cost) * 100, 2
    ) if total_cost > 0 else 0

    return {
        "holdings":              enriched,
        "cash_balance":          round(cash, 2),
        "total_invested":        round(total_cost, 2),
        "total_market_value":    round(total_mkt_value, 2),
        "total_portfolio_value": round(total_mkt_value + cash, 2),
        "total_gain_loss":       total_gain_loss,
        "total_gain_loss_pct":   total_gain_loss_pct,
        "transactions":          portfolio.get("transactions", []),
    }


# ── Buy ───────────────────────────────────────────────────────────────────────
def buy_stock(ticker: str, shares: float, note: str = "") -> dict:
    """Buys shares at live price. Deducts from cash."""
    ticker = ticker.upper().strip()
    price  = get_live_price(ticker)

    if price is None:
        return {
            "success": False,
            "message": f"Could not fetch price for **{ticker}**. "
                       f"Please check the ticker symbol."
        }
    if shares <= 0:
        return {"success": False, "message": "Shares must be greater than 0."}

    total_cost = round(price * shares, 2)
    portfolio  = load_portfolio()
    cash       = portfolio.get("cash_balance", 0)

    if total_cost > cash:
        max_shares = int(cash // price)
        return {
            "success": False,
            "message": (
                f"Insufficient funds! This purchase costs **${total_cost:,.2f}** "
                f"but you only have **${cash:,.2f}** cash.\n"
                f"You can afford up to **{max_shares} shares** of {ticker}."
            )
        }

    holdings = portfolio.get("holdings", {})
    if ticker in holdings:
        existing          = holdings[ticker]
        new_shares        = existing["shares"] + shares
        new_invested      = existing["total_invested"] + total_cost
        holdings[ticker]  = {
            "shares":         new_shares,
            "avg_cost":       round(new_invested / new_shares, 2),
            "total_invested": round(new_invested, 2),
        }
    else:
        holdings[ticker] = {
            "shares":         shares,
            "avg_cost":       price,
            "total_invested": total_cost,
        }

    portfolio["cash_balance"] = round(cash - total_cost, 2)
    portfolio["holdings"]     = holdings
    portfolio["transactions"].insert(0, {
        "date":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type":   "BUY",
        "ticker": ticker,
        "shares": shares,
        "price":  price,
        "total":  total_cost,
        "note":   note or f"Chat buy at ${price}",
    })

    save_portfolio(portfolio)
    return {
        "success": True,
        "ticker": ticker,
        "shares": shares,
        "price":  price,
        "total":  total_cost,
        "remaining_cash": portfolio["cash_balance"],
        "message": (
            f"✅ Bought **{shares} shares** of **{ticker}** "
            f"at **${price}**\n"
            f"Total: **${total_cost:,.2f}** | "
            f"Cash left: **${portfolio['cash_balance']:,.2f}**"
        )
    }


# ── Sell ──────────────────────────────────────────────────────────────────────
def sell_stock(ticker: str, shares: float, note: str = "") -> dict:
    """Sells shares at live price. Adds proceeds to cash."""
    ticker    = ticker.upper().strip()
    portfolio = load_portfolio()
    holdings  = portfolio.get("holdings", {})

    if ticker not in holdings:
        return {
            "success": False,
            "message": f"You don't own any shares of **{ticker}**."
        }

    existing     = holdings[ticker]
    owned_shares = existing["shares"]

    if shares <= 0:
        return {"success": False, "message": "Shares must be greater than 0."}
    if shares > owned_shares:
        return {
            "success": False,
            "message": (
                f"You only own **{owned_shares} shares** of {ticker}. "
                f"Cannot sell {shares}."
            )
        }

    price = get_live_price(ticker)
    if price is None:
        return {
            "success": False,
            "message": f"Could not fetch price for **{ticker}**."
        }

    proceeds      = round(price * shares, 2)
    cost_basis    = round(existing["avg_cost"] * shares, 2)
    realized_gain = round(proceeds - cost_basis, 2)
    realized_pct  = round((realized_gain / cost_basis) * 100, 2)

    remaining = owned_shares - shares
    if remaining == 0:
        del holdings[ticker]
    else:
        holdings[ticker]["shares"]         = remaining
        holdings[ticker]["total_invested"] = round(
            existing["total_invested"] - cost_basis, 2
        )

    portfolio["cash_balance"] = round(
        portfolio.get("cash_balance", 0) + proceeds, 2
    )
    portfolio["holdings"] = holdings
    portfolio["transactions"].insert(0, {
        "date":              datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type":              "SELL",
        "ticker":            ticker,
        "shares":            shares,
        "price":             price,
        "total":             proceeds,
        "realized_gain":     realized_gain,
        "realized_gain_pct": realized_pct,
        "note":              note or f"Chat sell at ${price}",
    })

    save_portfolio(portfolio)
    return {
        "success":       True,
        "ticker":        ticker,
        "shares":        shares,
        "price":         price,
        "proceeds":      proceeds,
        "realized_gain": realized_gain,
        "realized_pct":  realized_pct,
        "updated_cash":  portfolio["cash_balance"],
        "message": (
            f"✅ Sold **{shares} shares** of **{ticker}** "
            f"at **${price}**\n"
            f"Proceeds: **${proceeds:,.2f}** | "
            f"Gain/Loss: **${realized_gain:,.2f} ({realized_pct}%)** | "
            f"Cash: **${portfolio['cash_balance']:,.2f}**"
        )
    }


# ── Reset ─────────────────────────────────────────────────────────────────────
def reset_portfolio():
    """Resets to default dummy portfolio."""
    save_portfolio(DEFAULT_PORTFOLIO)