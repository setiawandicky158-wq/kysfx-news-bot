import sqlite3
import threading
from datetime import datetime, timezone

from config import DATABASE_FILE


# ============================================================
# STATE DATABASE
# ============================================================

class StateManager:
    """
    Persistent state manager untuk KYSFX Bot.

    Digunakan untuk:
    - anti duplicate news
    - calendar alerts
    - calendar results
    - session alerts
    - system events
    """

    def __init__(self, database_file=DATABASE_FILE):

        self.database_file = database_file

        # Mencegah konflik SQLite ketika beberapa
        # bagian bot mengakses database bersamaan.
        self.lock = threading.RLock()

        self._initialize_database()

    # ========================================================
    # DATABASE CONNECTION
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

        connection.execute(
            "PRAGMA busy_timeout=30000"
        )

        return connection

    # ========================================================
    # INITIALIZE
    # ========================================================

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

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_sent_items_created
                    ON sent_items(created_at)
                    """
                )

                connection.commit()

            finally:

                connection.close()

    # ========================================================
    # CHECK ITEM
    # ========================================================

    def exists(self, item_key):

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

                result = cursor.fetchone()

                return result is not None

            finally:

                connection.close()

    # ========================================================
    # MARK ITEM
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
    # CHECK + MARK
    # ========================================================

    def check_and_mark(
        self,
        item_key,
        item_type,
    ):
        """
        Atomic anti-duplicate operation.

        True  = item baru, boleh dikirim.
        False = sudah pernah dikirim.
        """

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
    # REMOVE ITEM
    # ========================================================

    def remove(self, item_key):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    DELETE FROM sent_items
                    WHERE item_key = ?
                    """,
                    (item_key,),
                )

                deleted = cursor.rowcount

                connection.commit()

                return deleted > 0

            finally:

                connection.close()

    # ========================================================
    # CLEAN OLD DATA
    # ========================================================

    def cleanup(self, days=30):

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
                        f"-{int(days)} days",
                    ),
                )

                deleted = cursor.rowcount

                connection.commit()

                return deleted

            finally:

                connection.close()

    # ========================================================
    # COUNT BY TYPE
    # ========================================================

    def count_type(self, item_type):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM sent_items
                    WHERE item_type = ?
                    """,
                    (item_type,),
                )

                result = cursor.fetchone()

                return int(result[0])

            finally:

                connection.close()

    # ========================================================
    # GLOBAL STATS
    # ========================================================

    def stats(self):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT
                        item_type,
                        COUNT(*)
                    FROM sent_items
                    GROUP BY item_type
                    ORDER BY item_type
                    """
                )

                return cursor.fetchall()

            finally:

                connection.close()

    # ========================================================
    # TOTAL
    # ========================================================

    def total(self):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM sent_items
                    """
                )

                result = cursor.fetchone()

                return int(result[0])

            finally:

                connection.close()

    # ========================================================
    # RECENT ITEMS
    # ========================================================

    def recent(self, limit=20):

        with self.lock:

            connection = self._connect()

            try:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT
                        item_key,
                        item_type,
                        created_at
                    FROM sent_items
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (int(limit),),
                )

                return cursor.fetchall()

            finally:

                connection.close()


# ============================================================
# GLOBAL STATE INSTANCE
# ============================================================

state = StateManager()
