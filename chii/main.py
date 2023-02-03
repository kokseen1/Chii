import json
import requests
import telegram
from threading import Lock
from pathlib import Path
from telegram.ext import Updater, CommandHandler

USER_DB_TEMPLATE = lambda: [[], []]


def _send_message(bot, chat_id, message):
    """
    Send a message without throwing
    """

    bot.send_message(
        chat_id,
        message,
        parse_mode=telegram.ParseMode.MARKDOWN,
    )



def _send_image(bot, chat_id, message, image_url):
    bot.send_photo(
        chat_id,
        photo=requests.get(image_url).content,
        caption=message,
        parse_mode=telegram.ParseMode.MARKDOWN,
    )



def _get_message_data(update):
    """
    Parse Telegram `update` object and return chat ID and query text
    """

    message_json = update.message
    chat_id = str(message_json["chat"]["id"])
    message_full = message_json["text"]
    query_text = message_full[message_full.find(" ") + 1 :]

    return chat_id, query_text


class Chii:
    def __init__(self, bot_token) -> None:
        self.db_path = Path.cwd() / "chii_db.json"
        self.lock = Lock()

        self.parse_query = None
        self.craft_message = None
        self.get_image = lambda x: None
        self.get_key = None

        self.bot = telegram.Bot(bot_token)
        self.updater = Updater(bot_token)

    def _write_db(self, db):
        with open(self.db_path, "w") as fp:
            json.dump(db, fp)

    def _get_db(self):
        if not self.db_path.exists():
            db = dict()
            self._write_db(db)
            return db

        with open(self.db_path, "r") as fp:
            return json.load(fp)

    def _fetch_query(self, update, context):
        chat_id, _ = _get_message_data(update)

        self._poller(target_chat_id=chat_id)

    def _list_query(self, update, context):
        chat_id, _ = _get_message_data(update)

        with self.lock:
            db = self._get_db()
            user_db = db.get(chat_id, USER_DB_TEMPLATE())
            queries = user_db[0]

            _send_message(self.bot, chat_id, "\n".join(queries))

    def _parse_queries(self, query_text):
        # Support newline-separated queries
        return [q for q in query_text.strip().split("\n")]

    def _remove_query(self, update, context):
        chat_id, query_text = _get_message_data(update)
        if not query_text:
            return

        with self.lock:
            db = self._get_db()
            user_db = db.get(chat_id, USER_DB_TEMPLATE())

            for query in self._parse_queries(query_text):
                if query in user_db[0]:
                    user_db[0].remove(query)

            db[chat_id] = user_db
            self._write_db(db)

    def _add_query(self, update, context):
        chat_id, query_text = _get_message_data(update)
        if not query_text:
            return

        with self.lock:
            db = self._get_db()
            user_db = db.get(chat_id, USER_DB_TEMPLATE())

            for query in self._parse_queries(query_text):
                if query not in user_db[0]:
                    user_db[0].append(query)

            db[chat_id] = user_db
            self._write_db(db)

    def _send(self, chat_id, result):
        """
        Send a message or image with caption based on whether the
        `get_image` callback is set
        """

        message = self.craft_message(result)
        if message is None:
            return False

        image_url = self.get_image(result)

        try:
            if image_url is not None:
                _send_image(self.bot, chat_id, message, image_url)
            else:
                _send_message(self.bot, chat_id, message)
        except Exception as e:
            print(f"Exception when sending: {e}")
            return False
        
        return True

    def _poller(self, context=None, target_chat_id=None):

        with self.lock:
            db = self._get_db()

        for chat_id, user_db in db.items():

            # Only send to `target_chat_id` if set
            if target_chat_id is not None and chat_id != target_chat_id:
                continue

            queries = user_db[0]
            queried = user_db[1]

            for query in queries:
                results = self.parse_query(query)

                for result in results:
                    key = self.get_key(result)

                    if key is None or key in queried:
                        continue

                    # Store only if message was sent successfully
                    if self._send(chat_id, result) == True:
                        queried.append(key)

            with self.lock:
                db = self._get_db()
                db[chat_id][1] = queried
                self._write_db(db)

    # Public functions

    def start(self):

        if not all([self.parse_query, self.craft_message, self.get_key]):
            raise Exception(f"Required decorators are not set!")

        self.updater.dispatcher.add_handler(CommandHandler("add", self._add_query))
        self.updater.dispatcher.add_handler(CommandHandler("rm", self._remove_query))
        self.updater.dispatcher.add_handler(CommandHandler("ls", self._list_query))
        self.updater.dispatcher.add_handler(CommandHandler("fetch", self._fetch_query))

        self.updater.job_queue.run_repeating(self._poller, interval=3600, first=1)

        self.updater.start_polling()
        print(f"Bot started")

        self.updater.idle()

    # Decorators

    def image(self, fn):
        self.get_image = fn
        return fn

    def key(self, fn):
        self.get_key = fn
        return fn

    def message(self, fn):
        self.craft_message = fn
        return fn

    def query(self, fn):
        self.parse_query = fn
        return fn
