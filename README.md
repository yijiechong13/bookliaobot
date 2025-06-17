# bookliaobot

Set Up Instructions: 
1. Clone Github repository 
2. cd bookliaobot
3. python3 -m venv venv 
4. source venv/bin/activate #mac
venv\Scripts\activate #windows
5. pip install -r requirements.txt
6. Create .env file :
    Add: (EXACT SAME NAME) 
    i)   BOT_TOKEN
    ii)  ANNOUNCEMENT_CHANNEL
    iii) FIREBASE_CREDENTIALS = ".firebasekey.json"

7. Create .firebasekey.json file to store firebase key 

8. Add these to .env file: 
# Get these from https://my.telegram.org/auth
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash 
TELEGRAM_PHONE_NUMBER=your phone number

