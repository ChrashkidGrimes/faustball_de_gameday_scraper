#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat March 21 2021

@author: Tobias
"""
from __future__ import print_function
# Imports for json and getting websites
import json
import requests
# custom modules (place in same folder as this script!)
import settings
from modules import getSeason, getMatches

if __name__ == '__main__':
    responseTeamsClub = requests.get(f"{settings.api}/club/{settings.clubID}/teams")
    teams = json.loads(responseTeamsClub.text)
    seasonIDs = getSeason()
    for season in seasonIDs:
        for team in teams:
            getMatches(team['id'], season)