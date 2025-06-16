from post_create_user import lambda_handler  # assuming your file is named post_create_user.py
from uuid import uuid4
from random import choice
from datetime import datetime

countries = ['US', 'IL', 'FR', 'DE', 'JP']
# names = ['Alice', 'Bob', 'Charlie', 'Dana', 'Eli']
# nicknames = ['ali', 'bobby', 'char', 'dee', 'elz']

names = ['Alicia', 'Robert', 'Charles', 'Danielle', 'Elijah']
nicknames = ['al', 'rob', 'chaz', 'dani', 'eli']


# names = ['Allie', 'Bobby Jr.', 'Chuck', 'Dani', 'Ely']
# nicknames = ['ally', 'bobbyj', 'chuck', 'dede', 'elyz']

# names = ['Alina', 'Boaz', 'Carl', 'Daphne', 'Elan']
# nicknames = ['ali2', 'bo', 'car', 'daph', 'lan']


# names = ['Alejandro', 'Brandon', 'Chris', 'Doron', 'Ezra']
# nicknames = ['aj', 'bran', 'chriz', 'dor', 'ez']



for i in range(5):
    #uid = str(uuid4())
    
    
    # below is uid for making it easier to test, delete later
    uid= names[i] + str(i+1)  # !! Delete later
    name = names[i]
    nickname = nicknames[i]
    country = choice(countries)
    email = f"{nickname}@testmail.com"
    picture = f"https://i.pravatar.cc/150?img={i+1}"

    event = {
        "Email": email,
        "request": {
            "userAttributes": {
                "sub": uid,
                "name": name,
                "nickname": nickname,
                "locale": country,
                "picture": picture
            }
        }
    }

    print(f"\nCreating user: {email}")
    lambda_handler(event, context=None)
