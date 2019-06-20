import os, pickle, re, time

from selenium.webdriver import Chrome
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

path = "."


class Scraper_BetfairSportsbook:
    clean = lambda _, array: [x.strip().translate({'\n': ''}) for x in array]
    
    patternA = re.compile("section-header-label[^<]*En Juego[^<]*</span>",
                          flags = re.DOTALL)
    patternB = re.compile("section-header-label[^<]*Hoy[^<]*</span>",
                          flags = re.DOTALL)
    patternC = re.compile("section-header-label[^<]*Próximamente[^<]*</span>",
                          flags = re.DOTALL)
    patternD = re.compile("section-header-label.[^<]*Mañana[^<]*</span>",
                          flags = re.DOTALL)

    pattern1 = re.compile("team-name[^<]*>([^<]*)</span>",
                          flags = re.DOTALL)
    pattern2 = re.compile("ui-time[^<]*format[^<]*>([^<′]*)′?</span>",
                          flags = re.DOTALL)
    pattern3 = re.compile("ui-status-format[^<]*>(\w\d)[^<′]*</span>",
                          flags = re.DOTALL)
    pattern4 = re.compile("ui-score-home[^<]*>([^<]*)</span>",
                          flags = re.DOTALL)
    pattern5 = re.compile("ui-score-away[^<]*>([^<]*)</span>",
                          flags = re.DOTALL)
    pattern6 = re.compile("sel-0.*?ui-runner-price[^<]*>([^<]*)</span>",
                          flags = re.DOTALL)
    pattern7 = re.compile("sel-1.*?ui-runner-price[^<]*>([^<]*)</span>",
                          flags = re.DOTALL)
    pattern8 = re.compile("sel-2.*?ui-runner-price[^<]*>([^<]*)</span>",
                          flags = re.DOTALL)

    def __init__(self):
        """Initializes a headless Chrome session for scraping purposes,
        and ensures that there are the necessary structures to hold the
        data, as well as a datafile in which to write the results of the
        session once it has ended."""

        # Browser.        
        chrome_options = Options()
        chrome_options.headless = True
        
        self.browser = Chrome(options = chrome_options)

        # Data storage.
        self.data = {}
        self.datafile = {}

        for sport in ('soccer',):#, 'tennis', 'basket'):
            if f"{sport}_data.dat" in os.listdir(path):
                with open(path + f"\\{sport}_data.dat", 'rb') as datafile:
                    self.data[sport] = pickle.load(datafile)
            else:
                self.data[sport] = {}

            self.datafile[sport] = open(path + f"\\{sport}_data.dat", 'wb')

    def close(self):
        """Makes sure the browser and every open file is properly closed."""
        self.browser.quit()
        for sport in ('soccer',):# 'tennis', 'basket'):
            pickle.dump(self.data[sport], self.datafile[sport])
            self.datafile[sport].close()

    #--------------------------
    # Scraping
    #--------------------------
    def start(self):
        """The scraping is done from 11 AM to 11 PM, non-stop."""

        START_TIME, CLOSING_TIME = 11, 23
        first_time = True

        while True:
            self.now = time.localtime()
            
            if self.now.tm_hour >= CLOSING_TIME and self.now.tm_min >= 50:
                print("Finished")
                return
            
            elif self.now.tm_hour >= START_TIME:
                if first_time:
                    urls = {'soccer': "https://www.betfair.es/sport/football"}
                            #'tennis': "https://www.betfair.es/sport/tennis",
                            #'basket': "https://www.betfair.es/sport/basketball"}

                    first_time = False
                    print("Starting opening pages...")
                    for sport, url in urls.items():
                        self.browser.execute_script("window.open('');")
                        tab = self.browser.window_handles[-1]
                        self.browser.switch_to.window(tab)
                        self.browser.get(url)
                        print(url)

                    tab = self.browser.window_handles[0]
                    self.browser.switch_to.window(tab)
                    self.browser.execute_script("window.close();")
                    print("Scraping in progress...")
                
                self.gather(urls)

            time.sleep(20)

    def gather(self, urls):
        """The process of scraping/gathering the data from the Betfair
        Sportsbook specified sports sections."""

        # For each sport...
        for i, sport in enumerate(urls):
            
            # We change to its corresponding tab, and get the HTML.
            tab = self.browser.window_handles[i]
            self.browser.switch_to.window(tab)
            html = self.browser.page_source

            # We restrict ourselves to the part of the html file we need.
            try:
                sect_start = self.patternA.search(html).start()
                sect_end   = [pat.search(html) for pat in (self.patternB,
                                                           self.patternC,
                                                           self.patternD)]
                for result in sect_end:
                    if result is not None:
                        sect_end = result.start()
                        break

                html = html[sect_start : sect_end]
                
            except Exception:
                continue

            # Then, we extract the raw data from all games/matches that have
            # gone in play, and store it.
            names = self.clean(self.pattern1.findall(html))
            start, stop = 0, 0

            for i in range(len(names) // 2):
                start = stop
                stop  = html.rfind(names[2*i + 1])
                part  = html[start : stop]

                # Skip unavailable games/matches.
                if ('Suspendido' in part) or ('Cerrado' in part):
                    continue
                
                # Otherwise, try to extract all the needed information.
                # If something is amiss, skip that game/match.
                try:
                    odds  = []

                    if sport == 'soccer':
                        timestamp  = self.clean(self.pattern2.findall(part))[0]
                        home_score = self.clean(self.pattern4.findall(part))[0]
                        away_score = self.clean(self.pattern5.findall(part))[0]
                        score = (int(home_score), int(away_score))
                        # ~~( Odds )~~
                        odds_sect  = self.clean(self.pattern6.findall(part))[0]
                        part = part[part.find("market-3-runners") : ]
                        odds.append(self.clean(self.pattern6.findall(part))[0])
                        odds.append(self.clean(self.pattern7.findall(part))[0])
                        odds.append(self.clean(self.pattern8.findall(part))[0])

                    elif sport == 'tennis':
                        timestamp = "%02d:%02d" % (self.now.tm_hour,
                                                   self.now.tm_min)
                        score = None
                        # ~~( Odds )~~
                        odds.append(self.clean(self.pattern6.findall(part))[0])
                        odds.append(self.clean(self.pattern7.findall(part))[0])
                        
                    elif (sport == 'basket'):
                        timestamp  = self.clean(self.pattern2.findall(part))[0]
                        quarter    = self.clean(self.pattern3.findall(part))[0]
                        timestamp  = " ".join((quarter, timestamp))
                        home_score = self.clean(self.pattern4.findall(part))[0]
                        away_score = self.clean(self.pattern5.findall(part))[0]
                        score = (int(home_score), int(away_score))
                        # ~~( Odds )~~
                        odds.append(self.clean(self.pattern6.findall(part))[-1])
                        odds.append(self.clean(self.pattern7.findall(part))[-1])
                    
                except:
                    continue

                # --- Title ---
                title  = " VS ".join((names[2*i], names[2*i + 1]))
                title += " %02d/%02d/%d" % (self.now.tm_mday,
                                            self.now.tm_mon,
                                            self.now.tm_year)
                # --- Odds ---
                if all(x == '' for x in odds):
                    continue
                else:
                    for j in range(len(odds)):
                        try:
                            odds[j] = float(odds[j])
                        except Exception:
                            odds[j] = 1.0

                # How big?
                somethings_wrong = ''

                if sport == 'soccer':
                    print(len(self.data['soccer']))

                # *** Storing the data ***
                info = {'score': score, 'odds': odds}
                
                if title not in self.data[sport]:
                    self.data[sport][title] = {timestamp: info}
                else:
                    if timestamp not in self.data[sport][title]:
                        self.data[sport][title][timestamp] = info

#==============================
# Run on execution
#==============================
if __name__ == "__main__":
    scraper = Scraper_BetfairSportsbook()
    scraper.start()
    scraper.close()
