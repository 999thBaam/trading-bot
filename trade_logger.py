import sqlite3
import csv
from datetime import datetime, date


class TradeLogger:
    def __init__(self, db_path="trades.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                strategy TEXT NOT NULL,
                stop_loss REAL NOT NULL,
                pnl REAL,
                exit_reason TEXT,
                opened_at TEXT NOT NULL,
                closed_at TEXT
            )
        """)
        self.conn.commit()

    def open_trade(self, symbol, side, entry_price, quantity, strategy, stop_loss):
        cursor = self.conn.execute(
            """INSERT INTO trades (symbol, side, entry_price, quantity, strategy, stop_loss, opened_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (symbol, side, entry_price, quantity, strategy, stop_loss, datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return cursor.lastrowid

    def close_trade(self, trade_id, exit_price, exit_reason):
        trade = self.get_trade(trade_id)
        if trade is None:
            raise ValueError(f"Trade {trade_id} not found")
        if trade["side"] == "BUY":
            pnl = (exit_price - trade["entry_price"]) * trade["quantity"]
        else:
            pnl = (trade["entry_price"] - exit_price) * trade["quantity"]
        self.conn.execute(
            """UPDATE trades SET exit_price=?, pnl=?, exit_reason=?, closed_at=? WHERE id=?""",
            (exit_price, pnl, exit_reason, datetime.utcnow().isoformat(), trade_id),
        )
        self.conn.commit()

    def get_trade(self, trade_id):
        row = self.conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return dict(row) if row else None

    def get_daily_pnl(self):
        today = date.today().isoformat()
        row = self.conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE closed_at LIKE ? AND pnl IS NOT NULL",
            (f"{today}%",),
        ).fetchone()
        return row["total"]

    def get_total_pnl(self):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE pnl IS NOT NULL"
        ).fetchone()
        return row["total"]

    def get_strategy_stats(self, strategy):
        rows = self.conn.execute(
            "SELECT * FROM trades WHERE strategy=? AND pnl IS NOT NULL", (strategy,)
        ).fetchall()
        if not rows:
            return {"total_trades": 0, "winning_trades": 0, "win_rate": 0.0, "total_pnl": 0.0}
        total = len(rows)
        winners = sum(1 for r in rows if r["pnl"] > 0)
        total_pnl = sum(r["pnl"] for r in rows)
        return {
            "total_trades": total,
            "winning_trades": winners,
            "win_rate": winners / total if total > 0 else 0.0,
            "total_pnl": total_pnl,
        }

    def get_consecutive_losses(self):
        rows = self.conn.execute(
            "SELECT pnl FROM trades WHERE pnl IS NOT NULL ORDER BY id DESC"
        ).fetchall()
        count = 0
        for row in rows:
            if row["pnl"] < 0:
                count += 1
            else:
                break
        return count

    def has_open_position(self):
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE closed_at IS NULL"
        ).fetchone()
        return row["cnt"] > 0

    def get_open_position(self):
        row = self.conn.execute(
            "SELECT * FROM trades WHERE closed_at IS NULL ORDER BY opened_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def update_stop_loss(self, trade_id, new_stop_loss):
        self.conn.execute(
            "UPDATE trades SET stop_loss=? WHERE id=?", (new_stop_loss, trade_id)
        )
        self.conn.commit()

    def get_coins_traded(self):
        rows = self.conn.execute("SELECT DISTINCT symbol FROM trades").fetchall()
        return [r["symbol"] for r in rows]

    def get_all_strategy_stats(self):
        """Get stats for all strategies that have been used."""
        rows = self.conn.execute(
            "SELECT DISTINCT strategy FROM trades WHERE pnl IS NOT NULL"
        ).fetchall()
        return {r["strategy"]: self.get_strategy_stats(r["strategy"]) for r in rows}

    def get_all_closed_trades(self):
        rows = self.conn.execute(
            "SELECT * FROM trades WHERE closed_at IS NOT NULL ORDER BY closed_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def export_csv(self, filepath):
        trades = self.get_all_closed_trades()
        if not trades:
            return
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=trades[0].keys())
            writer.writeheader()
            writer.writerows(trades)

    def close(self):
        self.conn.close()
