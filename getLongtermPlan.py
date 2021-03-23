#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun March 21 2021

@author: Tobias
"""
from __future__ import print_function

# saison setzen und dann durchcyclen pro spieltag ähnlich wie https://towardsdatascience.com/xpath-for-python-89f4423415e0

# import libraries
import pandas as pd

# custom modules (place in same folder as this script!)
from modules import getFrameDates
import settings

"""
teams irgendiwe auslesen aus https://www.faustball.de/#/club/313/teams
und mit diesen dann in das array rein  sonst zu viel
Problem sind zu viele Teams die nicht aktiv sind, also doch eher eingbaut was man hat in settings.our_leagues
dann aber noch schöner machen
"""

if __name__ == '__main__':
    getFrameDates()

#TODO: [FISTCRAWL-3] create table overview for all teams of a club  
# save to pandas dataframe
#df = pd.DataFrame(date_values)
#print(df)

# write to csv
#df.to_csv('asdaYogurtLinkHeadless.csv')



#####
# git ändern da noch na github gepushed wird!
# git clone https://fistball-gameday-crawler-admin@bitbucket.org/fistball-gameday-crawler/faustball_de_gameday_scraper.git
####