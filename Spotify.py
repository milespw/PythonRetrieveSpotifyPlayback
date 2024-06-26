import requests
import json    
from datetime import datetime

# Other Programs
from URLEncoding import urlencoding

class Spotify:
    def __init__(self, BASE_64_STRING, CLIENT_ID, REDIRECT_URI, SCOPES, JSON_FILE_FOLDER="") -> None:
        """BASE_64_STRING - Base 64 String of --> clientid:clientsecret\n
        CLIENT_ID - Users client ID from --> https://developer.spotify.com/dashboard\n
        REDIRECT_URI - Found on Spotify Developer Dashboard\n
        SCOPES -> Required scopes for the application to function\n
        JSON_FILE_FOLDER -> Possible subfolder for JSON file"""
        self.BASE_64_STRING = BASE_64_STRING 
        self.CLIENT_ID = CLIENT_ID  
        self.REDIRECT_URI = REDIRECT_URI  
        self.JSON_FILE_FOLDER = JSON_FILE_FOLDER 
        self.SCOPES = SCOPES 
        
        self.accessToken = ""
        data = self.__retrieveCredFile()
        try:
            self.refreshToken = data["REFRESHKEY"]
        except KeyError:
            self.refreshToken = ""

        if self.refreshToken == "":
            print(self.getKeyUrl())
            authKey = input()
            
            self.__getAuthorizationTokens(authKey)
            data["REFRESHKEY"] = self.refreshToken
            self.__saveCredFile(data)
        
        else:
            self.__refreshAccessToken()

    def getKeyUrl(self) -> str:
        """Returns a URL which the user must go to to get their initial Authorization Token.\n
        Code is stated after ?code="""
        return f"https://accounts.spotify.com/authorize?client_id={self.CLIENT_ID}&scope={self.SCOPES}&response_type=code&redirect_uri={self.REDIRECT_URI}" 

    def __getAuthorizationTokens(self, token) -> None: 
        """Gets initial refresh and access token, using the intial authorization token."""
        authHeader = {}
        authHeader["Authorization"] = "Basic " + self.BASE_64_STRING

        url = "https://accounts.spotify.com/api/token"
        form = {
            "code":token,
            "redirect_uri":self.REDIRECT_URI,
            "grant_type":"authorization_code"
        }
        headers = {
            "Authorization":"Basic " + self.BASE_64_STRING,
            "Content-Type":"application/x-www-form-urlencoded"
        }
        form = urlencoding.urlencode(form) # type: ignore

        # Get Spotify Response
        response = requests.post(url=url, headers=headers, data=form).json()
        
        try:
            self.refreshToken = response["refresh_token"]
            self.accessToken = response["access_token"]
            self.accessTokenExpiry = [datetime.now().strftime("%d/%m/%Y %H:%M:%S"),int(response["expires_in"])]
        except KeyError:
            print(response)

    # Refreshes an Access token when needed.
    def __refreshAccessToken(self) -> None:
        """Refreshes the Access token using the Refresh Token when it expires."""
        url = "https://accounts.spotify.com/api/token"
        form = {
            "grant_type": "refresh_token",
            "refresh_token":self.refreshToken
        }
        headers = {
            "Authorization":"Basic " + self.BASE_64_STRING,
            "Content-Type":"application/x-www-form-urlencoded"
        }

        # Get Spotify response
        response = requests.post(url=url, headers=headers, data=urlencoding.urlencode(query=form)).json() # type: ignore
        try:
            self.accessToken = response["access_token"]
            self.accessTokenExpiry = [datetime.now().strftime("%d/%m/%Y %H:%M:%S"),int(response["expires_in"])]
        except KeyError:
            print("InvalidRefreshToken", self.refreshToken)
            
        try: # Needed because the API does not always respond with a refresh token
            self.refreshToken = response["refresh_token"]
        except KeyError:
            pass
    
    def get(self, url) -> dict:
        """Handles token expiry and no content automatically when making an HTTP GET request."""
        headers = {"Authorization": f"Bearer {self.accessToken}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 401:
            print("Token Expired")
            self.__refreshAccessToken()
            return self.requestPlayback(), response.status_code
        elif response.status_code == 204:
            return json.dumps({"Playback":"No Content"}), response.status_code
        elif response.status_code == 200:
            return response.json(), response.status_code
        
    def post(self, url, data="") -> dict:
        """Handles token expiry and no content automatically when making an HTTP POST request."""
        headers = {"Authorization": f"Bearer {self.accessToken}"}
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 401:
            print("Token Expired")
            self.__refreshAccessToken()
            return self.requestPlayback(), response.status_code
        elif response.status_code == 204:
            return json.dumps({"Playback":"No Content"}), response.status_code
        elif response.status_code == 200:
            return response.json(), response.status_code
        
    def requestPlayback(self) -> json:
        """Returns the users currently playing song as a json object."""
        return self.get('https://api.spotify.com/v1/me/player')
        
    def requestFormattedPlayback(self) -> dict:
        """Retrieves the users currently playing song, formats it into the necessary data and outputs it as a dictionary."""
        data, statusCode = self.requestPlayback()
        
        # If there is no content, there is nothing to format!
        if statusCode == 204:
            return data, statusCode
        
        try:
            trackID = data['item']['id']
        except KeyError:
            trackID = None
        try:
            trackName = data['item']['name']
        except KeyError:
            trackName = None
        try:
            names = []
            for i in range(0, len(data['item']['artists'])):
                names.append(data['item']['artists'][i]["name"])
            trackArtists = ", ".join(names)
        except KeyError:
            trackArtists = None
        try:
            link = data['item']['external_urls']['spotify']
        except:
            link = None
        try:
            try:
                lqAlbumArt = data["item"]["album"]["images"][2]["url"]
            except KeyError:
                lqAlbumArt = None
            try:
                hqAlbumArt = data["item"]["album"]["images"][0]["url"]
            except KeyError:
                hqAlbumArt = None
        except IndexError:
            lqAlbumArt = None
            hqAlbumArt = None
            
        if lqAlbumArt == None:
            try:
                lqAlbumArt, statusCode = self.getPlaylistImage(str(data["context"]["external_urls"]["spotify"]).replace("https://open.spotify.com/playlist/","",1))
                lqAlbumArt = lqAlbumArt[0]["url"]
            except KeyError:
                pass
            except IndexError:
                pass
        try:
            playing = data["is_playing"]
        except KeyError:
            playing = False

        trackData = {
            "id":trackID,
            "name":trackName,
            "artists":trackArtists,
            "link":link,
            "hq_art":hqAlbumArt,
            "art":lqAlbumArt,
            "playing":playing
        }

        return trackData, statusCode

    def __retrieveCredFile(self) -> dict:
        """Retrieves refresh token from Credentials file."""
        with open(f"{self.JSON_FILE_FOLDER}credentials.json","r") as f:
            data = json.load(f)
        return data

    def __saveCredFile(self, data) -> None:
        """Saves refresh token to the Credentials file."""
        with open(f"{self.JSON_FILE_FOLDER}credentials.json", "w") as f:
            json.dump(data, f)

    def search(self, query, searchType) -> dict:
        """Searches for a song on the Spoify Database\n
        Common valid search types include:
        * "track"
        * "album"
        * "artist" """
        url = "https://api.spotify.com/v1/search"
        searchQuery = f"?q={query}&type={searchType}"
        return self.get(f"{url}{searchQuery}")
    
    def searchAndQueue(self, query) -> json:
        """Searches and Queues a song on the users spotify account."""
        response = self.search(query, "track")
        newTrack = response["tracks"]["items"][0]["uri"]
        return self.addToQueue(newTrack)
    
    def addToQueue(self, uri) -> json:
        """Adds a track to queue, using the tracks unique identifier."""
        url = "https://api.spotify.com/v1/me/player/queue"
        track = f"?uri={uri}"
        return self.post(f"{url}{track}")
    
    def skip(self, forward=True) -> json:
        """Skips the currently playing song in the users queue."""
        url_fw = "https://api.spotify.com/v1/me/player/next"
        url_bw = "https://api.spotify.com/v1/me/player/previous"
        if forward:
            return self.post(url_fw)
        else:
            return self.post(url_bw)
    
    def getPlaylistItems(self, playlistID) -> dict:
        """Gets the whole contents of a users playlist."""
        url = f"https://api.spotify.com/v1/playlists/{playlistID}/tracks"
        return self.get(url)

    def getPlaylistImage(self, playlistID) -> str:
        """Gets the image of the currently playing playlist"""
        url = f"https://api.spotify.com/v1/playlists/{playlistID}/images"
        return self.get(url)
