import json

import csv

class IOUtilities:
    """
    Holds routines for I/O of betting data
    """
    def recordJsonData(self, dataObject):
        """
        Dumps the provided data into a json file
        """
        # # debug point
        print("Size:", len(dataObject))
    
        with open('data.json', 'w+') as dataStore:
            json.dump(dataObject, dataStore)
            
        return
    
    def saveWebPage(self, dataObject, fileName):
        # yield the whole output
        with open(fileName, 'w+') as dataStore:
            dataStore.write(dataObject)
            
        return
    
    def saveAsCsv(self, saveName:str, betDataObjects:dict):
        with open(saveName, 'w+') as csvFileObject:
            # data fields
            fieldnames = ["date", "time", "league", "home_team", "away_team", "home_win", "draw_win", "away_win"]
            
            # create a writing object
            writerObject = csv.DictWriter(csvFileObject, fieldnames=fieldnames)
            
            # create the fields
            for resourceCount, resourceData in enumerate(betDataObjects.items()):
                if resourceCount == 0:
                    pass
                    
                else:
                    # create some gap
                    writerObject.writerow(dict())
                    writerObject.writerow(dict())
                    
                # write the name of the resource
                writerObject.writerow(
                    dict(
                        date = resourceData[0]
                        )
                    )
                
                # write down the header row
                writerObject.writeheader()
                
                # write the details
                for eachDataItem in resourceData[1]:
                    # write all the items
                    writerObject.writerow(eachDataItem)

                    
                    
        return

