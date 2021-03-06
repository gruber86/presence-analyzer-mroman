# -*- coding: utf-8 -*-
"""
Helper functions used in views.
"""

import csv

from json import dumps

from functools import wraps

from datetime import datetime

from lxml import etree

from flask import Response

from presence_analyzer.main import app

import urllib

import threading

import logging

import time

log = logging.getLogger(__name__)  # pylint: disable-msg=C0103


def jsonify(function):
    """
    Creates a response with the JSON representation of wrapped function result.
    """
    @wraps(function)
    def inner(*args, **kwargs):
        return Response(dumps(function(*args, **kwargs)),
                        mimetype='application/json')
    return inner


def cache(time_in_sek):
    """
    Cache for CSV file
    """
    def inner_cache(function):
        lock = threading.Lock()
        function.inner_cache = {}
        @wraps(function)
        def decorator(*args, **kwargs):
            key = repr(args) + repr(kwargs)
            with lock:
                if key in function.inner_cache:
                    time_result = time.time() - function.inner_cache['time']
                    if time_result < time_in_sek:
                        return function.inner_cache[key]
                result = function(*args, **kwargs)
                function.inner_cache[key] = result
                function.inner_cache['time'] = time.time()
                return result

        return decorator
    return inner_cache


@cache(600)
def get_data():
    """
    Extracts presence data from CSV file and groups it by user_id.

    It creates structure like this:
    data = {
        'user_id': {
            datetime.date(2013, 10, 1): {
                'start': datetime.time(9, 0, 0),
                'end': datetime.time(17, 30, 0),
            },
            datetime.date(2013, 10, 2): {
                'start': datetime.time(8, 30, 0),
                'end': datetime.time(16, 45, 0),
            },
        }
    }
    """
    data = {}
    with open(app.config['DATA_CSV'], 'r') as csvfile:
        presence_reader = csv.reader(csvfile, delimiter=',')
        for i, row in enumerate(presence_reader):
            if len(row) != 4:
                # ignore header and footer lines
                continue

            try:
                user_id = int(row[0])
                date = datetime.strptime(row[1], '%Y-%m-%d').date()
                start = datetime.strptime(row[2], '%H:%M:%S').time()
                end = datetime.strptime(row[3], '%H:%M:%S').time()
            except (ValueError, TypeError):
                log.debug('Problem with line %d: ', i, exc_info=True)

            data.setdefault(user_id, {})[date] = {'start': start, 'end': end}
    return data


def group_by_weekday(items):
    """
    Groups presence entries by weekday.
    """
    result = {i: [] for i in range(7)}
    for date in items:
        start = items[date]['start']
        end = items[date]['end']
        result[date.weekday()].append(interval(start, end))
    return result


def group_times_by_weekday(items):
    """
    Groups times presence entries by weekday.
    """
    result = {i: {'start': [], 'end': []} for i in range(7)}
    for date, times in items.items():
        result[date.weekday()]['start'].append(
            seconds_since_midnight(times['start']))
        result[date.weekday()]['end'].append(
            seconds_since_midnight(times['end']))
    return result


def seconds_since_midnight(time):
    """
    Calculates amount of seconds since midnight.
    """
    return time.hour * 3600 + time.minute * 60 + time.second


def interval(start, end):
    """
    Calculates inverval in seconds between two datetime.time objects.
    """
    return seconds_since_midnight(end) - seconds_since_midnight(start)


def mean(items):
    """
    Calculates arithmetic mean. Returns zero for empty lists.
    """
    return float(sum(items)) / len(items) if len(items) > 0 else 0


def get_data_from_xml():
    """
    Parser get data from users.xml file
    Structure:
    [{
            10: {
            'name': user_name,
            'avatar': url+avatar}
    }]
    """
    with open('runtime/data/users.xml', 'r') as xmlfile:
        tree = etree.parse(xmlfile)
        server = tree.find('./server')
        protocol = server.find('./protocol').text
        host = server.find('./host').text
        additional = '://'
        url = protocol+additional+host
        return {
            user.attrib['id']: {
                'name': user.find('./name').text,
                'avatar': url+user.find('./avatar').text}
            for user in tree.findall('./users/user')}


def download_and_write_xml():
    """
    This script download and write a xml file from url
    """
    URL = app.config['XML_URL']
    webFile = urllib.urlopen("URL")
    print "Downloading file . . . "
    localFile = open.app.config('USER_DATA_XML', 'w')
    localFile.write(webFile.read())
    webFile.close()
    localFile.close()
