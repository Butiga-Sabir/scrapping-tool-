from core.scrappingClient import FetchClient
from core.coreIOPipeLines import IOUtilities


class LevelOneClient:
    # run this file and it will generate a file called data.csv
    def getTodaysData(self, fetchTag):
        """
        Fetches todays data and returns it
        fetchTag - 1 : football, 2 - basketball
        """
        # debug
        print('\nStarted Scrapping Engine...')
        
        # get run the scrapper
        dataStoreName, todaysData = FetchClient().fetchBetMeta(fetchTag)
        
        # save the data
        IOUtilities().saveAsCsv(
            dataStoreName,
            todaysData
            )
        
        return
    

# 1- football, 2 - basket ball
# Note: running this file will generate a csv file
LevelOneClient().getTodaysData(2)


print('\nDone scrapping')


# last command  playwright install