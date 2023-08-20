import base64
import io
import json
import threading
from datetime import datetime
import re

import websocket
from kivy.animation import Animation
from kivy.config import Config
from kivy.lang import Builder
from kivy.network.urlrequest import UrlRequest
from kivy.properties import (
    BooleanProperty,
    DictProperty,
    ListProperty,
    StringProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import CoreImage
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton, MDRoundFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import (
    ImageLeftWidget,
    OneLineAvatarListItem,
    TwoLineListItem,
)
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.tab import MDTabsBase
from plyer import filechooser
import hashlib

# skemaionel problema = global
debug = False
Config.set('kivy', 'exit_on_escape', '0')
global listresult
global accountData
global image_base64
global mylistresult
global ws
global kick_id
global curr_group
global firstopen
global img_src
global owner_hash
global memberlist
firstopen = True

image_base64=''
kick_id = ''
api_url = "http://localhost:8000/api/"

buttonkv = '''
<Content>
    orientation: "vertical"
    spacing: "12dp"
    size_hint_y: None
    height: "180dp"


    MDTextField:
        id: group_name
        hint_text: "Group name"

    MDTextField:
        id: group_description
        hint_text: "Description"





'''

memberkv = '''
<Content1>
    orientation: "vertical"
    size_hint_y: None
    height: "180dp"
    MDLabel:
        font_size: 20
        id: member_name
        halign: 'center'
        text: 'egg'
        valign: "middle"
    MDLabel:
        font_size: 20
        id: member_studying
        halign: 'center'
        text: 'egg'
        valign: "middle"
    MDLabel:
        font_size: 20
        id: member_date
        halign: 'center'
        text: 'egg'
        valign: "middle"
    MDRoundFlatButton:
        id: kick_btn
        text: "KICK"
        font_size: 12
        pos_hint: {"center_x": 0.5}
        on_press: app.kick()
'''
class ChatBubble(MDLabel):
    send_by_user = BooleanProperty()

class OneLineAvatarListItem(OneLineAvatarListItem):
    owner = BooleanProperty()

class Tab(MDFloatLayout, MDTabsBase):
    pass

class MyList(MDScreen):
    pass

class Main(MDScreen):
    pass


class LoginWindow(MDScreen):
    pass


class RegisterWindow(MDScreen):
    pass


class FirstLoginSetup(MDScreen):
    pass


class WindowManager(MDScreenManager):
    pass


class Content(BoxLayout):
    pass

class Content1(BoxLayout):
    pass

class ListItem(MDScreen):
    pass




class MainApp(MDApp):
    dialog = None
    user = DictProperty()
    title = StringProperty()
    chat_logs = ListProperty()



    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        Builder.load_string(memberkv)
        return Builder.load_file('login.kv')



    def on_message(self,ws, message):
        self.receive(message)


    def start_websocket(self,group_id):
        global ws
        global localId
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp(
            f"ws://localhost:8000/ws?auth_id={localId}&group_id={group_id}",
            on_message=self.on_message,
        )
        wsthread = threading.Thread(target=ws.run_forever)
        wsthread.start()

    def kick(self):
        global localId
        global kick_id
        global curr_group
        if kick_id:
            req1 = UrlRequest(f"{api_url}kick_user?auth_id={localId}&user_hash={kick_id}&group_id={curr_group}")
            req1.wait(delay=0)
            result1 = req1.result
    def memberPress(self,object):
        global kick_id
        req1 = UrlRequest(f"{api_url}get_userinfo?user_hash={object.id}")
        req1.wait(delay=0)
        result1 = req1.result
        kick_id = object.id
        self.dialog1 = MDDialog(
            type="custom",
            content_cls=Content1(),
            buttons=[
            ],
        )
        username = result1['username']
        studying = result1['studying_at']
        bd = result1['birth_date']
        self.dialog1.content_cls.ids.member_name.text = f'Name: {username}'
        self.dialog1.content_cls.ids.member_studying.text = f'Studying at: {studying}'
        self.dialog1.content_cls.ids.member_date.text = f'Birth date: {bd}'
        self.dialog1.content_cls.ids.kick_btn.opacity = 1

        authid_hash = hashlib.sha1(localId.encode("UTF-8")).hexdigest()
        if authid_hash == owner_hash and '(Owner)' not in object.text:
            self.dialog1.content_cls.ids.kick_btn.opacity = 1
        else:
            self.dialog1.content_cls.ids.kick_btn.opacity = 0
        res = bytes(result1['profile_pic'], 'utf-8')

        self.dialog1.open()

    def deleteGroup(self,object):
        global localId
        global curr_group
        req = UrlRequest(f"{api_url}delete_group?auth_id={localId}&group_id={curr_group}")
        req.wait(delay=0)
        result = req.result
        self.populateList()
        self.populate_myList()
        self.root.current = "main"


    def listPress(self, object):
        global listresult
        global mylistresult
        global localId
        global ws
        global curr_group
        global owner_hash
        global memberlist
        authid_hash = hashlib.sha1(localId.encode("UTF-8")).hexdigest()
        curr_group = object.id
        self.chat_logs=[]
        self.start_websocket(object.id)
        self.root.get_screen('listitem').ids.group_members.clear_widgets()
        self.root.get_screen('listitem').id = object.id
        self.root.current = "listitem"
        req1 = UrlRequest(api_url + "get_messages?auth_id=" + localId + "&group_id=" + object.id)
        req1.wait(delay=0)
        result1 = req1.result
        if result1!='Internal Server Error' and result1:
            for message in result1:
                if result1[message]['sender_hash'] == authid_hash:
                    self.chat_logs.append(
                        {
                            "text": f"({datetime.utcfromtimestamp(int(result1[message]['message_date'])).strftime('%H:%M')}){result1[message]['username']}: {result1[message]['message']}",
                            "send_by_user": True,
                            "pos_hint": {"right": 1},
                        }
                    )
                else:
                    self.chat_logs.append(
                        {
                            "text": f"({datetime.utcfromtimestamp(int(result1[message]['message_date'])).strftime('%H:%M')}){result1[message]['username']}: {result1[message]['message']}",
                            "send_by_user": False,
                        }
                    )
        req = UrlRequest(api_url + "get_groupmembers?auth_id=" + localId + "&group_id=" + object.id)
        req.wait(delay=0)
        result = req.result
        memberlist = result
        in_group = any(i['authid_hash'] == authid_hash for i in result)

        if not in_group:
            self.root.get_screen('listitem').ids.field.height = '0'
            self.root.get_screen('listitem').ids.send.opacity= '0'
            self.root.get_screen('listitem').ids.topbar.right_action_items=[["door",self.joinGroup]]
        else:
            self.root.get_screen('listitem').ids.topbar.right_action_items=[["door-open",self.leaveGroup]]
        if result != 'Internal Server Error':
            self.root.get_screen('listitem').ids.group_members.clear_widgets()
            for i in result:
                if authid_hash == i['authid_hash'] and i['is_owner']:
                    self.root.get_screen('listitem').ids.topbar.right_action_items = [["delete",self.deleteGroup]]
                if i['profile_pic']:
                    res = bytes(i['profile_pic'], 'utf-8')
                    data = base64.decodebytes(res)
                    data1 = io.BytesIO(data)
                    img = CoreImage(data1, ext="png").texture
                else:
                    img = "pfp.png"
                text = i['username']
                if i['is_owner'] == True:
                    owner_hash= i['authid_hash']
                    text += '(Owner)'

                self.root.get_screen('listitem').ids.group_members.add_widget(
                    OneLineAvatarListItem(ImageLeftWidget(source=img), text=f"{text}", on_press=self.memberPress,id=i['authid_hash'],owner=i['is_owner']))

    def MylistPress(self,object):
        global mylistresult
        self.root.current = 'mylist'

    def populate_myList(self):
        global mylistresult
        global localId
        req = UrlRequest(f"{api_url}get_mygroups?auth_id={localId}")
        req.wait(delay=0)
        result = req.result
        mylistresult =result
        self.root.get_screen('main').ids.group_list1.clear_widgets()
        if result != 'Internal Server Error':
            for i in result:
                self.root.get_screen('main').ids.group_list1.add_widget(
                    TwoLineListItem(text=f"{result[i]['group_name']}",
                                    secondary_text=f"{result[i]['group_description']}", on_press=self.listPress, id=i)
                )

    def populateList(self):
        global localId
        global listresult
        req = UrlRequest(f"{api_url}get_groups?auth_id={localId}")
        req.wait(delay=0)
        result = req.result
        listresult = result
        self.root.get_screen('main').ids.group_list.clear_widgets()
        if result != 'Internal Server Error':
            for i in result:
                self.root.get_screen('main').ids.group_list.add_widget(
                    TwoLineListItem(text=f"{result[i]['group_name']}",
                                    secondary_text=f"{result[i]['group_description']}", on_press=self.listPress, id=i)
                )

    def createGroup(self, group_name, group_desc):
        global localId
        if group_name and group_desc:
            data = {'group_name': group_name, 'group_description': group_desc}
            json_data = json.dumps(data)
            req = UrlRequest(
                f"{api_url}create_group?auth_id={localId}", req_body=json_data
            )
            self.populateList()
            self.populate_myList()

    def joinGroup(self,object):
        global localId
        global accountData
        authid_hash = hashlib.sha1(localId.encode("UTF-8")).hexdigest()
        data = {'group_id': self.root.get_screen('listitem').id}
        json_data = json.dumps(data)
        req = UrlRequest(f"{api_url}join_group?auth_id={localId}", req_body=json_data)
        req.wait(delay=0)
        result = req.result
        self.root.get_screen('listitem').ids.field.height = '50dp'
        self.root.get_screen('listitem').ids.send.opacity = '1'
        self.root.get_screen('listitem').ids.topbar.right_action_items=[["door-open",self.leaveGroup],["dots-vertical"]]
        self.populateList()
        self.populate_myList()
        if accountData['profile_pic']:
            res = bytes(accountData['profile_pic'], 'utf-8')
            data = base64.decodebytes(res)
            data1 = io.BytesIO(data)
            img = CoreImage(data1, ext="png").texture
            self.root.get_screen('listitem').ids.group_members.add_widget(
                OneLineAvatarListItem(ImageLeftWidget(source=img), text=f"{accountData['username']}", on_press=self.MylistPress,id=authid_hash))
        else:
            self.root.get_screen('listitem').ids.group_members.add_widget(
                OneLineAvatarListItem(ImageLeftWidget(source='pfp.png'), text=f"{accountData['username']}",
                                      on_press=self.MylistPress, id=authid_hash))

    def leaveGroup(self,object):
        authid_hash = hashlib.sha1(localId.encode("UTF-8")).hexdigest()
        data = {'group_id': self.root.get_screen('listitem').id}
        json_data = json.dumps(data)
        req = UrlRequest(f"{api_url}leave_group?auth_id={localId}", req_body=json_data)
        req.wait(delay=0)
        result = req.result
        self.root.get_screen('listitem').ids.field.height = '0'
        self.root.get_screen('listitem').ids.send.opacity = '0'
        self.root.get_screen('listitem').ids.topbar.right_action_items = [["door", self.joinGroup], ["dots-vertical"]]
        for widget in self.root.get_screen('listitem').ids.group_members.children:
            if widget.id == authid_hash:
                self.root.get_screen('listitem').ids.group_members.remove_widget(widget)



    def send(self, text):
        global accountData
        if not text:
            return
        currentTime = datetime.now().strftime("%H:%M")

        ws.send(text)
        self.chat_logs.append(
            {
                "text": f"({currentTime}){accountData['username']}: {text}",
                "send_by_user": True,
                "pos_hint": {"right": 1},
            }
        )


    def receive(self, text):
        global localId
        global memberlist
        text = json.loads(text)
        authid_hash = hashlib.sha1(localId.encode("UTF-8")).hexdigest()
        currentTime = datetime.now().strftime("%H:%M")
        for x in memberlist:
            if x['authid_hash']==text['authid_hash']:
                username = x['username']
        if text['authid_hash']!= authid_hash:
            self.chat_logs.append(
                {
                    "text": f"({currentTime}){username}: {text['message']}",
                    "send_by_user": False,
                }
            )

    def scroll_to_bottom(self):
        rv = self.root.get_screen('listitem').ids.chat_rv
        box = self.root.get_screen('listitem').ids.box
        if rv.height < box.height:
            Animation.cancel_all(rv, "scroll_y")
            Animation(scroll_y=0, t="out_quad", d=0.5).start(rv)

    def on_tab_switch(self, instance_tabs, instance_tab, instance_tab_label, tab_text):
        id = self.root.get_screen('listitem').id
        

    def coaie(self, touch):
        pass

    def logger(self):
        global accountData
        global localId
        if debug:
            email = "test@gmail.com"
            password = "123456"
        else:
            email = self.root.get_screen('login').ids.user.text
            password = self.root.get_screen('login').ids.password.text
        err='a'
        if not re.match(r"^\S+@\S+\.\S+$", email):
            err +='Input a valid email'
        if len(password)<6:
            if err:
                err+=', password must be at least 6 characters'
            else:
                err='Password must be at least 6 characters'
        data = {'email': email, 'password': password}
        json_data = json.dumps(data)
        req = UrlRequest(f"{api_url}login", req_body=json_data)
        req.wait(delay=0)
        result = req.result
        status = req.resp_status

        if status!=500:
            localId = result['local']
            accountData = result['acc_data']
            self.root.current = "main"
            self.populateList()
        else:
            self.root.get_screen('login').ids.error_text.text = err
            self.root.get_screen('login').ids.error_text.opacity = 1

    def register(self):
        self.root.current = "register"

    def register_next(self):
        self.root.current = "loginsetup"

    def register_button_press(self):
        self.root.get_screen('register').ids.reg_error_text.opacity = 0
        email = self.root.get_screen('register').ids.reg_user.text
        password = self.root.get_screen('register').ids.reg_password.text
        err=''
        if not re.match(r"^\S+@\S+\.\S+$", email):
            err +='Input a valid email'
        if len(password)<6:
            if err:
                err+=', password must be at least 6 characters'
            else:
                err='Password must be at least 6 characters'
        if not err:
            self.root.current = "loginsetup"
        else:
            self.root.get_screen('register').ids.reg_error_text.text = err
            self.root.get_screen('register').ids.reg_error_text.opacity = 1

    def on_save(self, instance, value, date_range):
        self.root.get_screen('loginsetup').ids.date.text = str(value)

    def show_date_picker(self):
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.on_save)
        date_dialog.open()

    def finish_login(self):
        global localId
        global accountData
        email = self.root.get_screen('register').ids.reg_user.text
        password = self.root.get_screen('register').ids.reg_password.text
        username = self.root.get_screen('loginsetup').ids.username.text
        bd = self.root.get_screen('loginsetup').ids.date.text
        study = self.root.get_screen('loginsetup').ids.study_field.text
        data = {'email': email, 'password': password, 'username': username, 'birth_date': bd, 'studying_at': study}
        json_data = json.dumps(data)
        req = UrlRequest(f"{api_url}register", req_body=json_data, method='POST')
        req.wait(delay=0)
        result = req.result
        accountData = result['acc_data']
        localId = result['local']
        self.root.current = "main"

    def reg_back(self):
        self.root.current = 'login'

    def logout(self):
        global accountData
        global localId
        accountData = []
        localId = ''
        self.root.get_screen('login').ids.error_text.opacity = 0
        self.root.current = "login"
        self.root.get_screen('register').ids.reg_error_text.opacity = 1

    def populate_profile(self):
        global accountData
        global firstopen
        self.root.get_screen('main').ids.username_edit.text = accountData['username']
        self.root.get_screen('main').ids.date_edit.text = accountData['birth_date']
        self.root.get_screen('main').ids.studying_at_edit.text = accountData['studying_at']
        avatar_object = self.root.get_screen('main').ids.avatar_image.canvas.get_group('a')[0]
        if firstopen:
            if accountData['profile_pic']:
                res = bytes(accountData['profile_pic'], 'utf-8')
                with open("a.png", "wb") as fh:
                    fh.write(base64.decodebytes(res))
                avatar_object.source = 'a.png'
            else:
                avatar_object.source = 'pfp.png'
        firstopen = False
    def file_chooser(self):
        filechooser.open_file(on_selection=self.selected)

    def mainscreen(self):
        global ws
        ws.close()
        self.root.current = "main"
        self.root.get_screen('listitem').ids.field.text=''

    def selected(self, selection):
        global image_base64
        if selection:
            avatar_object = self.root.get_screen('main').ids.avatar_image.canvas.get_group('a')[0]
            avatar_object.source = selection[0]
            img_src = selection[0]
            with open(selection[0], "rb") as img_file:
                image_base64 = base64.b64encode(img_file.read())

    def saveProfile(self):
        global accountData
        global localId
        global image_base64
        username = None
        date = None
        studying = None
        if accountData['username'] != self.root.get_screen('main').ids.username_edit.text:
            username = self.root.get_screen('main').ids.username_edit.text
            accountData['username'] = username
        if accountData['birth_date'] !=  self.root.get_screen('main').ids.date_edit.text:
            date = username = self.root.get_screen('main').ids.username_edit.text
            accountData['birth_date'] = date
        if accountData['studying_at'] != self.root.get_screen('main').ids.studying_at_edit.text:
            studying = self.root.get_screen('main').ids.studying_at_edit.text
            accountData['studying_at'] = studying
        data = {'username': username, 'birth_date': date, "studying_at": studying}
        if image_base64:
            data['profile_pic'] = str(image_base64)[2:]
        json_data = json.dumps(data)
        req = UrlRequest(
            f"{api_url}edit_account?auth_id={localId}", req_body=json_data
        )
        req.wait(delay=0)
        result = req.result

    def on_request_close(self, *args):
        global ws
        ws.close()
        return True

    def show_confirmation_dialog(self):
        if not self.dialog:
            Builder.load_string(buttonkv)
            self.dialog = MDDialog(
                title="Create a group:",
                type="custom",
                content_cls=Content(),
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda _: self.dialog.dismiss()
                    ),
                    MDFlatButton(
                        text="CREATE",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda _: [self.createGroup(self.dialog.content_cls.ids.group_name.text,
                                                              self.dialog.content_cls.ids.group_description.text,
                                                              ),self.dialog.dismiss()]
                    ),
                ],
            )
        self.dialog.open()


MainApp().run()
