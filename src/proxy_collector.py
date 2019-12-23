# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from proxyscrape import create_collector
from proxyscrape import get_collector

collector = create_collector('list-collector', 'https')

def get_proxy_list():
	collector = get_collector('list-collector')
	proxie_collection = collector.get_proxies({'anonymous': True})
	return list(i.host + ':' + i.port for i in proxie_collection)
