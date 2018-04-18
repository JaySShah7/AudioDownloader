from selenium import webdriver
import time, os, sys, re, requests, csv, spotipy
import spotipy.util as util
from SpotifyCredentials import *

import logging
import eyed3
logging.getLogger().handlers.pop()


from logging.handlers import RotatingFileHandler
logger=logging.getLogger(__name__)
handler=RotatingFileHandler('MusicDownloader.log', maxBytes=100000, backupCount=1)
logger.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

#Remove eyed3 handler logging,as it always prints to console
eyed3_logger=logging.getLogger('eyed3.log')
eyed3_logger.setLevel("CRITICAL")
for Handler in eyed3_logger.handlers[:]:
    eyed3_logger.removeHandler(Handler)
eyed3_logger=logging.getLogger('eyed3.core')
eyed3_logger.setLevel("CRITICAL")
for Handler in eyed3_logger.handlers[:]:
    eyed3_logger.removeHandler(Handler)
eyed3_logger=logging.getLogger('eyed3.utils')
eyed3_logger.setLevel("CRITICAL")
for Handler in eyed3_logger.handlers[:]:
    eyed3_logger.removeHandler(Handler)
eyed3_logger=logging.getLogger('eyed3')
eyed3_logger.setLevel("CRITICAL")
for Handler in eyed3_logger.handlers[:]:
    eyed3_logger.removeHandler(Handler)


logger.info("Program started!")




class MusicDownloader: #Remember: artist name comes first
    def __init__(self):
        self.driver=webdriver.Chrome()
        os.chdir(sys.path[0])
        self.driver.set_page_load_timeout(30)
        self.driver.get("https://my-free-mp3.net")
        self.token=util.prompt_for_user_token(SPOTIFY_USERNAME,SCOPE,client_id=CLIENT_ID,client_secret=CLIENT_SECRET,redirect_uri=REDIRECT_URI)
        self.spotify = spotipy.Spotify(auth=self.token)
        self.FailedDownloads=[]
        

    def Exit(self):
        self.driver.quit()


    def FixTag(self, FileName):  #fixtag of specific file
        logger.info("Fixing tags: "+str(FileName))
        time.sleep(0.5)
        forbidden=['\\', '/', '&', '.', '?', '(', ')', '[', ']', ' ft ', ' feat ', ' featuring ']
        query=str(os.path.basename(FileName)[:-4])
        query=query.lower()
        for char in forbidden:
            query=query.replace(char, ' ')
        results=self.spotify.search(q=query, type='track', limit=1)
        if not results['tracks']['items']:
            Song, Artist=self.GetSongArtistFromName(query)
            results=self.spotify.search(q='artist:"'+ Artist +'" track:"' + Song + '"', type='track', limit=1)
        if not results['tracks']['items']:
            logger.error("Spotify search for tags failed.")
            raise Exception("Spotify search found no tags.")
        SongName=results['tracks']['items'][0]['name']
        Artists=[]
        for artist in results['tracks']['items'][0]['artists']:
                if artist['name'] not in SongName:
                    Artists.append(artist['name'])
                    
        Artist=', '.join(Artists)

        AlbumArtist= results['tracks']['items'][0]['album']['artists'][0]['name']
        Album=results['tracks']['items'][0]['album']['name']
        Artist=results['tracks']['items'][0]['artists'][0]['name']
        TrackNumber=results['tracks']['items'][0]['track_number']
        Duration=results['tracks']['items'][0]['duration_ms']/1000

        audiofile=eyed3.load(FileName)
        audiofile.initTag()
        audiofile.tag.artist=Artist
        audiofile.tag.album=Album
        audiofile.tag.album_artist=AlbumArtist
        audiofile.tag.title=SongName
        audiofile.tag.track_num=TrackNumber
        audiofile.tag.save()
        print("Fixed tags: " + Artist + " - "+ SongName)
        
    def FixAllTags(self):  #Fix tags of all songs in DownloadedSongs folder

        SongList=[]
        for File in os.listdir('DownloadedSongs'):
            if File.endswith('.mp3'):
                SongList.append(os.path.join("DownloadedSongs",File))

        for Song in SongList:
            try:
                self.FixTag(Song)
            except Exception as e:
                logger.error("Unable to fix tags for song: "+Song)
                print("Unable to fix tags for song: "+Song)
                logger.error(e)

    def GetSongListFromPlaylist(self, playlist_uri):  #Returns list of song names from playlist uri

        playlist_username=playlist_uri.split(':')[2]
        playlist_id=playlist_uri.split(':')[4]
        
        playlist=self.spotify.user_playlist(playlist_username, playlist_id)

        print("Playlist: " + playlist['name'])  
        SongNames=[]
        for i in range(len(playlist['tracks']['items'])):
            Artists=[]
            TrackName=playlist['tracks']['items'][i]['track']['name']
            
            for artist in playlist['tracks']['items'][i]['track']['artists']:
                if artist['name'] not in TrackName:
                    Artists.append(artist['name'])
            if len(Artists)==1:
                SongName=Artists[0]+ ' - '+TrackName
            else:
                artist_string=', '.join(Artists)
                SongName=artist_string+ ' - '+TrackName
            SongNames.append(SongName)
        
        return SongNames
    def DownloadSpotifyPlaylist(self, playlist_uri):
        SongList=[]
        try:
            SongList=self.GetSongListFromPlaylist(playlist_uri)
        except Exception as e:
            logger.error("Couldn't get list of songs from playlist.")
            logger.error(e)
        for Song in SongList:
            Tries=0
            while(Tries<5 and not self.DownloadSong(Song)):
                Tries+=1
                
    def DownloadSongList(self, SongList):
        tempList=list(SongList) #create copy of list
        for Song in tempList:
            Tries=0
            while(Tries<3 and not self.DownloadSong(Song)):
                Tries+=1

            
    def MatchesKeywords(self, SongName, PossibleName): #check if words in SongName are in PossibleName
        PossibleName=''.join(ch for ch in PossibleName if (ch.isalnum() or ch==' '))
        SongName=''.join(ch for ch in SongName if (ch.isalnum() or ch==' '))
        PossibleName=PossibleName.lower()
        SongName=SongName.lower()
        matches=0  
        for word in SongName.split(' '):
            if word in PossibleName:
                matches+=1       
        if matches>=len(SongName.split(' ')):     
            return True
        else:
            return False
        

    def GetSongArtistFromName(self, SongName):
        
        Song=SongName.encode('ascii', 'ignore').decode()
        Artist=''
        
        Split=SongName.split('-')
        if len(Split)==2:
            Artist=Split[0]
            Song=Split[1]

        else:
            Song='-'.join(Split[1:])
            Artist=Split[0]
        
        Split=SongName.split(' - ')
        if len(Split)==2:
            Artist=Split[0]
            Song=Split[1]
        else:
            Song=' - '.join(Split[1:])
            Artist=Split[0]
        
        return Song, Artist
        
    def GetSongInformation(self, SongName): #Returns Dictionary with Link, Song, Artist
        SongName=SongName.lower()
        forbidden=['\\', '/', '&', '.', ',', '(', ')', '[', ']', ' ft ', ' feat ', 'featuring ']
        for wrd in forbidden:
            SongName=SongName.replace(wrd, ' ')   #NEW ADDITION, TEST LATER

        SongName=SongName.title()
        Song, Artist= self.GetSongArtistFromName(SongName)
        #Enter text into search
        try:
            self.driver.find_element_by_id('query').clear()
            self.driver.find_element_by_id('query').send_keys(' '.join(SongName.split('-')))
            self.driver.find_element_by_css_selector("button").click()    
            time.sleep(8)
        except Exception as e:
            logger.error("Unable to query webpage. Logging error:")
            logger.error(e)
            
        #Create list of result. if no result, raise error,
        #Result has Name, Link
        NoResults=self.driver.find_elements_by_xpath("//li[@class='list-group-item list-group-item-danger']")
        if(NoResults):  #Song not in database
            raise Exception("No results! Song not in database.")
        Results=[]
        linkresults=self.driver.find_elements_by_xpath("//li[@class='list-group-item']")
        
        for i in range(0,len(linkresults)):
            try:
                Link=str(self.driver.find_elements_by_xpath("//*[@class='name']")[i].get_attribute('href'))
                Name=str(linkresults[i].text.split('\n')[3].encode('UTF-8').decode('UTF-8'))
                if(self.MatchesKeywords(SongName, Name)):  #Check if Artists name is in Result  
                    Results.append({'Name':Name, 'Link':Link})
                    
                else:
                    pass
            except Exception as e:
                logger.error(e)

        if len(Results)==0:
            raise Exception("Results could not be appended to list.")
        
        # Get Best Matcht
        try:
            Results=self.FilterResults(Results, SongName)
        except Exception as e:
            logger.error("Could not filter song results to download.")
            logger.error(e)
        #Create Link, Song, Artist Variables
        Link=Results[0]['Link']
        Song,Artist= self.GetSongArtistFromName(Results[0]['Name'])
        Song=Song.encode('ascii', 'ignore').decode()
        Artist=Artist.encode('ascii', 'ignore').decode()
        try:
            logger.info("Link: " + Link+"  Song Name: "+Song +"  Artist: "+Artist)
        except exception as e:
            logger.warning("Couldn't log song name")
        return{'Link':Link, 'Song':Song, 'Artist':Artist}



    def FilterResults(self, OldResults, SongName): #returns 
        NewResults=OldResults
        SongName=SongName.lower()
        i=0
        j=0
        Flag=False
        WordSpecifiers=['remix', 'version', 'edit', 'instrumental', 'karaoke']
        while j<len(NewResults):
            for word in WordSpecifiers:
                if word in NewResults[i]['Name'].lower() and not word in SongName:
                    Flag=True 
            if Flag:
                temp=NewResults.pop(i)
                
                i-=1
                Flag=False
            
            i+=1
            j+=1
        return NewResults
    
    
    def DownloadFile(self, Link, Song, Artist):              
        if not os.path.exists('DownloadedSongs'):
            os.makedirs('DownloadedSongs')     
        r=requests.get(Link, allow_redirects=True, stream=True)
        time.sleep(1)
        tries=0    
        while(tries<5):    #Try to download file 5 times
            r=requests.get(Link, allow_redirects=True, stream=True)
            FileInfo=r.headers.get('Content-Disposition')
            FileTypes=re.findall('\.(\w\w\w)', FileInfo)
            FileType=FileTypes[len(FileTypes)-1]
            FileName=Artist+' - '+ Song + '.'+ FileType
            FileName=FileName.replace('\\', ' ')
            FileName=FileName.replace('/', ' ')
            FileName=FileName.replace('*', ' ')
            
            time.sleep(3)
            if(r.status_code==200):
                logger.info("Downloading song: "+str(Song)+' - '+str(Artist))  
                file=open(os.path.join('DownloadedSongs',FileName), 'wb')
                for chunk in r.iter_content(chunk_size=1024):
                    file.write(chunk)
                file.close()
                if os.path.getsize(os.path.join('DownloadedSongs',FileName)):
                    break
                else:
                    logger.warning("Zero filesize. Download failed.")
                    os.remove(os.path.join('DownloadedSongs',FileName))
            logger.warning("Download failed for " + FileName+ " , trying again.")
            tries+=1
        if tries==5:
            logger.error("File failed to download. Too many tries.")
            


    def DownloadSong(self,SongName):
        try:
            SongInformation=self.GetSongInformation(SongName)
        except Exception as e:
            logger.error("Could not get song information from my-free-mp3")
            logger.error(e)
            self.FailedDownloads.append(SongName)
            print("Download failed: "+ SongName)
            return False
        try:    
            self.DownloadFile(SongInformation['Link'],SongInformation['Song'],SongInformation['Artist'])
            print("Song downloaded: "+ SongInformation["Artist"].encode('ascii', 'ignore').decode() + ' - '+SongInformation["Song"].encode('ascii', 'ignore').decode())
            return True
        except Exception as e:
            logger.error(e)
            logger.error("Could not download: "+SongName)
            print("Download failed: "+ SongName)
            self.FailedDownloads.append(SongName)
            return False
                         
    def DownloadCSVSongList(self,CSVFileName):
        File=open(CSVFileName, 'r')
        FileList=csv.reader(File)
        
        for Row in FileList:
            Tries=0
            while(Tries<5 and not self.DownloadSong(Row[0])):
                Tries+=1
        File.close()
    def RetryFailedDownloads(self):
        tempFailedDownloads=list(set(self.FailedDownloads))
        self.FailedDownloads=[]
        self.DownloadSongList(tempFailedDownloads)
        self.FailedDownloads=list(set(self.FailedDownloads))

    def SearchPlaylist(self, SearchTerm=''):
        if not SearchTerm:
            SearchTerm=input("Enter name of playlist: ")
        results = self.spotify.search(q=SearchTerm, type='playlist', limit=10)

        for i in range(len(results['playlists']['items'])):
            playlist_uri=results['playlists']['items'][i]['uri']
            playlist_name=results['playlists']['items'][i]['name']
            playlist_owner=results['playlists']['items'][i]['owner']['display_name']
            print("\nName: " + str(playlist_name) + "\nOwner: " + str(playlist_owner))

            ToDownload=input("Download playlist? (y/n)(press enter to exit)")
            if ToDownload.lower().startswith("y"):
                self.DownloadSpotifyPlaylist(playlist_uri)
            elif ToDownload.lower().startswith("n"):
                pass
            else:
                break
            print("\n\n")
        

downloader=MusicDownloader()
#downloader.DownloadSongList('SongList.csv')
#downloader.DownloadSpotifyPlaylist('spotify:user:22yflzfiannkxkcy7hng346ga:playlist:1mMFlL8j6r82BGFFAtyRHI')
#downloader.DownloadSong("MC Fioti Ft Future, J Balvin Stefflon, Don Juan Magan - Bum Bum Tam Tam")
#print(downloader.FailedDownloads)
#downloader.FailedDownloads=['Travis Atreo - Kids', 'Travis Atreo - Kids', 'Travis Atreo - Kids', 'Travis Atreo - Kids', 'Travis Atreo - Kids', 'Cash Cash - How To Love (feat. Sofia Reyes)', 'courtship. - Tell Me Tell Me', 'courtship. - Tell Me Tell Me', 'courtship. - Tell Me Tell Me', 'courtship. - Tell Me Tell Me', 'courtship. - Tell Me Tell Me', 'Lukas Graham - 7 Years - Spotify Sessions', 'Lukas Graham - 7 Years - Spotify Sessions', 'Lukas Graham - 7 Years - Spotify Sessions', 'Lukas Graham - 7 Years - Spotify Sessions', 'Lukas Graham - 7 Years - Spotify Sessions', 'Gab Veläzquez - Budapest', 'Gab Veläzquez - Budapest', 'Gab Veläzquez - Budapest', 'Gab Veläzquez - Budapest', 'Gab Veläzquez - Budapest', 'Ben Schuller - 2u', 'Ben Schuller - 2u', 'Ben Schuller - 2u', 'Ben Schuller - 2u', 'Ben Schuller - 2u', "Megan Davies - White Walls/Can't Hold Us/Same Love/Thrift Shop (Acoustic Mashup) Feat. Jaclyn Davies", "Megan Davies - White Walls/Can't Hold Us/Same Love/Thrift Shop (Acoustic Mashup) Feat. Jaclyn Davies", "Megan Davies - White Walls/Can't Hold Us/Same Love/Thrift Shop (Acoustic Mashup) Feat. Jaclyn Davies", "Megan Davies - White Walls/Can't Hold Us/Same Love/Thrift Shop (Acoustic Mashup) Feat. Jaclyn Davies", "Megan Davies - White Walls/Can't Hold Us/Same Love/Thrift Shop (Acoustic Mashup) Feat. Jaclyn Davies", 'Jennifer Lopez - Vivir Mi Vida - Recorded at Spotify Studios NYC', 'Jennifer Lopez - Vivir Mi Vida - Recorded at Spotify Studios NYC', 'Jennifer Lopez - Vivir Mi Vida - Recorded at Spotify Studios NYC', 'Jennifer Lopez - Vivir Mi Vida - Recorded at Spotify Studios NYC', 'Jennifer Lopez - Vivir Mi Vida - Recorded at Spotify Studios NYC', 'Midday Swim - Living a Lie', 'Midday Swim - Living a Lie', 'Midday Swim - Living a Lie', 'Midday Swim - Living a Lie', 'Midday Swim - Living a Lie', 'PONY - Baby, Please', 'PONY - Baby, Please', 'PONY - Baby, Please', 'PONY - Baby, Please', 'PONY - Baby, Please', "Big Shaq - Man's Not Hot - Black Caviar Remix", "Big Shaq - Man's Not Hot - Black Caviar Remix", "Big Shaq - Man's Not Hot - Black Caviar Remix", "Big Shaq - Man's Not Hot - Black Caviar Remix", "Big Shaq - Man's Not Hot - Black Caviar Remix", 'We Rabbitz, Marina Lin - Real Friends', 'We Rabbitz, Marina Lin - Real Friends', 'We Rabbitz, Marina Lin - Real Friends', 'We Rabbitz, Marina Lin - Real Friends', 'We Rabbitz, Marina Lin - Real Friends', 'Boyce Avenue - What Lovers Do (feat. Mariana Nolasco)', 'Boyce Avenue - What Lovers Do (feat. Mariana Nolasco)', 'Boyce Avenue - What Lovers Do (feat. Mariana Nolasco)', 'Boyce Avenue - What Lovers Do (feat. Mariana Nolasco)', 'Boyce Avenue - What Lovers Do (feat. Mariana Nolasco)']
#downloader.RetryFailedDownloads()
#downloader.FixAllTags()

downloader.SearchPlaylist()
downloader.Exit()


                           
                           


