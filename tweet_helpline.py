# -*- coding: latin-1 -*-
"""
*******************************************************************************
** Script Name: tweet_helpline.py
** Author(s):   Terrence Beach (tjbeachjr@gmail.com)
*******************************************************************************

** Description:

Use the -c / --config option to specify a configuration for the script (see
provided resources/config_template.json) file.  Modify this file with your
Twitter credentials from https://apps.twitter.com/.

Use the -t / --test option to test the script.  Tests that we can login to
the Twitter API and access / parse the Google Docs spreadsheet containing
the helpline tweets.

The script will send each of the tweets in the configured tweets Google Docs
spreadsheet with a computed wait between tweets.  The wait will be based on the
configured tweet_shift (in seconds) divided by the number of tweets to send.
The default tweet_shift is 14400 seconds (4 hours).

This script was written specifically for The Pixel Project:
Web:     http://www.thepixelproject.net/
Twitter: @PixelProject

*******************************************************************************
"""
import gspread
import json
import logging
import os
import requests
import time
from datetime import datetime, timezone
from google.oauth2.service_account import Credentials
from optparse import OptionParser

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_helpline_tweets(config, test_mode=False):
    # Login to the BlueSky account
    logger.info('Logging into BlueSky account')
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={
            "identifier": config["bluesky"]["handle"],
            "password": config["bluesky"]["password"]
        },
    )
    if not resp.ok:
        logger.error(
            "BlueSky login failed: status=%s body=%s",
            resp.status_code,
            resp.text,
        )
        resp.raise_for_status()
    session = resp.json()
    access_token = session["accessJwt"]

    # Login to the Google Docs API
    logger.info('Open Helpline Tweets Google Doc spreadsheet')
    values_list = []
    try:
        credentials = Credentials.from_service_account_info(
            config['google_docs'],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets"
            ]
        )
        gclient = gspread.authorize(credentials)
        spreadsheet = gclient.open_by_key(config['helpline_tweets_doc_key'])
        sheet_number = config.get('sheet_number', 0)
        worksheet = spreadsheet.get_worksheet(sheet_number)
        values_list = worksheet.col_values(1)
    except gspread.SpreadsheetNotFound:
        logger.error('Unable to open HelpLine tweets spreadsheet')
        return
    except KeyError:
        logger.error('Missing required key in config file')

    # Get the individual tweets from the file
    tweets = []
    for item in values_list:
        tweet = item.rstrip()
        if len(tweet) > 280:
            logger.error(u'Tweet is too long: {}'.format(repr(tweet)))
            continue
        if not tweet:
            continue
        tweets.append(tweet)

    # Tweet the articles
    logger.info(f'Sending {len(tweets)} new tweets')
    wait_time = config['tweet_shift'] / len(tweets)
    counter = 0
    wait = True
    for tweet in tweets:
        if counter and wait:
            logger.info(f'Waiting {wait_time} seconds before sending next tweet')
            time.sleep(wait_time)
        logger.info(f'Sending tweet {counter + 1} of {len(tweets)} - Tweet contents: {tweet}')
        if not test_mode:
            wait = send_tweet(config["bluesky"]["handle"], access_token, tweet)
        else:
            wait = False
        counter += 1


def send_tweet(bluesky_handle, access_token, tweet):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    post = {
        "$type": "app.bsky.feed.post",
        "text": tweet,
        "createdAt": now,
    }

    # Send the request
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers=headers,
        json={"repo": f"{bluesky_handle}", "collection": "app.bsky.feed.post", "record": post},
    )
    logger.info(f"Tweet status code [{resp.status_code}] /  body [{resp.json()}]")
    return resp.status_code == 200


###############################################################################
# Run the script when called from the command line
###############################################################################

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-c',
                      '--config',
                      dest='config',
                      help='Configuration file for the script (Twitter credentials, etc)',
                      metavar='FILE')
    parser.add_option('-t',
                      '--test',
                      dest='test',
                      action='store_true',
                      help='Test mode: Don\'t send the tweets or wait between tweets')
    (options, args) = parser.parse_args()

    if not options.config:
        parser.error('You must specify the configuration file to use')
    if not os.path.exists(options.config):
        parser.error('Could not find specified config file')

    with open(options.config) as fp:
        send_helpline_tweets(json.load(fp), options.test)
