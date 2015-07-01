#!/bin/bash
# wheel-of-food.py
# Spin the wheel of food and figure out what you want for your next meal!

import requests
import oauth2
import logging
import random
import argparse
import json
import sys

file = open('config.json','r')
config = json.loads(file.read())
file.close()

CONSUMER_KEY = config['CONSUMER_KEY']
CONSUMER_SECRET = config['CONSUMER_SECRET']
TOKEN = config['TOKEN']
TOKEN_SECRET = config['TOKEN_SECRET']

class Wheel():
    def __init__(self,CONSUMER_KEY,CONSUMER_SECRET,TOKEN,TOKEN_SECRET):
        self.CONSUMER_KEY = CONSUMER_KEY
        self.CONSUMER_SECRET = CONSUMER_SECRET
        self.TOKEN = TOKEN
        self.TOKEN_SECRET = TOKEN_SECRET
        self.base_url = 'https://api.yelp.com/v2/search'
        self.food_categories = config['categories']
        self.adjectives = config['adjectives']
        self.foods = config['foods']

    def _gen_signed_url(self, url_params):
        """ Generate a signed URL to call using the token and consumer identifiers and their respective secrets.
        url_params contains extra parameters to pass to Yelp's API URL beyond the authentication stuff;
        In our case, we're using it to pass along the type of food we want and our zip code.
        returns: signed_url_string """
        self.consumer = oauth2.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
        logging.debug(self.consumer)
        self.request = oauth2.Request(method='GET', url = self.base_url, parameters = url_params)
        logging.debug(self.request)
        self.request.update(
            {
                'oauth_nonce': oauth2.generate_nonce(),
                'oauth_timestamp': oauth2.generate_timestamp(),
                'oauth_token': TOKEN,
                'oauth_consumer_key': CONSUMER_KEY
            }
        )
        logging.debug(self.request)
        self.token = oauth2.Token(TOKEN, TOKEN_SECRET)
        logging.debug(self.token)
        self.request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), self.consumer, self.token)
        return self.request.to_url()

    def _select_food(self):
        """ Selects a random food category from the provided category list.
        Returns: category """
        return random.choice(self.food_categories)

    def spin(self, location, category=None, distance=10000):
        """ Spins the wheel. Hits up Yelp's API for food based on the provided ZIP code and the optional category of food. """
        if category is None:
            self.category = self._select_food()
        else:
            self.category = category
        
        if random.choice([True, False]) == True:
            toss_food = ", tossing {0} and {1} everywhere...".format(self.foods[random.randint(0, len(self.foods))], self.foods[random.randint(0, len(self.foods))])
        else:
            toss_food = "..."
            
        print("You spin the Wheel of Food!")
        print("The Wheel of Food spins {0}{1}".format(self.adjectives[random.randint(0, len(self.adjectives))], toss_food))
        print("The Wheel of Food comes to a halt, landing on {0}!".format(self.category.upper()))
        print("")

        # No point calling the API if the wheel decides we should go hungry or spin again.
        if self.category == "GO HUNGRY" or self.category == "SPIN AGAIN":
            return
        url_params = {'location': location, 'term': self.category, 'radius_filter': distance, 'limit': '20', 'category_filter': 'food,restaurants'}
        self.signed_url = self._gen_signed_url(url_params)
        logging.debug(self.signed_url)
        r = requests.get(self.signed_url)
        logging.debug(r.content)
        # If we passed proper authentication, we should be able to return a list of businesses.
        # Otherwise, we get the error and print it to the user.
        try:
            self.restaurants = r.json()['businesses']
        except KeyError:
            msg = "Yelp returned an error. The error details:\n"
            error = r.json()['error']
            for key in error.keys():
                msg += "{0}: {1}\n".format(key, error[key])
            logging.critical(msg)
            raise ValueError(msg)
        try:
            self.choice = random.choice(self.restaurants)
        except IndexError:
            print("No results found. Spin again!")
            sys.exit()
        return

parser = argparse.ArgumentParser("Hungry and can't decide what to eat? Give the Wheel of Food a spin!")
parser.add_argument('--zipcode', '-z', help="The ZIP code where you want to search. Required. (You can also use a city name instead as well.)", required=True)
parser.add_argument('--distance', '-d', help="Distance in meters from the ZIP code. Default is 10km, or about 6.2 miles.")
parser.add_argument('--category','-c',help="Specify this option if you feel like you know what you want to eat.")
parser.add_argument('--debug',action='store_true', default = False, help=argparse.SUPPRESS)
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.CRITICAL)

category = args.category
zipcode = args.zipcode
distance = args.distance
if distance is None:
    distance = 10000
wheel = Wheel(CONSUMER_KEY,CONSUMER_SECRET,TOKEN,TOKEN_SECRET)
wheel.spin(zipcode, category, distance)
if wheel.category == "GO HUNGRY" or wheel.category == "SPIN AGAIN":
    sys.exit()

choice = wheel.choice['name']
url = wheel.choice['url']
rating = wheel.choice['rating']
category = wheel.category
review_count = wheel.choice['review_count']
display_address = wheel.choice['location']['display_address']
url = wheel.choice['url']

# Some restaurants come with non-ASCII-encoded letters. When that happens, let's force the encoding to be utf-8 and try again.
choice = choice.encode('utf-8', 'replace')
msg = "Hungry for {0}? Try {1}, rated at {2} stars with {3} reviews!".format(category, choice, rating, review_count)
print(msg)
print("Address:")
for address in display_address:
    print(address)
print("")
print("Yelp URL: {0}".format(url))
