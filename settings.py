# settings

# Variables
api="https://www.faustball.de/rest"
teamCategory = {1: "Männer", 2: "Frauen", 3: "Jugend", 4: "Senioren"}

# longtermplan STB
# specify the url
urlpage = 'https://www.stb.de/sportarten/faustball/spielbetrieb/' 
leagues ={"1.BL Männer": 4, "2.BL Männer": 5, "SL Männer": 6, "VL Männer": 7,"LL Männer": 8,"BZL Männer": 9,"1.BL Frauen": 10, "2.BL Frauen": 11, "SL Frauen": 12, "LL Frauen": 13,"BZL Frauen": 13,"VL M35": 14, "LL M35": 15, "M60": 16,"U18m": 17, "U18w": 18, "U16m": 19, "U16w": 20,"U14m": 21,"U14w": 21,"U12": 22,"U10": 23,"U8": 24}
""" not neccessary right now:
league_men = {"1.BL Männer": 4, "2.BL Männer": 5, "SL Männer": 6, "VL Männer": 7,"LL Männer": 8,"BZL Männer": 9}
league_women = {"1.BL Frauen": 10, "2.BL Frauen": 11, "SL Frauen": 12, "LL Frauen": 13,"BZL Frauen": 13}
league_senior = {"VL M35": 14, "LL M35": 15, "M60": 16}
league_youth = {"U18m": 17, "U18w": 18, "U16m": 19, "U16w": 20,"U14m": 21,"U14w": 21,"U12": 22,"U10": 23,"U8": 24}
"""

# club specific settings
googleCalendarId = {1: "tvwaldrennach@gmail.com", 2: "ln1o5r1pgah266sh3f5dsln9d8@group.calendar.google.com", 3: "n6bgju27vs5hv8au4i2pldte44@group.calendar.google.com", 4: "tvwaldrennach@gmail.com"}
clubID = "313"

# longtermplan STB - club specific settings
our_leagues = [leagues["1.BL Männer"],leagues["VL Männer"],leagues["LL Frauen"],leagues["VL M35"],leagues["U16m"],leagues["U10"],leagues["U8"]]