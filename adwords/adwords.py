# -*- coding: utf-8 -*-
"""
Python API for Google AdWords
"""

from __future__ import unicode_literals

import googleads
import config
import csv

from collections import defaultdict
from log import logging


class Base(object):
    """ Base class from which most other classes are derived """

    def __repr__(self):
        repr = "{0}('{1}')".format(self.__class__.__name__, self.name)
        return repr.encode('utf-8')

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf-8')


class Label(Base):
    """ AdWords label """

    def __init__(self, label):
        self.id = label['id']
        self.name = label['name']


class Client(object):
    """ AdWords client """

    def __init__(self, client_customer_id=None, version='v201705'):
        self.client = googleads.adwords.AdWordsClient.LoadFromStorage()
        self.downloader = self.client.GetReportDownloader()
        self.dynamic_params = defaultdict(dict)
        self.version = version

        # Client customer ID, if needed, can be obtained either from
        # credentials storage or set explicitly when creating new object
        if client_customer_id is not None:
            self.client.SetClientCustomerId(client_customer_id)

    def service(self, name):
        """ Return AdWords service by name """
        return self.client.GetService(name, self.version)

    def campaigns(self, labels=[]):
        """
        Return campaigns for the account. If `labels' is given, filter only
        those which contain at least one of the provided labels, otherwise
        return all campaigns.
        """
        service = self.service('CampaignService')
        selector = {
            'fields': ['Id', 'Name'],
            'predicates': [
                {
                    'field': 'Status',
                    'operator': 'EQUALS',
                    'values': ['ENABLED'],
                },
            ],
        }

        if labels:
            selector['predicates'] += {
                'field': 'Labels',
                'operator': 'CONTAINS_ANY',
                'values': [label.id for label in labels],
            }

        response = service.get(selector)
        try:
            campaigns = [
                Campaign(client=self, id=entry.id, name=entry.name)
                for entry in response.entries
            ]
        except AttributeError:
            campaigns = []

        return campaigns

    def ad_groups(self, labels=[]):
        """
        Return ad groups for the account. If `labels' is given, filter only
        those which contain at least one of the provided labels, otherwise
        return all ad groups.
        """
        service = self.service('AdGroupService')
        selector = {
            'fields': ['Id', 'Name', 'CampaignId', 'CampaignName'],
            'predicates': [
                {
                    'field': 'Labels',
                    'operator': 'CONTAINS_ANY',
                    'values': [label.id for label in labels],
                },
                {
                    'field': 'Status',
                    'operator': 'EQUALS',
                    'values': ['ENABLED'],
                },
            ]
        }

        response = service.get(selector)

        try:
            ad_groups = [
                AdGroup(
                    client = self,
                    id = entry.id,
                    name = entry.name,
                    campaign = Campaign(
                        client = self,
                        id = entry.campaignId,
                        name = entry.campaignName,
                    ),
                )
                for entry in response.entries
            ]
        except AttributeError:
            ad_groups = []

        return ad_groups

    def labels(self, label_names):
        """ Return label objects based on names """
        service = self.service('LabelService')
        selector = {
            'fields': ['LabelId', 'LabelName'],
            'predicates': {
                'field': 'LabelName',
                'operator': 'IN',
                'values': label_names,
            }
        }

        response = service.get(selector)
        labels = [Label(entry) for entry in response.entries]

        return labels

    def upload_dynamic_params(self):
        """ Upload dynamic ad parameters to AdWords """
        # Return if there is nothing to upload
        if not self.dynamic_params:
            return

        # Find ad customizer feed by name
        service = self.service('AdCustomizerFeedService')

        selector = {
            'fields': ['FeedId', 'FeedStatus', 'FeedAttributes'],
            'predicates': [
                {
                    'field': 'FeedName',
                    'operator': 'EQUALS',
                    'values': config.AD_CUSTOMIZER_FEED,
                },
                {
                    'field': 'FeedStatus',
                    'operator': 'EQUALS',
                    'values': 'ENABLED',
                },
            ],
        }

        response = service.get(selector)

        feed = response.entries[0]
        feed_id = feed.feedId
        attribute_ids = {
            attribute.name: attribute.id for attribute in feed.feedAttributes
        }

        # Find all dynamic parameters for ad groups that are being updated
        service = self.service('FeedItemService')

        selector = {
            'fields': ['FeedItemId'],
            'predicates': [
                {
                    'field': 'FeedId',
                    'operator': 'EQUALS',
                    'values': feed_id,
                },
                {
                    'field': 'TargetingAdGroupId',
                    'operator': 'IN',
                    'values': self.dynamic_params.keys(),
                },
                {
                    'field': 'Status',
                    'operator': 'EQUALS',
                    'values': 'ENABLED',
                },
            ],
        }

        response = service.get(selector)

        # Remove any parameters before uploading new values
        if 'entries' in response:
            feed_item_ids = [
                entry.feedItemId for entry in response.entries
            ]

            operations = [
                {
                    'operator': 'REMOVE',
                    'operand': {
                        'feedId': feed_id,
                        'feedItemId': feed_item_id,
                    },
                }
                for feed_item_id in feed_item_ids
            ]

            service.mutate(operations)

        # Upload fresh values to the feed
        operations = [
            {
                'operator': 'ADD',
                'operand': {
                    'feedId': feed_id,
                    'adGroupTargeting': {
                        'TargetingAdGroupId': ad_group_id,
                    },
                    'attributeValues': [
                        {
                            'feedAttributeId': attribute_ids[param],
                            'stringValue':
                                self.dynamic_params[ad_group_id][param],
                        }
                        for param in self.dynamic_params[ad_group_id]
                    ],
                }
            }
            for ad_group_id in self.dynamic_params
        ]

        service.mutate(operations)


class Campaign(Base):
    """ AdWords campaign """

    def __init__(self, client, id=None, name=None):
        self.client = client
        self.id = id
        self.name = name

        self._dsa = None
        self._ad_groups = None

    @property
    def dsa(self):
        """ Check if campaign is a Dynamic Search Ad campaign """
        if self._dsa is None:
            service = self.client.service('CampaignService')

            selector = {
                'fields': ['Settings'],
                'predicates': [
                    {
                        'field': 'Status',
                        'operator': 'EQUALS',
                        'values': ['ENABLED'],
                    },
                    {
                        'field': 'CampaignId',
                        'operator': 'EQUALS',
                        'values': [self.id],
                    },
                ],
            }

            settings = service.get(selector)
            setting_types = [
                setting['Setting.Type']
                for setting in settings.entries[0].settings
                if 'Setting.Type' in setting
            ]

            self._dsa = 'DynamicSearchAdsSetting' in setting_types

        return self._dsa

    @property
    def ad_groups(self):
        """ Return all ad groups in the campaign """
        if self._ad_groups is None:
            service = self.client.service('AdGroupService')

            selector = {
                'fields': ['Id', 'Name'],
                'predicates': [
                    {
                        'field': 'Status',
                        'operator': 'EQUALS',
                        'values': ['ENABLED'],
                    },
                    {
                        'field': 'CampaignId',
                        'operator': 'EQUALS',
                        'values': [self.id],
                    },
                ],
            }

            ad_groups = service.get(selector)

            self._ad_groups = [
                AdGroup(
                    self.client, id=entry.id, name=entry.name, campaign=self
                ) for entry in ad_groups.entries
            ]

        return self._ad_groups


class AdGroup(Base):
    """ AdWords ad group """

    def __init__(self, client, id=None, name=None, campaign=None):
        self.client = client

        self.id = id
        self.name = name
        self._campaign = campaign

        self._ads = None
        self._urls = None
        self._url = None
        self._top_keyword = None
        self._keywords = None

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

    @property
    def campaign(self):
        """ Return campaign to which the ad group belongs """
        if self._campaign is None:
            service = self.client.service('AdGroupService')

            selector = {
                'fields': ['CampaignId', 'CampaignName'],
                'predicates': [
                    {
                        'field': 'AdGroupId',
                        'operator': 'EQUALS',
                        'values': [self.id],
                    },
                ],
            }

            campaign = service.get(selector)

            self._campaign = next([
                Campaign(
                    self.client, id=entry.campaignId, name=entry.campaignName
                ) for entry in campaign.entries
            ])

        return self._campaign

    @property
    def ads(self):
        """ Return all ads in the ad group """
        if self._ads is None:
            service = self.client.service('AdGroupAdService')

            selector = {
                'fields': [
                    'Id', 'HeadlinePart1', 'HeadlinePart2', 'Description',
                    'Path1', 'Path2', 'CreativeFinalUrls', 'Labels',
                ],
                'predicates': [
                    {
                        'field': 'AdGroupId',
                        'operator': 'EQUALS',
                        'values': [self.id],
                    },
                ],
            }

            ads = service.get(selector)

            expanded_text_ads = [
                ExpandedTextAd(
                    entry['ad'],
                    labels=map(Label, dict(entry).get('labels', [])),
                )
                for entry in dict(ads).get('entries', [])
                if entry['ad']['Ad.Type'] == 'ExpandedTextAd'
            ]

            dynamic_search_ads = [
                DynamicSearchAd(
                    entry['ad'],
                    map(Label, dict(entry).get('labels', [])),
                )
                for entry in dict(ads).get('entries', [])
                if entry['ad']['Ad.Type'] == 'DynamicSearchAd'
            ]

            self._ads = expanded_text_ads + dynamic_search_ads

        return self._ads

    @property
    def urls(self):
        """
        Return target URLs of all ads in the ad group
        """
        if self._urls is None:
            service = self.client.service('AdGroupAdService')

            selector = {
                'fields': ['CreativeFinalUrls'],
                'predicates': [
                    {
                        'field': 'AdGroupId',
                        'operator': 'EQUALS',
                        'values': [self.id],
                    },
                    {
                        'field': 'Status',
                        'operator': 'EQUALS',
                        'values': ['ENABLED'],
                    },
                ],
            }

            ads = service.get(selector)

            self._urls = [
                url for ad in dict(ads).get('entries', [])
                for url in dict(ad.ad).get('finalUrls', [])
            ]

        return self._urls

    @property
    def top_keyword(self):
        """
        Return keyword with most impressions in the ad group. If more keywords
        are tied, only one of them is returned.
        """
        return self.keywords[0] if self.keywords else None

    @property
    def keywords(self):
        """
        Return all keywords in the ad group sorted by impressions for the last
        30 days
        """
        if self._keywords is None:
            report = {
                'reportName': 'Today KEYWORDS_PERFORMACE_REPORT',
                'dateRangeType': 'LAST_30_DAYS',
                'reportType': 'KEYWORDS_PERFORMANCE_REPORT',
                'downloadFormat': 'CSV',
                'selector': {
                    'fields': ['Criteria', 'Impressions'],
                    'predicates': [
                        {
                            'field': 'Status',
                            'operator': 'EQUALS',
                            'values': ['ENABLED'],
                        },
                        {
                            'field': 'AdGroupId',
                            'operator': 'EQUALS',
                            'values': [self.id],
                        },
                    ],
                },
            }

            keywords_csv = self.client.downloader.DownloadReportAsString(
                report, skip_report_header=True, skip_column_header=True,
                skip_report_summary=True, include_zero_impressions=True,
            )
            keywords_csv = keywords_csv.encode('utf-8').splitlines()

            keyword_reader = csv.reader(keywords_csv)

            keywords_impressions = sorted(
                keyword_reader, key=lambda x: int(x[1]), reverse=True
            )

            self._keywords = [
                keyword for keyword, _ in keywords_impressions
            ]

        return self._keywords

    def upload_ad(self, ad):
        """ Upload new ad to the ad group """
        service = self.client.service('AdGroupAdService')

        if isinstance(ad, ExpandedTextAd):
            ad_fields = {
                'xsi_type': 'ExpandedTextAd',
                'headlinePart1': ad.headlinePart1,
                'headlinePart2': ad.headlinePart2,
                'description': ad.description,
                'path1': ad.path1,
                'path2': ad.path2,
                'finalUrls': [ad.url],
            }
        elif isinstance(ad, DynamicSearchAd):
            ad_fields = {
                'xsi_type': 'DynamicSearchAd',
                'description1': ad.description1,
                'description2': ad.description2,
                'displayUrl': ad.displayUrl,
            }
        else:
            logging.error('Unrecognized ad type, skipping')
            return None

        operations = [
            {
                'operator': 'ADD',
                'operand': {
                    'xsi_type': 'AdGroupAd',
                    'adGroupId': self.id,
                    'ad': ad_fields,
                    'status': 'PAUSED',
                },
            },
        ]

        service.mutate(operations)


class Ad(object):
    """ Base class for all ad types """

    def __init__(self, *args, **kwargs):
        """
        Create Ad object from parameters. They can be passed either as a
        dictionary in the first argument or separately as named arguments.
        """
        try:
            self._dict = dict(args[0])
        except IndexError:
            self._dict = kwargs

        self.labels = self._dict.get('labels', [])


class ExpandedTextAd(Ad):
    """ Expanded Text Ad """

    def __init__(self, *args, **kwargs):
        """
        Create ExpandedTextAd object from parameters. They can be passed either
        as a dictionary in the first argument or separately as named arguments.
        """
        super(self.__class__, self).__init__(*args, **kwargs)

        self.headlinePart1 = self._dict.get('headlinePart1', '')
        self.headlinePart2 = self._dict.get('headlinePart2', '')
        self.description = self._dict.get('description', '')
        self.path1 = self._dict.get('path1', '')
        self.path2 = self._dict.get('path2', '')
        self.finalUrls = self._dict.get('finalUrls', [])

        self.url = self.finalUrls[0] if self.finalUrls else ''

    def __eq__(self, other):
        return all([
            self.headlinePart1 == other.headlinePart1,
            self.headlinePart2 == other.headlinePart2,
            self.description == other.description,
            self.path1 == other.path1,
            self.path2 == other.path2,
            self.url == other.url,
        ])

    def __unicode__(self):
        return '{0}\n{1} - {2}\n{3}{4}{5}\n{6}'.format(
            self.url, self.headlinePart1, self.headlinePart2, config.HOST_NAME,
            '/' + self.path1 if self.path1 else '',
            '/' + self.path2 if self.path2 else '',
            self.description)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def valid(self):
        """ Check that no field exceeds its allowed length limit """
        return all([
            len(headlinePart1) <= config.HEADLINE_PART1_LIMIT,
            len(headlinePart2) <= config.HEADLINE_PART2_LIMIT,
            len(description) <= config.DESCRIPTION_LIMIT,
            len(self.path1) <= config.PATH1_LIMIT,
            len(self.path2) <= config.PATH2_LIMIT,
        ])


class DynamicSearchAd(Ad):
    """ Dynamic Search Ad """

    def __init__(self, ad, labels=[]):
        """
        Create DynamicSearchAd object from parameters. They can be passed
        either as a dictionary in the first argument or separately as named
        arguments.
        """
        super(self.__class__, self).__init__(*args, **kwargs)

        self.description1 = self._dict['description1']
        self.description2 = self._dict['description2']
        self.displayUrl = self._dict['displayUrl']

    def __unicode__(self):
        return '{{Dynamically generated headline}}\n{0}\n{1}'.format(
            self.description1, self.description2)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def valid(self):
        """ Check that no field exceeds its allowed length limit """
        return all([
            len(self.description1) <= config.DSA_DESCRIPTION_LIMIT,
            len(self.description2) <= config.DSA_DESCRIPTION_LIMIT,
        ])
