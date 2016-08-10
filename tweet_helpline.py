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

Use the -t / --tweets option to specify a list of tweets to send.  The file
should be a UTF-8 text file with one tweet per line.

The script will send each of the tweets in the provided tweets file and with a
wait between tweets.  The wait will be based on the configured tweet_shift
(in seconds) divided by the number of tweets to send.  The default tweet_shift
is 14400 seconds (4 hours).

*******************************************************************************
"""
import codecs
import json
import logging
import os
import time
import tweepy
from optparse import OptionParser

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_helpline_tweets(config, tweets_file):
    # Log into the Twitter account
    logger.info('Logging into Twitter account')
    auth = tweepy.OAuthHandler(config['twitter']['consumer_key'],
                               config['twitter']['consumer_secret'])
    auth.set_access_token(config['twitter']['access_token'],
                          config['twitter']['access_token_secret'])
    twitter_api = tweepy.API(auth)

    # Get the individual tweets from the file
    tweets = []
    with codecs.open(tweets_file, 'r', 'utf8') as infile:
        for line in infile:
            tweet = line.rstrip()
            if len(tweet) > 140:
                logger.error(u'Tweet is too long: {}'.format(repr(tweet)))
                continue
            if not tweet:
                continue
            tweets.append(tweet)

    # Tweet the articles
    logger.info(u'Sending {} new tweets'.format(len(tweets)))
    wait_time = config['tweet_shift'] / len(tweets)
    counter = 0
    wait = True
    for tweet in tweets:
        if counter and wait:
            logger.info(u'Waiting {} seconds before sending next tweet'.format(wait_time))
            time.sleep(wait_time)
        logger.info(u'Sending tweet {} of {} - Tweet contents: {}'.format(counter + 1,
                                                                          len(tweets),
                                                                          tweet))
        wait = send_tweet(twitter_api, tweet)
        counter += 1


def send_tweet(twitter_api, tweet):
    try:
        twitter_api.update_status(tweet)
        return True
    except tweepy.error.TweepError as e:
        logger.error(u'Error sending tweet')
        for i in range(0, len(e.message)):
            error = e.message[i]
            logger.error(u'Error {} - Code: {} - Message: {}'.format(i + 1,
                                                                     error['code'],
                                                                     error['message']))


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
                      '--tweets',
                      dest='tweets',
                      help='The text file containing the helpline tweets',
                      metavar='FILE')
    (options, args) = parser.parse_args()

    if not options.config:
        parser.error('You must specify the configuration file to use')
    if not os.path.exists(options.config):
        parser.error('Could not find specified config file')
    if not options.tweets:
        parser.error('You must specify the file containing the helpline tweets')
    if not os.path.exists(options.tweets):
        parser.error('Could not find specified helpline tweets file')

    with open(options.config) as fp:
        send_helpline_tweets(json.load(fp), options.tweets)
