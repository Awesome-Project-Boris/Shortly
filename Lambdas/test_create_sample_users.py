from post_create_user import lambda_handler  # assuming your file is named post_create_user.py
from uuid import uuid4
from random import choice
from datetime import datetime

countries = ['US', 'IL', 'FR', 'DE', 'JP']
# names = ['Alice', 'Bob', 'Charlie', 'Dana', 'Eli']
# usernames = ['ali', 'bobby', 'char', 'dee', 'elz']

# names = ['Alicia', 'Robert', 'Charles', 'Danielle', 'Elijah']
# usernames = ['al', 'rob', 'chaz', 'dani', 'eli']


# names = ['Allie', 'Bobby Jr.', 'Chuck', 'Dani', 'Ely']
# usernames = ['ally', 'bobbyj', 'chuck', 'dede', 'elyz']

# names = ['Alina', 'Boaz', 'Carl', 'Daphne', 'Elan']
# usernames = ['ali2', 'bo', 'car', 'daph', 'lan']


# names = ['Alejandro', 'Brandon', 'Chris', 'Doron', 'Ezra']
# usernames = ['aj', 'bran', 'chriz', 'dor', 'ez']

names = ['a', 'b', 'c', 'd', 'e']
usernames = ['aa', 'bb', 'cc', 'dd', 'ee']

for i in range(5):
    #uid = str(uuid4())
    
    
    # below is uid for making it easier to test, delete later
    uid= names[i] + str(i+1)  # !! Delete later
    name = names[i]
    uname = usernames[i]  # ← use a different name
    country = choice(countries)
    email = f"{uname}@testmail.com"
    picture = f"https://i.pravatar.cc/150?img={i+1}"

    event = {
        "Email": email,
        "request": {
            "userAttributes": {
                "sub": uid,
                "name": name,
                "username": uname,
                "locale": country,
                "picture": picture
            }
        }
    }

    print(f"\nCreating user: {email}")
    lambda_handler(event, context=None)
