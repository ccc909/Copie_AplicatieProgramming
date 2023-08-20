from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import pyrebase
from typing import Union
from typing import Optional
import uuid
import datetime
import json
import hashlib
import time

firebaseConfig = {
  
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth=firebase.auth()
db = firebase.database()

class leave(BaseModel):
    group_id: str

class join(BaseModel):
    group_id: str

class Item(BaseModel):
    group_name: str
    group_description: Optional[str]

class login(BaseModel):
    email: str
    password: str

class register(BaseModel):
    email: str
    password: str
    username: str
    birth_date: str
    studying_at: str

class account_items(BaseModel):
    username: Optional[str] = None
    birth_date: Optional[str] = None
    profile_pic: Optional[str] = None
    studying_at: Optional[str] = None

app = FastAPI(title="fanclub danutzu")

def check_username(username):
    dict1 = db.child("users").get().val()
    if dict1:
        iter_list = dict1.keys()
        for x in iter_list:
            if dict1[x]["username"]==username:
                return False
        return True
    else:
        return True

def get_tokens():
    return db.child("users").get().val().keys()

@app.get("/api/get_groups")
async def read_main(auth_id: Optional[str] = None):
    groups = db.child("groups").get()
    vals = dict(groups.val())
    authid_hash = hashlib.sha1(auth_id.encode("UTF-8")).hexdigest()
    print(vals)
    delete = [key for key in vals if auth_id in vals[key]['member_tokens'] or vals[key]['creator_token']==auth_id]
    for x in delete:
        del vals[x]
    for x in vals.values():
        del x['creator_token']
        del x['member_tokens']
    return vals

@app.post("/api/create_group")
async def read_main(item: Item, auth_id: Optional[str] = None):
    try:
        usr_uuid= str(uuid.uuid4())
        data= {
            'creator_token':auth_id,
            'group_name':item.group_name,
            'group_description':item.group_description,
            'member_tokens': [auth_id]
            }
        db.child("groups").child(usr_uuid).set(data)
    except:
        return {"success":False}

@app.get("/api/delete_group")
async def read_main(auth_id: Optional[str] = None,group_id: Optional[str] = None):
    if db.child("groups").child(group_id).child('creator_token').get().val() == auth_id:
        db.child("groups").child(group_id).remove()
@app.post("/api/register")
async def read_main(register: register):   
    if check_username(register.username):
        auth.create_user_with_email_and_password(register.email,register.password)
        login = auth.sign_in_with_email_and_password(register.email, register.password)
        auth_response = auth.get_account_info(login['idToken'])
        localId= auth_response['users'][0]['localId']
        data = {
            "username": register.username,
            "birth_date": str(register.birth_date),
            "profile_pic": "",
            "studying_at": register.studying_at,
            "user_hash":  hashlib.sha1(localId.encode("UTF-8")).hexdigest()        }
        db.child("users").child(localId).set(data)
        return {"success":True,"local":localId, "acc_data":data}
    else:
        return {"success":False}
    
    

@app.post("/api/login")
async def read_main(login: login):
    login = auth.sign_in_with_email_and_password(login.email, login.password)
    auth_response = auth.get_account_info(login['idToken'])
    localId= auth_response['users'][0]['localId']
    l=[]
    for x in get_tokens():
        l.append(x)
    if localId in l:
        return {"success":True,"local":localId, "acc_data":db.child("users").child(localId).get().val()}
    else:
        return {"success":False}

@app.post("/api/edit_account")
async def read_main(account_items: account_items, auth_id: Optional[str] = None):
    print(account_items.profile_pic)
    print(check_username(account_items.username))
    if auth_id in get_tokens() and check_username(account_items.username):
        db.child("users").child(auth_id).update(account_items.dict(exclude_none=True))
        return {"success":True}
    else:
        return {"success":False}

@app.post("/api/join_group")
async def read_main(join: join, auth_id: Optional[str] = None):
    groups = db.child("groups").get()
    vals = dict(groups.val())
    for x in vals:
        if join.group_id == x and auth_id not in vals[x]['member_tokens']:
            member_tokens=vals[x]['member_tokens']
            member_tokens.append(auth_id)
            db.child("groups").child(x).child('member_tokens').set(member_tokens)


@app.post("/api/leave_group")
async def read_main(leave:leave, auth_id: Optional[str] = None):
    groups = db.child("groups").get()
    vals = dict(groups.val())
    for x in vals:
        tokens = vals[x]['member_tokens']
        if x == leave.group_id and auth_id in tokens and auth_id != vals[x]['creator_token']:
            tokens.remove(auth_id)
            db.child("groups").child(x).child('member_tokens').set(tokens)


@app.get("/api/get_mygroups")
async def read_main(auth_id: Optional[str] = None):
    groups = db.child("groups").get()
    vals = dict(groups.val())
    authid_hash = hashlib.sha1(auth_id.encode("UTF-8")).hexdigest()
    vals1={}
    for x in vals:
        if vals[x]['creator_token']==auth_id or auth_id in vals[x]['member_tokens']:
            vals1[x]=vals[x]
    return vals1

@app.get("/api/get_groupmembers")
async def read_main(auth_id: Optional[str] = None, group_id: Optional[str] = None):
    members = db.child("users").get()
    members_val = dict(members.val())
    groups = db.child("groups").get()
    vals = dict(groups.val())
    authid_hash = hashlib.sha1(auth_id.encode("UTF-8")).hexdigest()
    l=[]
    for x in vals[group_id]['member_tokens']:
        if x==vals[group_id]['creator_token']:
            l.append({'username':members_val[x]['username'],'profile_pic':members_val[x]['profile_pic'],'is_owner':True,'authid_hash':hashlib.sha1(x.encode("UTF-8")).hexdigest()})
        else:
            l.append({'username':members_val[x]['username'],'profile_pic':members_val[x]['profile_pic'],'is_owner':False,'authid_hash':hashlib.sha1(x.encode("UTF-8")).hexdigest()})
    return l

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, auth_id: Optional[str] = None, group_id: Optional[str] = None):
    authid_hash = hashlib.sha1(auth_id.encode("UTF-8")).hexdigest()
    username = db.child("users").child(auth_id).child('username').get().val()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            db.child("groups").child(group_id).child('messages').push({'message_date':time.time(),'message':data,'sender_hash':authid_hash,'username':username})
            await manager.broadcast({'authid_hash':authid_hash,'message':data})
    except:
            manager.disconnect(websocket)
@app.get("/api/get_messages")
async def read_main(auth_id: Optional[str] = None, group_id: Optional[str] = None):
    tokens = db.child("groups").child(group_id).child('member_tokens').get()
    token_vals = tokens.val()
    messages = db.child("groups").child(group_id).child('messages').get()
    if messages:
        messages_val = messages.val()
        return messages_val


@app.get("/api/kick_user")
async def read_main(auth_id: Optional[str] = None, user_hash: Optional[str]= None,group_id: Optional[str]=None):
    group = db.child("groups").child(group_id).get()
    group_vals = group.val()
    l=[]
    for x in group_vals['member_tokens']:
        l.append(hashlib.sha1(x.encode("UTF-8")).hexdigest())
    print(group_vals['member_tokens'])
    if group_vals['creator_token'] == auth_id and user_hash in l:
        i=0
        pos=-1
        for x in l:
            if user_hash == x:
                pos = i
            i+=1
        prep = db.child("groups").child(group_id).child('member_tokens').get().val()
        prep.pop(pos)
        db.child("groups").child(group_id).child('member_tokens').set(prep)

@app.get("/api/get_userinfo")
async def read_main(user_hash: Optional[str] = None):
    users = db.child("users").get().val()
    for x in users:
        print(user_hash)
        if users[x]['user_hash'] == user_hash:
            print(users[x]['user_hash'])
            return {'username':users[x]['username'], 'profile_pic': users[x]['profile_pic'], 'birth_date': users[x]['birth_date'], 'studying_at': users[x]['studying_at']}
    
