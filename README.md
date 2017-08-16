# adwords

Python API for Google AdWords

## Prerequisites

This package provides a Google AdWords API for Python 2.7. In order to be able to use it, make sure you have Python 2.7 installed on your machine. Additionally, `pip` package manager is recommended for easy, pain-free installation.

On Red Hat-based Linux distros (Fedora, Red Hat Enterprise Linux, CentOS, Scientific Linux), run:

```
dnf install python python-pip
```

On Debian-based distros (Debian, Ubuntu), run:

```
apt-get install python python-pip
```

## Installation

The recommended and most straightforward way to install the package is from [PyPI](https://pypi.python.org/pypi/adwords). 

```
pip install adwords
```

## Credentials

Before you start using `adwords` package, you will need to [create your credentials]((https://github.com/googleads/googleads-python-lib/wiki/API-access-using-own-credentials-(installed-application-flow))) first.

Once you have the credentials ready, create file `googleads.yaml` in your home directory with the following structure:

```yaml
adwords:
  developer_token: INSERT_DEVELOPER_TOKEN_HERE
  client_id: INSERT_OAUTH_2_CLIENT_ID_HERE
  client_secret: INSERT_CLIENT_SECRET_HERE
  refresh_token: INSERT_REFRESH_TOKEN_HERE
```

## Example usage

This very simple example shows how to browse your campaign structure with `adwords`:

```pycon
>>> import adwords
>>> client = adwords.Client()
>>> client
<adwords.adwords.Client object at 0x7fe2d958bb90>
>>> campaigns = client.campaigns()
>>> campaigns
[Campaign('A Campaign of Ice and Fire')]
>>> ad_groups = campaigns[0].ad_groups()
>>> ad_groups
[AdGroup('Lannister'), AdGroup('Stark')]
>>> ads = ad_groups[0].ads
>>> ads
[<adwords.adwords.ExpandedTextAd object at 0x7fe2c9783650>, <adwords.adwords.ExpandedTextAd object at 0x7fe2c97836d0>, <adwords.adwords.ExpandedTextAd object at 0x7fe2c9783350>]
>>> print ads[0]
Lannister Investment Group - Hear Me Roar => https://lannister.com/
www.lannister.com/hear-me-roar
Guarding you wealth since the Age of Heroes.
```

## Author
[Martin Frodl](https://github.com/mfrodl)
