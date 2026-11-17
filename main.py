import os
import json
import threading
import urllib.request
import ssl
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen

BASE_URL = "https://WALID12345.pythonanywhere.com"

def api_post(endpoint, payload_dict):
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    data = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=context, timeout=10) as res:
        return res.status, json.loads(res.read().decode("utf-8"))


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=30, spacing=20)
        title = Label(text="CREATE YOUR ACCOUNT", font_size=24, size_hint=(1, 0.25))
        self.name_input = TextInput(hint_text="Username (e.g. mundhir)", multiline=False, font_size=20, size_hint=(1, 0.15))
        self.status_lbl = Label(text="", font_size=16, color=(1, 1, 0, 1), size_hint=(1, 0.15))
        self.btn = Button(text="START", font_size=20, background_color=(0.2, 0.7, 0.3, 1), size_hint=(1, 0.15))
        self.btn.bind(on_press=self.register)
        layout.add_widget(Label(size_hint=(1, 0.15)))
        layout.add_widget(title)
        layout.add_widget(self.name_input)
        layout.add_widget(self.status_lbl)
        layout.add_widget(self.btn)
        layout.add_widget(Label(size_hint=(1, 0.15)))
        self.add_widget(layout)

    def register(self, instance):
        username = self.name_input.text.strip().lower()
        if not username:
            self.status_lbl.text = "Please write a name!"
            return
        self.btn.disabled = True
        self.status_lbl.text = "Connecting..."
        threading.Thread(target=self._do_register, args=(username,), daemon=True).start()

    def _do_register(self, username):
        try:
            status, res = api_post("/register", {"username": username})
            if status == 200 and res.get("status") == "OK":
                app = App.get_running_app()
                app.save_local_user(username)
                Clock.schedule_once(lambda dt: self.go_to_chat())
            else:
                Clock.schedule_once(lambda dt: self._error("Server Error"))
        except Exception as e:
            Clock.schedule_once(lambda dt: self._error("Connection Failed"))

    def _error(self, msg):
        self.status_lbl.text = msg
        self.btn.disabled = False

    def go_to_chat(self):
        self.manager.current = "chat"
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_friend = None
        self.last_msg_count = -1
        main_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        search_bar = BoxLayout(orientation="horizontal", size_hint=(1, 0.10), spacing=8)
        self.search_input = TextInput(hint_text="Search friend username...", multiline=False, font_size=18, size_hint=(0.72, 1))
        self.search_btn = Button(text="SEARCH", font_size=16, background_color=(0.2, 0.6, 1, 1), size_hint=(0.28, 1))
        self.search_btn.bind(on_press=self.search_friend)
        search_bar.add_widget(self.search_input)
        search_bar.add_widget(self.search_btn)

        self.tunnel_label = Label(text="Search for a friend to start chatting", font_size=16, color=(0.8, 0.8, 0.8, 1), size_hint=(1, 0.07))

        self.scroll = ScrollView(size_hint=(1, 0.68))
        self.messages_label = Label(text="", font_size=18, size_hint_y=None, halign="left", valign="top", markup=True)
        self.messages_label.bind(width=self._update_w, texture_size=self._update_h)
        self.scroll.add_widget(self.messages_label)

        bottom_bar = BoxLayout(orientation="horizontal", size_hint=(1, 0.15), spacing=8)
        self.msg_input = TextInput(hint_text="Write a message...", multiline=True, font_size=18, disabled=True, size_hint=(0.75, 1))
        self.send_btn = Button(text="SEND", font_size=18, disabled=True, background_color=(0.1, 0.8, 0.4, 1), size_hint=(0.25, 1))
        self.send_btn.bind(on_press=self.send_message)
        bottom_bar.add_widget(self.msg_input)
        bottom_bar.add_widget(self.send_btn)

        main_layout.add_widget(search_bar)
        main_layout.add_widget(self.tunnel_label)
        main_layout.add_widget(self.scroll)
        main_layout.add_widget(bottom_bar)
        self.add_widget(main_layout)
        Clock.schedule_interval(self.poll_messages, 2.5)

    def _update_w(self, instance, value):
        instance.text_size = (value - 20, None)

    def _update_h(self, instance, value):
        instance.height = value[1]

    def search_friend(self, instance):
        target = self.search_input.text.strip().lower()
        my_name = App.get_running_app().username
        if not target or target == my_name:
            self.tunnel_label.text = "Enter a valid friend username!"
            self.tunnel_label.color = (1, 0.3, 0.3, 1)
            return
        self.tunnel_label.text = f"Searching for '{target}'..."
        self.tunnel_label.color = (1, 1, 0, 1)
        threading.Thread(target=self._do_search, args=(target,), daemon=True).start()

    def _do_search(self, target):
        try:
            status, res = api_post("/search", {"target": target})
            if status == 200 and res.get("status") == "FOUND":
                Clock.schedule_once(lambda dt: self._open_tunnel(target))
            else:
                Clock.schedule_once(lambda dt: self._not_found(target))
        except:
            Clock.schedule_once(lambda dt: self._not_found(target))

    def _open_tunnel(self, target):
        self.current_friend = target
        self.last_msg_count = -1
        self.tunnel_label.text = f"Connected with: {target.upper()}"
        self.tunnel_label.color = (0, 1, 0, 1)
        self.msg_input.disabled = False
        self.send_btn.disabled = False
        self.messages_label.text = "Loading chat..."
        self.poll_messages(0)

    def _not_found(self, target):
        self.tunnel_label.text = f"User '{target}' not found!"
        self.tunnel_label.color = (1, 0.3, 0.3, 1)

    def send_message(self, instance):
        text = self.msg_input.text.strip()
        if not text or not self.current_friend:
            return
        my_name = App.get_running_app().username
        self.msg_input.text = ""
        threading.Thread(target=self._do_send, args=(my_name, self.current_friend, text), daemon=True).start()

    def _do_send(self, sender, receiver, text):
        try:
            api_post("/send_msg", {"sender": sender, "receiver": receiver, "text": text})
            Clock.schedule_once(lambda dt: self.poll_messages(0))
        except:
            pass

    def poll_messages(self, dt):
        if not self.current_friend:
            return
        my_name = App.get_running_app().username
        threading.Thread(target=self._fetch_msgs, args=(my_name, self.current_friend), daemon=True).start()

    def _fetch_msgs(self, user1, user2):
        try:
            status, res = api_post("/get_msgs", {"user1": user1, "user2": user2})
            if status == 200 and res.get("status") == "OK":
                msgs = res.get("messages", [])
                if len(msgs) != self.last_msg_count:
                    self.last_msg_count = len(msgs)
                    Clock.schedule_once(lambda dt: self._render_messages(msgs))
        except:
            pass

    def _render_messages(self, msgs):
        my_name = App.get_running_app().username
        lines = []
        for m in msgs:
            if m["sender"] == my_name:
                lines.append(f"[color=44ff44][b]You ({m['time']}):[/b][/color] {m['text']}")
            else:
                lines.append(f"[color=44aaff][b]{m['sender']} ({m['time']}):[/b][/color] {m['text']}")
        self.messages_label.text = "\n\n".join(lines) if lines else "No messages yet. Say Hi!"
        self.scroll.scroll_y = 0


class MiniInstaApp(App):
    def build(self):
        self.title = "Hind & Mundhir"
        self.user_file = os.path.join(self.user_data_dir, "account.json")
        self.username = self.load_local_user()
        sm = ScreenManager()
        sm.add_widget(RegisterScreen(name="register"))
        sm.add_widget(ChatScreen(name="chat"))
        sm.current = "chat" if self.username else "register"
        return sm

    def load_local_user(self):
        if os.path.exists(self.user_file):
            try:
                with open(self.user_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("username")
            except:
                return None
        return None

    def save_local_user(self, username):
        self.username = username
        os.makedirs(self.user_data_dir, exist_ok=True)
        with open(self.user_file, "w", encoding="utf-8") as f:
            json.dump({"username": username}, f)


if __name__ == "__main__":
    MiniInstaApp().run()
