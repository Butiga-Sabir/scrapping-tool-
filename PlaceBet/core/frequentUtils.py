from scrapy import Selector

from datetime import datetime

from urllib.parse import urljoin

from .coreUtilities import PageFetchEngine


from playwright.sync_api import Playwright, sync_playwright, Page

import time

class ToolBox:
    def getTodaysDate(self, yearOnly=False):
        """
        Retrieves todays date
        """
        
        if yearOnly is False:
            return datetime.now().strftime("%A %m %Y")
        
        else:
            return str(datetime.now().year)
        

class MelBetUtils:
    def getLeagues(self, pageResponse: Selector, fetchSection: int):
        # nav.ui-nav.sports-menu-sports.sports-menu-group__sports > ul.ui-nav-items
        leaguesNavigationBar = pageResponse.css('nav.ui-nav.sports-menu-sports.sports-menu-group__sports ul.ui-nav-items')

        # print(len(leaguesNavigationBar))

        # get the league section
        # foot ball or basket
        # > li.ui-nav-item:nth-child(3) 
        # select first group that contains basket and football
        leaguesHandle = leaguesNavigationBar[0]

        # get matches handle
        # 0 - football
        # 2 - basket ball
        matchesHandle = leaguesHandle.css('li.ui-nav-item')[fetchSection]


        # get the matches 
        matchesObject = matchesHandle.css('ul.ui-nav-items li.ui-nav-item div.ui-nav-link a.ui-nav-link__content')

        # store the collected league names and their links
        leagueNameLinkMap = {}

        for eachMatchObject in matchesObject:
            # one item
            extractedLeague = eachMatchObject.css('::attr(title)').get().strip()

            extractedLink = eachMatchObject.css('::attr(href)').get()

            # print(extractedLeague)
            
            leagueNameLinkMap[extractedLeague] = urljoin("https://melbet-231489.top/en", extractedLink)

        
        # print(leagueNameLinkMap)
        
        return leagueNameLinkMap

    def getSelectedLeagueData(self, leagueMeta: dict):
        # {'KLASK': 'https://22bet.ug/line/football/2150631-klask'}
        # Goes to the url and extracts the matches for each league in the 'leagueMeta' object
        
        # collect the found matches
        foundMatches = []
        
        for eachLeague, leagueUrl in leagueMeta.items():
            # get the page data for the league
            pageData, _, _ = PageFetchEngine(
                fetchUrlTag=None,
                subPage=True,
                pageScrollCount=10,
                subUrlDetail=[leagueUrl, False, 2]
                ).getRawPage()
            
            # extract the matches
            extractedSetMatches = self.matchesExtractor(Selector(text=pageData))
            
            # dict creator
            dictResolver = lambda tupleItems: {
                eachPair[0] : eachPair[1] for eachPair in tupleItems
            }
            
            # resolve them into a list
            # { ((1, 2), (2, 4)), ((1, 5), (6, 7)) }
            extractedMatches = [
                dictResolver(eachDataObject) for eachDataObject in extractedSetMatches
            ]
            
            # store them
            foundMatches = foundMatches + extractedMatches
            
        return foundMatches
    
    
    def matchesExtractor(self, leagueResponse: Selector):
        # collect the matches
        extractedMatchDetails = set()
        
        # get the containers
        leaguesContainer = leagueResponse.css('div.layout__main main.betting-content div.betting-main.betting-content__main div.betting-dashboard div.betting-dashboard__item div.betting-main-dashboard div.ui-dashboard.dashboard ul.ui-dashboard__champs')
        
        for eachMatchHolder in leaguesContainer.css('li.ui-dashboard-champ.dashboard-champ.dashboard__champ'):
            # get the whole cell present
            leagueName = eachMatchHolder.css('div.ui-dashboard-champ__head div.ui-dashboard-champ-name.dashboard-champ__name a.ui-dashboard-champ-name__label.ui-dashboard-champ-name__link span.caption.ui-dashboard-champ-name__caption span.caption__label ::text').get()
            
            # get the games holder
            gamesHolder = eachMatchHolder.css('ul.ui-dashboard-champ__games li.ui-dashboard-game.dashboard-game')
            

            # extract the desired data
            for eachGame in gamesHolder:
                # team name handler
                teamNameHandler = lambda teamHolder: teamHolder.css('div.team-score-name span.caption.dashboard-game-team-info__name span.caption__label ::text').get()
                
                # odds extractor
                oddsExtractor = lambda oddsContainers: [
                    eachContainer.css('span.market__value ::text').get().strip() for eachContainer in oddsContainers
                ]
                
                rowContainingTeamInfo = eachGame.css('div.ui-dashboard-cell.dashboard-game-block.dashboard-game__block')
                
                # get the odds
                oddsContainer = eachGame.css('div.ui-dashboard-cell.ui-dashboard-markets-cell.dashboard-markets span.ui-dashboard-markets-cell-group.dashboard-markets__group button.market.dashboard-markets__item.market.market--nameless')
                
                # get an object of the odds in the order
                # [home win, draw, away win]
                oddsValuesObject = oddsExtractor(oddsContainer)
                
                # get time and team data
                teamMetaObject, timeMetaObject = rowContainingTeamInfo.css('span.dashboard-game-block__row')
                
                # get the date
                gameDate = timeMetaObject.css('span.dashboard-game-info.dashboard-game-block__info span.dashboard-game-info__item.dashboard-game-info__date::text').get()
                
                # get game time
                gameTime = timeMetaObject.css('span.dashboard-game-info.dashboard-game-block__info span.dashboard-game-info__item.dashboard-game-info__time::text').get()
                
                # get the teams
                teamsMetaHolders = teamMetaObject.css('a.dashboard-game-block__link.dashboard-game-block-link span.team-scores.dashboard-game-block__teams span.team-scores__teams.team-scores-teams div.dashboard-game-team-info.dashboard-game-block__team')

                homeTeam, awayTeam = [teamNameHandler(eachTeamObject).strip() for eachTeamObject in teamsMetaHolders]

                # print("League:", leagueName)

                # team data object
                teamDataObject = {
                    'date': gameDate.strip() if gameDate else ToolBox().getTodaysDate(),
                    'time': gameTime,
                    'league': leagueName.strip(),
                    'home_team': homeTeam,
                    'away_team': awayTeam,
                    'home_win': oddsValuesObject[0],
                    'draw_win': oddsValuesObject[1],
                    'away_win': oddsValuesObject[2]              
                }
                
                # print(teamDataObject)
                
                # collect the match links
                # check for duplicates
                    # liquidate the object
                liquidatedObject = (
                    (key, value) for key, value in teamDataObject.items()
                )
                

                # store it
                extractedMatchDetails.add(liquidatedObject)            
    
                
        return extractedMatchDetails

    

class TwentyTwoBetUtils:
    def getAvailableLeagues(self, customResponse: Selector, leagueLocation:int):
        """
        Gets the leagues and their resource urls for 22Bet
        """
        # get the leagues and their related matches
        leaguesAndTeams = customResponse.css('div#maincontent div#sports_left div.left_menuEventCon section.ps-container.scroll-area.left_menuEventCon_slide div.assideCon')
        
        # get the football teams and leagues
        footballLeaguesAndTeamsHolder = leaguesAndTeams[1].css('div.assideCon_body.not_top div.block_1 ul.sport_menu li')
        
        # get the football section
        leagueNamesAndMatches = footballLeaguesAndTeamsHolder[leagueLocation].css('ul.liga_menu li')
    
        # collect the leagues and their link pages
        leagueLinkMap = {}
        
        # get the league name and the matches
        for eachNameMatch in leagueNamesAndMatches:         
            # league name DailyUtilities().getLeagueName(headerContent.get())
            leagueName = eachNameMatch.css('a.link::text').get().strip()
            
            # get the link header
            linkHeader = eachNameMatch.css('a.link::attr(href)').get()
            
            # merged link
            mergedLink = urljoin('https://22bet.ug', linkHeader)
            
            # store the data
            leagueLinkMap[leagueName] = mergedLink
            
        
        return leagueLinkMap
    
    
    def getSelectedLeagueData(self, leagueMeta: dict):
        # {'KLASK': 'https://22bet.ug/line/football/2150631-klask'}
        # Goes to the url and extracts the matches for each league in the 'leagueMeta' object
        
        # collect the found matches
        foundMatches = []
        
        for eachLeague, leagueUrl in leagueMeta.items():
            # get the page data for the league
            pageData, _, _ = PageFetchEngine(
                fetchUrlTag=None,
                subPage=True,
                pageScrollCount=10,
                subUrlDetail=[leagueUrl, False, 1]
                ).getRawPage()
            
            # extract the matches
            extractedMatches = self.matchesExtractor(Selector(text=pageData), eachLeague)
            
            # store them
            foundMatches = foundMatches + extractedMatches
            
        return foundMatches
            
    
    def matchesExtractor(self, leagueResponse: Selector, preparedLeagueName):
        # get the matches container
        matchesContainer = leagueResponse.css('div#maincontent div#sports_page div#sports_main div.hottest_games div.sports_widget div#sports_main_new div.game_content_line.on_main.center-content div.line-dashboard div.dashboard.c-events')
        
        # set the league name
        leagueName = preparedLeagueName
        
        # collect the matches detail
        extractedMatchDetails = []
        
        # it will select all matches present there
        for eachMatch in matchesContainer.css('div.c-events__item.c-events__item_col'):
            # get the data holder
            teamInfoHolder = eachMatch.css('div.c-events__item')
            
            # get the time
            # '23/07 14:00'
            dateTimeHolder = teamInfoHolder.css('div.c-events__time.min span::text').get()
            
            dateOfMatch, timeOfMatch = dateTimeHolder.split(' ')
            
            # get the teams
            homeTeam, awayTeam = teamInfoHolder.css('a.c-events__name span.c-events__teams span.c-events__team.u-ovh::text').getall()[:2]
    
            # get the bests
            teamOddsHolder = teamInfoHolder.css('div.c-bets div.c-bets__bet.c-bets__bet_sm span.c-bets__inner::text').getall()
            
            
            missingTeamsManager = lambda teamList, currentSize: teamList[:3] if currentSize >= 3 else teamList.copy() + [ "-" for i in range(1, (3 - currentSize) + 1)]
            
            # get the team odds, substitute with '-' for invalid of inaccessible odds
            homeTeamOdds, drawOdds, awayTeamOdds = missingTeamsManager(teamOddsHolder, len(teamOddsHolder)) if teamOddsHolder else ["-", "-", "-"]
            
            
            # team data object
            teamDataObject = {
                'date': dateOfMatch.strip(),
                'time': timeOfMatch.strip(),
                'league': leagueName,
                'home_team': homeTeam,
                'away_team': awayTeam,
                'home_win': homeTeamOdds,
                'draw_win': drawOdds,
                'away_win': awayTeamOdds               
            }
            
            # print(teamDataObject)
            
            # collect the match links
            extractedMatchDetails.append(teamDataObject)
            
        return extractedMatchDetails

class OneXBetUtils:
    def matchesExtractor(self, leagueResponse: Selector, preparedLeagueName):
        matchHolder = leagueResponse.css('div.dashboard-champ-content')
        
        # for each league get the league name
        leagueName = preparedLeagueName.strip()
        
        # get the teams in the league
        teamsInfoObject = matchHolder.css('div.c-events__item.c-events__item_col.dashboard-champ-content__event-item')
        
        # collect
        matchesCollector = []
        
        for eachTeam in teamsInfoObject:                
            # get the teams playing
            coreTeamInfoObject = eachTeam.css('div.c-events__item.c-events__item_game.c-events-item')
            
            timeTeamInfoHolder = coreTeamInfoObject.css('div.c-events-vertical-scoreboard')
            
            # get the playing time
            dateTimeObject = timeTeamInfoHolder.css('div.c-events-item-group div.c-events__time-info div.c-events__time.c-events-time.min span.c-events-time__val ::text').get().strip()
        
            # get the date
            # 12/07 20:00
            partialGameDate, gameTime = dateTimeObject.split(" ")
            
            gameDate = "{}/{}".format(partialGameDate, ToolBox().getTodaysDate(yearOnly=True))
        
            # print(leagueName, gameDate, gameTime)
            playingTeams = timeTeamInfoHolder.css('a.c-events__name span.c-events__teams span.c-events__team ::text').getall()
            
            homeTeam, awayTeam = playingTeams[0].strip(), playingTeams[1].strip()
            
            # print(homeTeam, awayTeam)
            
            # get list of all odds
            allOdds = eachTeam.css('div.c-events__item.c-events__item_game.c-events-item')
            
            # check for blanks
            if len(allOdds.css('div.c-bets span.non.c-bets__bet.c-bets__bet_sm').getall()) > 3:
                # they are blank
                teamsOdds = ['-', '-', '-']
                
            else:
                # Detroit Pistons Toronto Raptors ['1.47', '15', '2.94']
                teamsOdds = allOdds.css('div.c-bets span.c-bets__bet.c-bets__bet_coef.c-bets__bet_sm span.c-bets__inner ::text').getall()[:3]
                    

            # print("odds:", teamsOdds)
            
            # team data object
            teamDataObject = {
                'date': gameDate,
                'time': gameTime,
                'league': leagueName,
                'home_team': homeTeam,
                'away_team': awayTeam,
                'home_win': teamsOdds[0].strip(),
                'draw_win': teamsOdds[1].strip(),
                'away_win': teamsOdds[2].strip()              
            }
            
            # collect the match links
            matchesCollector.append(teamDataObject)
            
        return matchesCollector


    def getSelectedLeagueData(self, leagueMeta: dict):
        # {'KLASK': 'https://22bet.ug/line/football/2150631-klask'}
        # Goes to the url and extracts the matches for each league in the 'leagueMeta' object
        
        # collect the found matches
        foundMatches = []
        
        for eachLeague, leagueUrl in leagueMeta.items():
            # get the page data for the league
            pageData, _, _ = PageFetchEngine(
                fetchUrlTag=None,
                subPage=True,
                pageScrollCount=10,
                subUrlDetail=[leagueUrl, False, 1]
                ).getRawPage()
            
            # extract the matches
            extractedMatches = self.matchesExtractor(Selector(text=pageData), eachLeague)
            
            # store them
            foundMatches = foundMatches + extractedMatches
            
        return foundMatches

    def extractPresentLeagues(self, pageHtml:str):
        # page response
        pageResponse = Selector(text=pageHtml)

        # get the leagues container
        leaguesObjects = pageResponse.css("div.b-filters-leagues__content")[1]

        # extract the leagues
        leaguesObjects = leaguesObjects.css('div.b-filters__league')
        
        # collect
        seivedLeagues = {}

        for eachLeagueObject in leaguesObjects:    
            # extract the header link
            headerLink = eachLeagueObject.css('a.b-filters__league-wrap::attr(href)').get()
            
            # merge the links
            leagueLink = urljoin('https://1xbet.ug/line/basketball', headerLink)
            
            
            # get the name of the league
            leagueName = eachLeagueObject.css('a.b-filters__league-wrap div.b-filters__league-name::text').get().strip()     

            # print(leagueName, ":", leagueLink)
            
            seivedLeagues[leagueName] = leagueLink
            
        return seivedLeagues
    
    def expandLeagueGroup(self, page: Page, whereToExpand:int):                
        # get the item
        groupLeagueSelector = f'div.b-filters-leagues__content > div.b-filters__league:nth-child({whereToExpand}) > a.b-filters__league-wrap'
        
        # get the group league
        groupLeagueLocator = page.locator(groupLeagueSelector)
        
        # hover over the league
        groupLeagueLocator.first.hover()
        
        return

    def oneXBetDefaultRoutine(self, page: Page, whereSection:int = 2):
        # 'div#maincontent > div#sports_page > div#sports_main div#hottest_games > ' + \
            # 'div.sports_widget > div.b-filters__slider > div.b-filters__sports.b-filters__sports_live.b-filters-sports >
        
        # football or basketball selector
        hoverItemSelector = 'div.b-filters__carousel > div.b-filters-list.b-filters__list > div.b-filters-list__inner > ' + \
            f'div.b-filters__slide:nth-child({whereSection}) > ' + \
                    'div.b-filters__item.b-filters-item.switches__item.b-filters__item > ' + \
                    'a.b-filters__sport.link'
        
        # hover over the football tab
        locator_ = page.locator(hoverItemSelector)
    
        
        # click on the very first element
        locator_.first.hover()

        return

    def pageGetEngine(self, playwright: Playwright, whereSection=None, whatToExpand=None, routineList:list = []) -> None:
        """
        Gets pages and also executes routines
        """
        # create a browser
        browser = playwright.firefox.launch(headless=False)
        
        # instance - tab
        context = browser.new_context()

        # Open new page
        page = context.new_page()

        # get url
        ulrToGet = 'https://1xbet.ug/line/basketball'

        
        page.evaluate(f"window.location.href = '{ulrToGet}';")
        
        # wait for the container to load
        page.wait_for_selector('div.hottest_games')
        
        # wait till all data is loaded
        page.wait_for_load_state("domcontentloaded")
        
        for eachRoutineTag in routineList:
            if eachRoutineTag == 1:
                # hover over the football thing
                self.oneXBetDefaultRoutine(page, whereSection)
                
            else:
                # expand the leagues
                # None by default
                self.expandLeagueGroup(page=page, whereToExpand=whatToExpand)
                
        # wait a little for all requests to be filled
        time.sleep(5)
        
        # wait and get the page content
        htmlContent = page.content()
        
        # close the tab
        context.close()
        
        # close the browser
        browser.close()
        
        return htmlContent
    
    def initiateScrappingSequence(self, where=None, whatToExpand=None, routineList=[]):
        """
        Manages getting the league pages
        Reason: Many leagues are nested in groups
        """
        with sync_playwright() as playwright:
            print(f'\nStarting the scraper..., where={where}, at {whatToExpand}')
            # getting the league pages
            data = self.pageGetEngine(
                playwright,
                whereSection=where,
                whatToExpand=whatToExpand,
                routineList=routineList
                )
            
        return data
    
    
    def getOneXBetLeagues(self, pageResponse:Selector, whereMenu=None, stopLimit=None):
        # get the leagues container
        leaguesObjects = pageResponse.css('div.b-filters-leagues__content div.b-filters__league')
        
        # print("Found:", len(leaguesObjects))
        
        # leagues collector
        leaguesCollector = {}
        
        
            
        # parse the main page
        for position, eachLeagueObject in enumerate(leaguesObjects):
            # manage dummy leagues
            if position == 0:
                # if its football
                if whereMenu == 2:
                    continue
                
                else:
                    pass
            else:
                pass
            
            
            # check for limit
            if stopLimit is None:
                pass
            
            else:
                # check if all is gotten
                if len(leaguesCollector) >= stopLimit:
                    # stop the league extraction
                    break
                
                else:
                    # proceed with league extraction
                    pass
                    
                
                
                    
            # check if its a group of league
            isItGroup = eachLeagueObject.css('div.b-filters__flag.flag-icon.b-filters__group')    
        
            if isItGroup:
                # print(f"{leagueName}: {position + 1}")
                # actual link location
                linkLocation = position + 1
                
                # write once
                withLeaguesExpanded = self.initiateScrappingSequence(
                    where=whereMenu,
                    whatToExpand=linkLocation,
                    routineList=[1, 2] 
                )
                
                # get the present leagues in the group
                foundLeagues = self.extractPresentLeagues(withLeaguesExpanded)
                
                # merge the leagues into one
                leaguesCollector.update(foundLeagues)
                
                # delete the smaller list
                del foundLeagues
                
            
            else:
                # extract the header link
                headerLink = eachLeagueObject.css('a.b-filters__league-wrap::attr(href)').get()
                
                # merge the links
                leagueLink = urljoin('https://1xbet.ug/line/basketball', headerLink)
                
                
                # get the name of the league
                leagueName = eachLeagueObject.css('a.b-filters__league-wrap div.b-filters__league-name::text').get().strip()     
                
            
                leaguesCollector[leagueName.strip()] = leagueLink
            
        
        #  slice required portion
        # will be done in the processor
        
        return leaguesCollector    