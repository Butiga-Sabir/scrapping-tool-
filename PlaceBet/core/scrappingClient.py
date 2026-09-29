from .coreUtilities import PageFetchEngine

from .coreIOPipeLines import IOUtilities

from .coreProcessors import PostDataProcessors

class FetchClient:
    def saveScrappedData(self, betDataObjects):
        # save as csv
        IOUtilities().saveAsCsv(betDataObjects)
        
        return
    
    def fetchBetMeta(self, getCategory):
        """
        0 - BetPawa,
        1 - 22Bet,
        2 - MelBet,
        3 - 1xBet
        
        Note: getCategory - 1: football, 2 - basketball
        """
        # data save name
        saveName = "football.csv" if getCategory == 1 else "basketball.csv"
        
        # tag to name, routines and scroll count
        tagKeyMap = {
        # tag: name, routines, scroll count, fetch limit
        0: ('BetPawa', [6], 50, None),
        1: ('22Bet', [], 10, 2),
        2: ('MelBet', [3], 5, 5),
        3: ('1xBet', [4], None, 4)
}
        
        # data store
        bettingData = {
            
        }
        
        # get all betting data from the respective resources
        # range(0, 4)
        for urlTag in range(0, 4):
            # determine 
            # engine instance
            engineInstance = PageFetchEngine(
                fetchUrlTag=urlTag,
                urlCategory=getCategory,
                pageScrollCount=tagKeyMap[urlTag][2],
                specificPageRoutines=tagKeyMap[urlTag][1]
                )
            
            # get the key name
            saveKeyName = tagKeyMap[urlTag][0]

            # print(f"\nScrapping site...., {urlTag}")
    
            # fetch the page using the engine
            pageData, _, pageUrl = engineInstance.getRawPage()
    
            # save the page data
            # IOUtilities().saveWebPage(pageData, pageName)
        
            # print("\nProcessing scrapped data....")
            
            # get the fetch limit
            fetchLimitValue = tagKeyMap[urlTag][3]

            # determine the appropriate processor
            if urlTag == 0:
                # process the data
                bettingJsonData = PostDataProcessors(
                    htmlContent=pageData,
                    pageUrl=pageUrl,
                    ).BetPawaProcessor(fetchLimit=fetchLimitValue)
                
            elif urlTag == 1:
                # process the data
                bettingJsonData = PostDataProcessors(
                    htmlContent=pageData,
                    pageUrl=pageUrl
                    ).Twenty2BetProcessor(
                        fetchCategory=getCategory,
                        fetchLimit=fetchLimitValue
                        
                    )
                
            elif urlTag == 2:
                # process the data
                bettingJsonData = PostDataProcessors(
                    htmlContent=pageData,
                    pageUrl=pageUrl
                    ).MelbetProcessor(
                        getCategory,
                        fetchLimit=fetchLimitValue
                        )
                
            else:
                # process the data
                bettingJsonData = PostDataProcessors(
                    htmlContent=pageData,
                    pageUrl=pageUrl
                    ).OneXBetProcessor(
                        fetchLimit=fetchLimitValue,
                        getCategory=1
                    )                              

            # print("\nSaving Processed data....")
            
            # store the data
            bettingData[saveKeyName] = bettingJsonData
            
            # print(f"\nDone storing the data for {saveKeyName}")
            
            
        
        # print("\nWriting final results to file..")
        
        # save the returned data
        # self.saveScrappedData(bettingData)

        # print("\nDone with Scraping")
        
        return saveName, bettingData

