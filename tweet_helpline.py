# -*- coding: latin-1 -*-
"""
*******************************************************************************
** Script Name: tweet_helpline.py
** Author(s):   Terrence Beach (tjbeachjr@gmail.com)
*******************************************************************************

** Description:

The script will take the tweets stored helpline tweets resource file and send
them at a specified interval.

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
            tweets.append(tweet)

    # Tweet the articles
    logger.info('Sending {} new tweets'.format(len(tweets)))
    wait_time = config['tweet_shift'] / len(tweets)
    counter = 0
    for tweet in tweets:
        if counter:
            logger.info('Waiting {} seconds before sending next tweet'.format(wait_time))
            time.sleep(wait_time)
        logger.info('Sending tweet {} of {} - Tweet contents: {}'.format(counter + 1,
                                                                         len(tweets),
                                                                         tweet))
        send_tweet(twitter_api, tweet)
        counter += 1


def send_tweet(twitter_api, tweet, retry=0):
    if retry > 9:
        logger.error('Maximum number of retries reached!')
        return
    try:
        twitter_api.update_status(tweet)
        return
    except:
        logger.error('Problem sending tweet. Retrying (Retry = {})...'.format(retry + 1))
        time.sleep(5.0)
        send_tweet(twitter_api, tweet, retry + 1)
        retry += 1


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
        config = json.load(fp)

    send_helpline_tweets(config, options.tweets)
