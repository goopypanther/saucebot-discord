#!/usr/bin/python3

# Saucebot, a Discord bot for interacting with various artwork site URLs.
#
# Current sites supported:
#    FurAffinity
#    Weasyl
#    DeviantArt
#    e621

__title__ = 'saucebot-discord'
__author__ = 'Goopypanther'
__license__ = 'GPL'
__copyright__ = 'Copyright 2017 Goopypanther'
__version__ = '0.2'

import json
import os
import re

import cfscrape
import discord
import twitter


discord_token = os.environ['DISCORD_API_KEY']
twitter_consumer_key = os.environ['TWITTER_CONSUMER_KEY']
twitter_consumer_secret = os.environ['TWITTER_CONSUMER_SECRET']
twitter_access_token_key = os.environ['TWITTER_TOKEN_KEY']
twitter_access_token_secret = os.environ['TWITTER_TOKEN_SECRET']

twitter_pattern = re.compile('twitter.com/\w+/status/(\d+)')

site_info = {
    'furaffinity': {
        'get_author_name': lambda x: x['author'],
        'get_author_icon': lambda x: x['avatar'],
        'get_image': lambda x: x['title'],
        'get_image_url': lambda x: x['image_url'],
        'rx_pattern': re.compile(r'(furaffinity\.net/view/(\d+))'),
        'url': 'https://bawk.space/fapi/submission/{}',
    },
    'weasyl': {
        'get_author_name': lambda x: x['owner'],
        'get_author_icon': lambda x: x['owner_media']['avatar'][0]['url'],
        'get_image': lambda x: x['title'],
        'get_image_url':
            lambda x: x['media']['submission'][0]['links']['cover'][0]['url'],
        'rx_pattern': re.compile(r'weasyl\.com/~\w+/submissions/(\d+)'),
        'url': 'https://www.weasyl.com/api/submissions/{}/view',
        'headers': {'X-Weasyl-API-Key': os.environ['WEASYL_API_KEY']},
    },
    'weasyl_char': {
        'get_author_name': lambda x: x['owner'],
        'get_author_icon': lambda x: x['owner_media']['avatar'][0]['url'],
        'get_image': lambda x: x['title'],
        'get_image_url':
            lambda x: x['media']['submission'][0]['links']['cover'][0]['url'],
        'rx_pattern': re.compile('weasyl\.com/character/(\d+)'),
        'url': 'https://www.weasyl.com/api/characters/{}/view',
        'headers': {'X-Weasyl-API-Key': os.environ['WEASYL_API_KEY']},
    },
    'deviantart': {
        'get_author_name': lambda x: x['author_name'],
        'get_author_icon': lambda x: x.Empty,
        'get_image': lambda x: x['title'],
        'get_image_url': lambda x: x['url'],
        'rx_pattern': re.compile(r'deviantart\.com.*.\d'),
        'url': 'https://backend.deviantart.com/oembed?url={}',
    },
    'e621': {
        'get_image': lambda x: x['artist'][0],
        'get_image_url': lambda x: x['file_url'],
        'rx_pattern': re.compile(r'e621\.net/post/show/(\d+)'),
        'url': 'https://e621.net/post/show.json?id={}',
        'no_author': True,
    },
}

client = discord.Client()
scraper = cfscrape.create_scraper()
twitter_api = twitter.Api(
    consumer_key=twitter_consumer_key,
    onsumer_secret=twitter_consumer_secret,
    access_token_key=twitter_access_token_key,
    access_token_secret=twitter_access_token_secret
)


def api_print(message, content):
    print(
        '{}#{}@{}:{}: {}'.format(
            message.author.name, message.author.discriminator,
            message.server.name, message.channel.name, content
        )
    )


@client.event
async def on_message(message):
    # We do not want the bot to reply to itself
    if message.author == client.user:
        return

    # Not as easy to integrate Twitter API with current form
    twitter_links = twitter_pattern.findall(message.content)
    tweet_media = ''

    # Process each twitter link
    for tweet in twitter_links:
        # Request tweet
        tweet_status = twitter_api.GetStatus(tweet)

        # Check for success from API
        if not tweet_status:
            continue

        # Get media links in tweet
        for media_num, media_item in enumerate(tweet_status.media):
            # Check if media is an image and not first image (disp. by embed)
            if (media_item.type == 'photo') and (media_num > 0):
                tweet_media += media_item.media_url_https + ' \n '

            # Disabling video feature since it can be played in the embed
            # Can there be multiple videos per tweet?
            # elif (media_item.type == 'video'):
            #    tweet_media += media_item.video_info['variants'][0]['url']

    # Check if any non-displayed media was found in any tweets in msg
    if len(tweet_media) > 0:
        api_print(message, tweet_media)

        await client.send_message(message.channel, tweet_media)

    for site, info in site_info.items():
        links = info['rx_pattern'].findall(message.content)

        for link, site_id in links:
            # Request submission info
            if 'headers' in info:
                resp = scraper.get(
                    info['url'].format(site_id), headers=info['headers']
                )
            else:
                resp = scraper.get(info['url'].format(site_id))

            # Ignore if get from API fails
            if not resp:
                continue

            api = json.loads(resp.text)
            api_print(message, info['get_image_url'](api))

            em = discord.Embed(title=info['get_image'](api))

            em.set_image(url=info['get_image_url'](api))

            if 'no_author' not in info:
                em.set_author(
                    name=info['get_author_name'](api),
                    icon_url=info['get_author_icon'](api)
                )

            await client.send_message(message.channel, embed=em)


@client.event
async def on_ready():
    print(f'Logged in as: {client.user.name} ({client.user.id})')
    print('------')


client.run(discord_token)
