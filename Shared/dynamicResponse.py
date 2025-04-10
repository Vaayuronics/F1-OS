class DynamicResponse():
    """Object to perform more functions on a uresponse object"""

    def __init__(self, response : dict, status : int):
        self.response = response
        self.status = status

    def get_status(self) -> int:
        """Returns the status code of the request object"""
        return self.status
    
    def ok(self) -> bool:
        """Returns whether the response was succesful or not"""
        if self.status >= 200 and self.status <= 400:
            return True
        else:
            return False

    def json(self) -> dict:
        """Returns the response object as a jsonified dictionary"""
        return self.response
    
    def get_detail(self) -> str:
        """Returns the error details, returns none if there was no error"""
        return self.response.get('detail')
    
    def keys(self) -> list:
        """Returns a list of all the keys in the response json"""
        return self.response.keys()
    
    def get(self, key):
        """Returns the value at key"""
        return self.response.get(key)
    
    def __str__(self):
        return self.json()
    
    def __getitem__(self, key):
        return self.get(key)