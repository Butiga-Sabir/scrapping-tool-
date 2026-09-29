from playwright.sync_api import Playwright, sync_playwright, Page

import time


class OneXBetSpecial:
    # 5
    def expandLeagueGroup(self, page: Page, whereToExpand:int):                
        # get the item
        groupLeagueSelector = f'div.b-filters-leagues__content > div.b-filters__league:nth-child({whereToExpand}) > a.b-filters__league-wrap'

        # click on the football thing
        menuLocator = page.locator(groupLeagueSelector)
        
        # print('count:{}'.format(menuLocator.count()))
        
        # hover over that menu
        menuLocator.first.hover()
        
        # get the group league
        groupLeagueLocator = page.locator(groupLeagueSelector)
        
        # print('leagues count:{}'.format(groupLeagueLocator.count()))
        
        # hover over the league
        groupLeagueLocator.first.hover()
        
        return 


    

class PageSpecificRoutines:
    def gameCategorySelectionRoutine(self, page:Page, optionToSelect:int):
        # select the specific option
        page.select_option('select.global-select', value=f'{optionToSelect}')
        
        # wait for some time for page to load
        page.wait_for_load_state('domcontentloaded')
        
        # do some waiting again
        time.sleep(3)
        
        return
    # 4
    def oneXBetDefaultRoutine(self, page: Page, whereSection:int = 2):
        # football or basketball selector
        hoverItemSelector = 'div.b-filters__carousel > div.b-filters-list.b-filters__list > div.b-filters-list__inner > ' + \
            f'div.b-filters__slide:nth-child({whereSection}) > ' + \
                    'div.b-filters__item.b-filters-item.switches__item.b-filters__item > ' + \
                    'a.b-filters__sport.link'
        
        # hover over the page
        # page.hover(selector=hoverItemSelector)
        
        
        # click on the football thing
        locator_ = page.locator(hoverItemSelector)
        
        # print('count:{}'.format(locator_.count()))
        
        # click on the very first element
        locator_.first.hover()
        
        
        return

    def scrollThePage(self, currentPage: Page, scrollCount, sleepTime):
        """
        Will scroll the page the specified number of times
        """
        # will generate the current page height
        heightHandler = lambda: currentPage.evaluate('document.body.scrollHeight')
        
        # initialize the height
        previousHeight = heightHandler()
    
        # Note: up (-), down (+)
        for _ in range(scrollCount):     
            # get the height
            currentPage.mouse.wheel(0, previousHeight)
            
            # get the new hight
            newHeight = heightHandler()
            
            # continue scrolling
            # get the new height
            previousHeight =  newHeight + previousHeight
        
            # wait for some time
            time.sleep(sleepTime)
                
        # after scrolling those times wait for the page to load fully
        currentPage.wait_for_load_state("domcontentloaded")
        
        return    

    def expandLeagueSection(self, page: Page, sectionToExpand: int):
        """
        For melbet it requires expanding the league sections so as to get 
        the leagues and their matches
        Note: The website uses protected javascript objects to render data
        
        sectionToExpand: 1 - football, 3 - basketball
        """
        # selector for the page
        navSelector = 'nav.ui-nav.ui-nav--rounded'
        
        # hover over the nav
        page.hover(selector=navSelector)
        
        # selector to wait for
        sectionSelector = 'span.sports-menu-section-name__count'
        
        # wait for some selector
        page.wait_for_selector(sectionSelector)
        
        
        # collapse the matches
        # 1 - expands football section
        # 3 - expands basketball section
        matchesSelector = f'nav.ui-nav.sports-menu-sports.sports-menu-group__sports > ul.ui-nav-items > li.ui-nav-item:nth-child({sectionToExpand}) > div.ui-nav-link > span.ui-nav-link__after > button.ui-nav-link-toggle.has-tooltip'
        
        # click on the football thing
        locator_ = page.locator(matchesSelector)
        
        # debug point - number of objects that match selector on page
        # print('count:{}'.format(locator_.count()))
        
        # click on the very first element to expand the section
        locator_.first.click()
        
        return


class PageFetchEngine:
    """
    Receives a url [fetchUrl] and the number of times [pageScrollCount] to scroll
    Note: The 'pageScrollCount' can be omitted
        # Recommended Scroll Counts :[10 up to 50]
    """
    resourceMapFootball = {
        0: ["https://www.betpawa.ug/upcoming?marketId=_1X2&categoryId=2", 0, False],
        1: ["https://22bet.ug/line/football", 0, False],
        2: ["https://melbet-231489.top/en/line/basketball", 0, False],
        3: ["https://1xbet.ug/line/football", 1, False],
        
        
    }
    
    resourceMapBasket = {
        0: ["https://www.betpawa.ug/upcoming?marketId=ML&categoryId=3", 0, False],
        1: ["https://22bet.ug/en/line/basketball", 0, False],
        2: ["https://melbet-231489.top/en/line/basketball", 0, False],
        3: ["https://1xbet.ug/line/basketball", 1, False],
        
        
    }
    
    def __init__(self, fetchUrlTag, subPage=False, pageScrollCount=50, sleepTime=1, urlCategory=1, subUrlDetail=[], specificPageRoutines=[]):
        # page routines
        self.pageSpecificRoutines = specificPageRoutines
        
        # track category
        self.urlCategory = urlCategory
        
        if subPage is False:
            # resource handler
            resourceHandler = lambda categoryTag: (self.resourceMapFootball[fetchUrlTag][0], self.resourceMapFootball[fetchUrlTag][2], self.resourceMapFootball[fetchUrlTag][1]) if categoryTag == 1 else (self.resourceMapBasket[fetchUrlTag][0], self.resourceMapBasket[fetchUrlTag][2], self.resourceMapFootball[fetchUrlTag][1])
            
            # get the url and the browser display mode and the browsing mode
            self.urlToGet, self.hideBrowser, self.browsingMode  = resourceHandler(urlCategory)
            
            # get the page save name
            self.pageSaveName  = "{}.html".format(self.urlToGet.split("/")[2])
            
            
        else:
            # initialize the respective environment for sub pages
            self.urlToGet,  self.hideBrowser, self.browsingMode = subUrlDetail
            
            # no need for the page name
            self.pageSaveName = None
            
        
        # check if the scroll count is valid
        assert lambda:pageScrollCount > 0 or pageScrollCount is None, "Ensure that the pageScrollCount is positive i.e greater than zero or its None"
        
        # initialize scroll count
        self.pageScrollCount = pageScrollCount
        
        # sleep
        self.sleepTime = sleepTime
        
        
    def pageFetchRoutine(self, playwright: Playwright):
        # create a browser 
        browser = playwright.firefox.launch(headless=self.hideBrowser)
        
        # create a new context of the browser
        browserTabInstance = browser.new_context()
        
        # access the browser and create a page
        currentPage = browserTabInstance.new_page()
                
        if self.browsingMode == 1:
            # get the page without timeouts for loading times
            currentPage.evaluate(f"window.location.href = '{self.urlToGet}';")
            
            # specific for 1xBet - due its loading times
                # wait for the container to load
            currentPage.wait_for_selector('div.hottest_games')

                    
        else:
            # get the page the normal way
            currentPage.goto(self.urlToGet)

        
        # wait for the page tol fully load
        currentPage.wait_for_load_state("domcontentloaded")
        
        
        # control scroll
        ignoreScroll = False
        
        if len(self.pageSpecificRoutines) > 0:
            # perform the routines on the page
            # Note: 2 was omitted it was meant for scrolling
            for eachRoutineTag in self.pageSpecificRoutines:
                # check the routine type 
                if eachRoutineTag == 1 or eachRoutineTag == 3:
                    # execute the custom routines
                    PageSpecificRoutines().expandLeagueSection(currentPage, eachRoutineTag)
                    
                    # after expanding ignore the scroll
                    ignoreScroll = True
                    
                elif eachRoutineTag == 4:
                    # determine the section to expand
                    sectionToExpand = 2 if self.urlCategory == 1 else 4
                    
                    # expand the section
                    PageSpecificRoutines().oneXBetDefaultRoutine(currentPage, sectionToExpand)
                    
                elif eachRoutineTag == 5 or eachRoutineTag == 6:
                    # determine the click point
                    gameCategoryToSelect = 2 if eachRoutineTag == 5 else 3
                    
                    # select the category
                    PageSpecificRoutines().gameCategorySelectionRoutine(
                        currentPage,
                        gameCategoryToSelect
                        )
                    
                # more will be added if a given website requires special attention
                
        else:
            # proceed
            pass
        
        if ignoreScroll is False:
            # check if scrolling is needed
            if not self.pageScrollCount is None:
                # scroll the page the specified number of times
                PageSpecificRoutines().scrollThePage(
                    currentPage=currentPage,
                    scrollCount=self.pageScrollCount,
                    sleepTime=self.sleepTime)
                
            else:
                # just proceed
                pass
            
        else:
            # pass
            pass
        
        # wait for a little longer for any page requests to stop
        time.sleep(4)
            
        # get the page data
        pageHtmlContent = currentPage.content()
        
        # close the tab , then the browser
        browserTabInstance.close()
        
        # close the specific browser instance
        browser.close()
        
        return pageHtmlContent
    
        
    def getRawPage(self):
        """
        Retrieves the web page data
        Returns the page data, page name, and the url
        """
        # start  playwright instance
        with sync_playwright() as playwrightInstance:
            receivedPageData = self.pageFetchRoutine(playwrightInstance)
            
        return receivedPageData, self.pageSaveName, self.urlToGet
            
        
        




    