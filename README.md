# Chii
 
A minimal marketplace bot maker.

## Installation

```shell
pip install chii
```

## Usage

Import and initialize the `Chii` object:

```py
from chii.main import Chii

chii = Chii("<bot_token>")
```

### Add decorators to the following callback functions:

This function takes in a query and must return an iterable of search results from the query (e.g. a `List` of result `Dict`s).

```py
@chii.query
def make_query(query: str):
```

This function takes in a result (an element of the iterable returned by `make_query`) and returns a string containing the desired formatted message to be sent out to the user.

```py
@chii.message
def get_message(result) -> str:
```

This function takes in a result and must return a uniquely identifiable attribute of the result to use as the 'primary key'.

```py
@chii.key
def get_key(result):
```

This function takes in a result and must return the image url of the result.

```py
@chii.image
def get_image(result) -> str:
```

Start the bot:

```py
if __name__ == "__main__":
    chii.start()
```

## Bot Usage

Add a query

```
/add <query>
```

Remove a query

```
/rm <query>
```

List queries

```
/ls
```

Fetch queries

```
/fetch
```

## Example

Below is a complete example made for the Yahoo! Auctions marketplace.

```py
import re
import requests
import urllib
from bs4 import BeautifulSoup
from datetime import datetime

from chii.main import Chii

YAHUOKU_SEARCH_TEMPLATE = r"https://auctions.yahoo.co.jp/search/search?p={query}&b={start}&n={count}&s1=new&o1=d"

POST_TIMESTAMP_REGEX = r"^.*i-img\d+x\d+-(\d{10}).*$"
AUCTION_TIMESTAMP_REGEX = r"^.*etm=(\d{10}),stm=(\d{10}).*$"

KEY_TITLE = "title"
KEY_URL = "url"
KEY_IMAGE = "img"
KEY_POST_TIMESTAMP = "post_ts"
KEY_END_TIMESTAMP = "end_ts"
KEY_START_TIMESTAMP = "start_ts"
KEY_BUYNOW_PRICE = "buynow_price"
KEY_CURRENT_PRICE = "curr_price"
KEY_START_PRICE = "start_price"
KEY_ITEM_ID = "item_id"

chii = Chii("<bot_token>")


@chii.image
def get_image(result):
    return result[KEY_IMAGE]


@chii.key
def get_key(result):
    return result[KEY_ITEM_ID]


@chii.message
def get_message(result):
    return f"{result[KEY_URL]}\n`{result[KEY_TITLE]}`\n_{datetime.fromtimestamp(result[KEY_POST_TIMESTAMP]).strftime('%d/%m/%Y %I:%M:%S %p')}_\n*{result[KEY_START_PRICE]}円*"


@chii.query
def make_query(query: str):
    url = YAHUOKU_SEARCH_TEMPLATE.format(query=urllib.parse.quote_plus(query), start=1, count=100)
    r = requests.get(url)

    return parse_raw_results(r.text)


def parse_raw_results(raw: str):
    results = []
    soup = BeautifulSoup(raw, "lxml")

    product_details = soup.find_all("div", class_="Product__detail")
    for product_detail in product_details:
        product_bonuses = product_detail.find_all("div", class_="Product__bonus")
        product_titlelinks = product_detail.find_all("a", class_="Product__titleLink")

        if not product_bonuses or not product_titlelinks:
            continue

        product_bonus = product_bonuses[0]
        product_titlelink = product_titlelinks[0]

        auction_title = product_titlelink["data-auction-title"]
        auction_img = product_titlelink["data-auction-img"]
        href = product_titlelink["href"]
        cl_params = product_titlelink["data-cl-params"]

        match = re.match(POST_TIMESTAMP_REGEX, auction_img)
        if not match:
            continue

        post_timestamp = int(match.group(1))

        match = re.match(AUCTION_TIMESTAMP_REGEX, cl_params)
        if not match:
            continue

        end_timestamp = int(match.group(1))
        start_timestamp = int(match.group(2))

        auction_id = product_bonus["data-auction-id"]
        auction_buynowprice = product_bonus["data-auction-buynowprice"]
        auction_price = product_bonus["data-auction-price"]
        auction_startprice = product_bonus["data-auction-startprice"]

        result = {
            KEY_TITLE: auction_title,
            KEY_IMAGE: auction_img,
            KEY_URL: href,
            KEY_POST_TIMESTAMP: post_timestamp,
            KEY_END_TIMESTAMP: end_timestamp,
            KEY_START_TIMESTAMP: start_timestamp,
            KEY_ITEM_ID: auction_id,
            KEY_BUYNOW_PRICE: auction_buynowprice,
            KEY_CURRENT_PRICE: auction_price,
            KEY_START_PRICE: auction_startprice,
        }

        results.append(result)

    return results


if __name__ == "__main__":
    chii.start()
```
