# bookliaobot

Set Up Instructions: 
1. Clone Github repository 
2. cd bookliaobot
3. python3 -m venv venv 
4. source venv/bin/activate #mac
venv\Scripts\activate #windows
5. pip install -r requirements.txt
6. Create .env file :
    Add: 
    i)   BOT_TOKEN
    ii)  ANNOUNCEMENT_CHANNEL
    iii) FIREBASE_CREDENTIALS = ".firebasekey.json"

7. Create .firebasekey.json file to store firebase key 