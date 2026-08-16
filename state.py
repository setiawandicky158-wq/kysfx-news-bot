import sqlite3
import threading
from datetime import datetime, timezone

from config import DATABASE_FILE


class StateManager:

    def __init__(self, database_file=DATABASE_FILE):
        self.database_file = database_file
        self.lock = threading.Lock()

        self._initialize_database()

    # ========================================================
    # DATABASE INITIALIZATION
    # ========================================================

    def _connect(self):
        connection = sqlite3.connect(
            self.database_file,
            timeout=30,
            check_same_thread=False,
        )

        connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        return connection

    def _initialize_database(self):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sent_items (
                        item_key TEXT PRIMARY KEY,
                        item_type TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_sent_items_type
                    ON sent_items(item_type)
                    """
                )

                connection.commit()

            finally:
                connection.close()

    # ========================================================
    # CHECK
    # ========================================================

    def exists(
        self,
        item_key,
    ):
        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT 1
                    FROM sent_items
                    WHERE item_key = ?
                    LIMIT 1
                    """,
                    (item_key,),
                )

                return cursor.fetchone() is not None

            finally:
                connection.close()

    # ========================================================
    # MARK
    # ========================================================

    def mark_sent(
        self,
        item_key,
        item_type,
    ):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO sent_items (
                        item_key,
                        item_type,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        item_key,
                        item_type,
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                    ),
                )

                connection.commit()

            finally:
                connection.close()

    # ========================================================
    # CHECK + MARK ATOMIC
    # ========================================================

    def check_and_mark(
        self,
        item_key,
        item_type,
    ):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT 1
                    FROM sent_items
                    WHERE item_key = ?
                    LIMIT 1
                    """,
                    (item_key,),
                )

                if cursor.fetchone():
                    return False

                cursor.execute(
                    """
                    INSERT INTO sent_items (
                        item_key,
                        item_type,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        item_key,
                        item_type,
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                    ),
                )

                connection.commit()

                return True

            finally:
                connection.close()

    # ========================================================
    # CLEAN OLD DATA
    # ========================================================

    def cleanup(
        self,
        days=30,
    ):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    DELETE FROM sent_items
                    WHERE created_at < datetime(
                        'now',
                        ?
                    )
                    """,
                    (
                        f"-{days} days",
                    ),
                )

                deleted = cursor.rowcount

                connection.commit()

                return deleted

            finally:
                connection.close()

    # ========================================================
    # STATS
    # ========================================================

    def stats(self):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT item_type, COUNT(*)
                    FROM sent_items
                    GROUP BY item_type
                    ORDER BY item_type
                    """
                )

                return cursor.fetchall()

            finally:
                connection.close()


# ============================================================
# GLOBAL STATE INSTANCE
# ============================================================

state = StateManager()
