import scrapy
from .frequentUtils import TwentyTwoBetUtils, ToolBox, MelBetUtils, OneXBetUtils

# 'date'
# 'time'
# 'league'
# 'home_team'
# 'away_team'
# 'home_win' 
# 'draw_win'
# 'away_win'

class SharedUtils:
    def determineLeagueFetchCount(self, leagueMatchMap: dict, fetchLimit, getCategory:int = 1, whatProcessor:int=-1):
        # only use the selected number
        assert lambda:fetchLimit > 0 or fetchLimit is None, "Ensure the fetch limit is a positive integer"
        
        # alter the fetch limit
        if not fetchLimit is None:
            fetchLimit = fetchLimit if len(leagueMatchMap) >= fetchLimit else len(leagueMatchMap)
        
        if fetchLimit is None or fetchLimit == 0:
            leaguesToGet = leagueMatchMap.copy()
            
        else:
            if whatProcessor == 0:
                # based on category change the slice according
                sliceStart = 1 if getCategory == 1 else 0
                
                sliceStop = fetchLimit + 1
                
            else:
                # start slicing from zero
                sliceStart = 0
                
                sliceStop = fetchLimit
            
            # slice the leagues
            leaguesToGet = {eachLeague: leagueMatchMap[eachLeague] for eachLeague in list(leagueMatchMap.keys())[sliceStart:sliceStop]}
        
        # delete the matches league from memory
        del leagueMatchMap
        
        return leaguesToGet



class PostDataProcessors:
    """
    Contains data processors for the given data resources
    
    ['melbet', 'betpawa', '22bet', '1xBet']
    """
    def __init__(self, htmlContent, pageUrl):        
        self.pageUrl = pageUrl
        
        # collect the data
        self.dataItems = []
        
        # create a new instance of the selector
        self.customResponse = scrapy.Selector(text=htmlContent)
    
    def OneXBetProcessor(self, fetchLimit=None, getCategory=1):
        # get the leagues
        leagueMatchMap = OneXBetUtils().getOneXBetLeagues(
            pageResponse=self.customResponse,
            whereMenu=2 if getCategory == 1 else 4,
            stopLimit=fetchLimit)
        
        # print(leagueMatchMap)
        
        # get the proportionate size
        leaguesToGet = SharedUtils().determineLeagueFetchCount(
            leagueMatchMap,
            fetchLimit,
            getCategory=getCategory
            )
        
        # print("Leagues to get:", len(leaguesToGet))
        
        # get the match data
        matchesData = OneXBetUtils().getSelectedLeagueData(leaguesToGet)

        # {'KLASK': 'https://22bet.ug/line/football/2150631-klask'}
        # print("\nScrapped Matches:{}".format(len(matchesData)))
        
        # store the data
        self.dataItems.extend(matchesData)
        
        return self.dataItems  

                

    def MelbetProcessor(self, getCategory: int, fetchLimit=None):
        # get the matches
        # div.layout__main main.betting-content div.betting-main.betting-content__main div.betting-dashboard div.betting-dashboard__item div.betting-main-dashboard div.ui-dashboard.dashboard
        # ul.ui-dashboard__champs li.ui-dashboard-champ.dashboard-champ.dashboard__champ
        # print('Index:', indexSection)
        indexSection = 0 if getCategory == 1 else 2 

        # get the leagues and their respective links
        leagueMatchMap = MelBetUtils().getLeagues(self.customResponse, indexSection)
        
        # print('Found:', len(leagueMatchMap))
        # print(leagueMatchMap)
        
        # get the proportionate size
        leaguesToGet = SharedUtils().determineLeagueFetchCount(
            leagueMatchMap,
            fetchLimit,
            whatProcessor=0 if getCategory==1 else -1,
            getCategory=getCategory
            )
        
        
        # print("Leagues to get:", len(leaguesToGet))
        # get the matches
        extractedMatches = MelBetUtils().getSelectedLeagueData(leaguesToGet)
        
        self.dataItems.extend(extractedMatches)
        
        # print(extractedMatches)
        
        # return None
        
        return self.dataItems

    
    
    def Twenty2BetProcessor(self, fetchLimit=2, fetchCategory=1):
        """
        Default get limit is 5, but can be increased or set to None to ger all leagues and their
        matches
        Note: Setting it to None makes the fetch resource intensive
        """
        
        # determine the league location
        leaguePosition = 0 if fetchCategory == 1 else 2
        
        # get list of present leagues and their matches
        leagueMatchMap = TwentyTwoBetUtils().getAvailableLeagues(self.customResponse, leaguePosition)
        
        # get the proportionate size
        leaguesToGet = SharedUtils().determineLeagueFetchCount(
            leagueMatchMap,
            fetchLimit,
            getCategory=fetchCategory,
            whatProcessor = 0 if fetchCategory == 1 else -1
            )
        
        # print('Found Leagues:{}'.format(len(leaguesToGet)))
        
        # get the match data
        matchesData = TwentyTwoBetUtils().getSelectedLeagueData(leaguesToGet)

        # {'KLASK': 'https://22bet.ug/line/football/2150631-klask'}
        # print("\nScrapped Matches:{}".format(len(matchesData)))
        
        # print(matchesData)
        
        # store the data
        self.dataItems.extend(matchesData)
        
        return self.dataItems


    
    def BetPawaProcessor(self, fetchLimit=None):
        """
        Extracts BetPawa data after scraping
        """
        # it will select all matches present there
        for eachMatch in self.customResponse.css('div[data-test-id="bpEvent"]'):
            # teams detail holder
            teamsDetailHolder = eachMatch.css('a.event-match')
            
            # link not needed as of now
            # headerLink =  teamsDetailHolder.css('::attr(href)').get()
            
            # get the match link
            # matchLink = urljoin(pageUrl, headerLink)
            
            # get the other detail
            teamMetaDataItems = teamsDetailHolder.css('div.row')
            
            # get the time stamps
            timeHolder = teamMetaDataItems[0].css('div.times ::text').get()
            
            dateHolder = teamMetaDataItems[0].css('div.times span.date ::text').get()
            
            # get the playing teams
            playingTeams = teamMetaDataItems[1].css('div.teams p.title.team ::text').getall()
            
            # will format country and league data
            # example: receives ['Football ', ' China ', ' China League 2']
            # extracts the country and the league that is 'china' and 'China League 2'
            leagueMetaHandler = lambda countryLeagueMeta: countryLeagueMeta[2].strip()
        
            
            # get the country and league item holder
            # sample result: Football / China / China League 2
            countryLeagueDataObject = teamMetaDataItems[2].css('p.sub-title.league ::text').get()
            
            # extract and format the country league data
            # sample result : {'country': 'china', 'league': 'China League 2'}
            countryLeagueMeta = leagueMetaHandler(countryLeagueDataObject.split('/'))
            
            # get odds data
            oddsHolder = eachMatch.css('div.betline-list.event-betline div.event-bets span.event-bet-wrapper span.event-bet span.anchor-wrap.short-name')
            
            # determine key tag
            keyTagMap = {
                0: 'first',
                1: 'second',
                2: 'third'
            }
            
            # odds data engine
            oddsDataPipeline = lambda dataObject:  dataObject.css('span.event-odds ::text').get().strip()
            
            if len(oddsHolder) == 3:
                oddsMetaObject = {
                    keyTagMap[itemId] : oddsDataPipeline(oddsItem)
                    
                    for itemId, oddsItem in enumerate(oddsHolder)
                }
            else:
                oddsMetaObject = {
                    'first': oddsDataPipeline(oddsHolder[0]),
                    'second': '-',
                    'third': oddsDataPipeline(oddsHolder[1])                              
                }
            

            # team data object
            teamDataObject = {
                # 'link': matchLink,
                'date': dateHolder.strip(),
                'time': timeHolder.strip(),
                'league': countryLeagueMeta,
                'home_team': playingTeams[0],
                'away_team': playingTeams[1],
                'home_win': oddsMetaObject['first'],
                'draw_win': oddsMetaObject['second'],
                'away_win': oddsMetaObject['third']              
            }
            
            # collect the match links
            self.dataItems.append(teamDataObject)
        
        
        return self.dataItems

