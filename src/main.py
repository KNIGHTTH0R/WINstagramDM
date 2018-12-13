#!/usr/bin/env python3

import threading
import time
import webbrowser
import requests
import json
import tkinter as tk
from io import BytesIO

from PIL import Image, ImageTk, ImageOps, ImageDraw
import InstagramAPI

import api

class Chat:

    def __init__(self, app, entry, threadId, users):
        self.usr = app.usr
        self.entry = entry
        self.threadId = threadId
        self.users = users
        self.app = app
        self.last_msgs = []
        self.pending_msgs = []

        get_user_pics_thread = threading.Thread(target=self.get_user_pics)
        get_user_pics_thread.daemon = True
        get_user_pics_thread.start()

    def get_user_pics(self):
        #BUG: Pfps sometimes not loaded
        usr_pics = {} #{pk: profile_pic_url}
        for user in self.users + [self.app.usr_name]:
            self.usr.api.searchUsername(user)
            response = json.loads(json.dumps(self.usr.api.LastJson))
            pfp_url = response["user"]["profile_pic_url"]

            img_response = requests.get(pfp_url)
            tmp_img = Image.open(BytesIO(img_response.content))
            tmp_img = tmp_img.resize((50, 50))
            #Generate mask for circularising image
            mask = Image.new("L", (50, 50), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + mask.size, fill=255)
            tmp_img = ImageOps.fit(tmp_img, mask.size, centering=(.5, .5))
            tmp_img.putalpha(mask)
            image = ImageTk.PhotoImage(tmp_img)

            usr_pics[response["user"]["pk"]] = image

        self.usr_pics = usr_pics

    def get_msgs(self):
        while True:
            try:
                msgs = self.usr.getMessages(self.threadId)
                if msgs != self.last_msgs:
                    new_msgs = []
                    for msg in msgs:
                        new_msgs.append(tk.Label(
                            self.app.canvas_frame,
                            text=" " * 4 + msg["text"]))
                        new_msgs[-1].config(
                            anchor=tk.W,
                            compound=tk.LEFT,
                            image=self.usr_pics[msg["user"]],
                            bg="#222",
                            fg="#ccc"
                        )
                        new_msgs[-1].item_id = msg["item_id"]
                        new_msgs[-1].thread_id = self.threadId
                        new_msgs[-1].unsendable = msg["user"] == self.app.usr_pk


                    self.pending_msgs = new_msgs[::-1] #invert to fix packing of recently-sent messages

            except AttributeError:
                pass

    def send_msg(self):

        msg = self.entry.get()
        self.entry.delete(0, "end")
        self.entry.config(state="disabled")

        if self.app.inf_spam["text"] == "Infinite spam":
            self.app.stop_spam.config(state="normal")
            self.app.back.config(state="disabled")
            self.app.inf_spam.config(state="disabled")
            self.stop_spam = False
            while True:
                if self.stop_spam:
                    break

                self.usr.sendMessage(self.users, msg)

        else:
            self.usr.sendMessage(self.users, msg)

        self.entry.config(state="normal")
        self.app.stop_spam.config(state="disabled")
        self.app.back.config(state="normal")
        self.app.inf_spam.config(state="normal")
        #Reset thread
        self.send_msg_thread = threading.Thread(target=self.send_msg)
        self.send_msg_thread.daemon = True

class App:

    def __init__(self):

        def attempt_login():
            self.root.title("WinstagramDM - Logging in")
            self.usr_name = usr_login.get()
            password = psswd.get()
            #disable editing while logging in
            usr_login.config(state="disabled")
            psswd.config(state="disabled")
            login.config(state="disabled")

            self.usr = api.User(self.usr_name, password)

            if self.usr.api.login():
                self.usr.api.searchUsername(self.usr_name)
                self.usr_pk = self.usr.api.LastJson["user"]["pk"]
                self.root.quit()
                self.logged_in = True

            else:

                if json.loads(json.dumps(self.usr.api.LastJson))["message"] == "challenge_required":
                    webbrowser.open(json.loads(json.dumps(self.usr.api.LastJson))["challenge"]["url"], new=2)
                    if self.usr.api.login():
                        self.usr.api.searchUsername(self.usr_name)
                        self.usr_pk = self.api.LastJson["user"]["pk"]
                        self.root.quit()
                        self.logged_in = True
                        return 0

                usr_login.config(state="normal")
                psswd.config(state="normal")
                login.config(state="normal")
                psswd.delete(0, "end")
                psswd.config(show="")
                psswd.insert(0, "Password")

                try:
                    del self.psswd_cleared
                except AttributeError:
                    pass

                self.root.title("WinstagramDM - Login")
                #Resetup login thread to allow rerun
                self.login_thread = threading.Thread(target=attempt_login)
                self.login_thread.daemon = True
                return 1

        def clear_entry(event):
            try:
                self.usr_name_cleared

            except AttributeError:
                event.widget.delete(0, "end")
                self.usr_name_cleared = True

        def clear_entry_psswd(event):
            try:
                self.psswd_cleared
                event.widget.config(show="●")

            except AttributeError:
                event.widget.delete(0, "end")
                self.psswd_cleared = True
                event.widget.config(show="●")

            event.widget.config(show="●")

        self.location = "login"

        self.root = tk.Tk()
        self.root.title("WinstagramDM - Login")
        self.root.wm_iconbitmap("icon.ico")
        self.root.geometry(newGeometry=("500x500")) #Sizing
        self.root.minsize(500, 500)
        self.root.maxsize(500, 500)
        self.root.update()

        #Setup attempt_login thread
        self.login_thread = threading.Thread(target=attempt_login)
        self.login_thread.daemon = True
        self.logged_in = False

        usr_login = tk.Entry()
        usr_login.insert(0, "Username")
        usr_login.bind("<Button-1>", clear_entry)
        usr_login.bind("<Key>", clear_entry)
        usr_login.bind("<Return>",
                    lambda event: self.login_thread.start())
        usr_login.place(relx=.5, rely=.475, anchor="center")

        psswd = tk.Entry()
        psswd.insert(0, "Password")
        psswd.bind("<Button-1>", clear_entry_psswd)
        psswd.bind("<Key>", clear_entry_psswd)
        psswd.bind("<Return>",
                    lambda event: self.login_thread.start())
        psswd.place(relx=.5, rely=.525, anchor="center")

        login = tk.Button(command=lambda: self.login_thread.start())
        login["text"] = "Login"
        login.place(relx=.44, rely=.555)

        #Styling
        font = ("Helvetica", 13)
        self.root.config(background="#000")
        usr_login.config(
                            background="#222",
                            fg="#ddd",
                            bd=0,
                            font=font)
        psswd.config(background="#222",
                        fg="#ddd",
                        bd=0,
                        font=font)
        login.config(background="#222",
                        fg="#ddd",
                        bd=0,
                        font=font)

        self.root.mainloop()
        #Clear icons
        usr_login.place_forget()
        psswd.place_forget()
        login.place_forget()
        self.homepage()

    def homepage(self):

        def getChats():
            chats = []
            self.pending_chats = None
            self.sleep_required = False
            self.clear_required = False
            while True:

                if self.sleep_required:
                    time.sleep(60)
                    self.sleep_required = False
                    self.clear_required = True

                if self.location != "homepage":
                    break

                new_chats = self.usr.getChats()
                self.num_required_chats = len(new_chats)

                if new_chats != chats:
                    if self.pending_chats == None:
                        self.pending_chats = [tk.Button(
                            self.canvas_frame,
                            text=" " * 16 + "New Chat",
                            command=self.new_convo,
                            font=("Helvetica", 12)
                        )]
                        self.pending_chats[-1].config(
                            bd=1,
                            anchor=tk.W,
                            bg="#222",
                            fg="#ccc"
                        )

                    else:
                        continue

                    for chat in new_chats:

                        #Get thread icon
                        response = requests.get(chat["thread_icon"])
                        font = ("Helvetica", 10)

                        if response.status_code == 200: #Check image received ok
                            tmp_img = Image.open(BytesIO(response.content))
                            tmp_img = tmp_img.resize((50, 50))
                            #Generate mask for circularising image
                            mask = Image.new("L", (50, 50), 0)
                            draw = ImageDraw.Draw(mask)
                            draw.ellipse((0, 0) + mask.size, fill=255)
                            tmp_img = ImageOps.fit(tmp_img, mask.size, centering=(.5, .5))
                            tmp_img.putalpha(mask)
                            image = ImageTk.PhotoImage(tmp_img)

                            self.pending_chats.append(tk.Button(
                                self.canvas_frame,
                                text="    " + chat["thread_name"],
                                command=lambda thread_id=chat["thread_id"], users=chat["users"]: self.convo_run(thread_id, users),
                                font=font))

                            self.pending_chats[-1].image = image
                            self.pending_chats[-1].config(compound=tk.LEFT,
                                               image=image,
                                               anchor=tk.W,
                                               bd=1,
                                               highlightbackground="#333",
                                               bg="#222",
                                               fg="#ccc")

                        else: #Offer alternative if image not received
                            self.pending_chats.append(tk.Button(
                                self.canvas_frame,
                                text="    " + chat["thread_name"],
                                command=lambda: self.convo_run(str(chat["thread_id"]), list(chat["users"]))))

                            self.pending_chats[-1].config(
                                bd=1,
                                anchor=tk.W,
                                bg="#222",
                                fg="#ccc")

        def clear_chats():
            #clear all buttons
            for button in self.canvas_frame.winfo_children():
                button.destroy()
            self.pending_chats = None

        def update_chats():

            if self.location != "homepage":
                return 0

            try:

                if self.clear_required: #Check clearing
                    clear_chats()
                    self.clear_required = False

                if len(self.pending_chats) > self.num_required_chats: #Check for repetition
                    self.sleep_required = True

                if self.sleep_required:
                    return 0 #Not needed

                #Update widths
                for button in self.canvas_frame.winfo_children():
                    width = int(self.root.geometry()[:self.root.geometry().index("x")])
                    button.config(width=width)

                for chat_button in self.pending_chats:
                    try:
                        chat_button.pack(fill=tk.X)
                    except:
                        pass

            except TypeError:
                pass #Hasn"t loaded yet

            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            self.root.after(10, update_chats)

        def scrollbar_update():
            self.canvas.config(scrollregion=ox("all"))

        def mouse_scroll(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        #Setup window
        for item in self.root.winfo_children():
            item.destroy()

        self.location = "homepage" #Used for checking in threads
        self.root.title("WinstagramDM - Homepage")
        self.root.config(background="#000")
        self.root.maxsize(self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        self.root.update()

        #setup canvas
        self.canvas = tk.Canvas(self.root, scrollregion=(0,0,500,500), background="#000", bd=0, highlightthickness=0)
        self.canvas_frame = tk.Frame(self.canvas, background="#000", bd=0, highlightthickness=0)
        #Setup scrollbar
        self.vscroll = tk.Scrollbar(self.root, orient=tk.VERTICAL)
        self.vscroll.config(command=self.canvas.yview)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        self.canvas.config(yscrollcommand=self.vscroll.set)
        self.canvas.pack(fill="both", expand=True)
        self.canvas_frame.pack(fill="both", expand=True)
        self.canvas.create_window((0,0), window=self.canvas_frame, anchor="nw")
        self.root.bind_all("<MouseWheel>", mouse_scroll)
        self.canvas_frame.bind("<Configure>", lambda event: scrollbar_update)
        #Styling
        self.canvas_frame.config(bd=0)
        self.canvas.config(bd=0)

        getChatsThread = threading.Thread(target=getChats)
        getChatsThread.daemon = True
        getChatsThread.start()

        self.root.after(1, update_chats) #update chat initial run
        self.root.mainloop()

    def new_convo(self):

        def check_user():
            self.target = user_select.get()
            msg_text = msg_entry.get()

            if None in (self.target, msg_text):
                self.check_send_thread = threading.Thread(target=check_user)
                self.check_send_thread.daemon = True
                return 1

            user_select.config(state="disabled")
            msg_entry.config(state="disabled")
            start_convo.config(state="disabled")

            if type(self.target) != type([]):
                self.target = self.target.split(',')

            self.targets = []
            for target in self.target:
                self.usr.api.searchUsername(target)

                try:
                    self.usr.api.LastJson["user"]["pk"]
                    self.targets.append(target)
                except:
                    self.exists = False
                    self.usr_select_cleared = False
                    self.msg_entry_cleared = False
                    break

            else:
                self.usr.sendMessage(self.targets, msg_text)
                self.usr.api.getv2Inbox()
                self.thread_id = json.loads(self.usr.api.LastResponse.content)["inbox"]["threads"][-1]["thread_id"]
                self.exists = True

            self.check_send_thread = threading.Thread(target=check_user)
            self.check_send_thread.daemon = True

        def try_chat():
            try:
                if self.exists:
                    self.convo_run(self.thread_id, self.targets)

                else:
                    user_select.config(state="normal")
                    msg_entry.config(state="normal")
                    start_convo.config(state="normal")
                    if not self.usr_select_cleared:
                        user_select.delete(0, "end")
                        user_select.insert(0, "Target user(s)")

                    if not self.msg_entry_cleared:
                        msg_entry.delete(0, "end")
                        msg_entry.insert(0, "Message")


            except AttributeError:
                pass

            self.root.after(100, try_chat)

        def clear_usr_select():
            try:
                if not self.usr_select_cleared:
                    user_select.delete(0, "end")
                    self.usr_select_cleared = True
            except AttributeError:
                self.usr_select_cleared = False
                clear_usr_select()

        def clear_msg_entry():
            try:
                if not self.msg_entry_cleared:
                    msg_entry.delete(0, "end")
                    self.msg_entry_cleared = True
            except AttributeError:
                self.msg_entry_cleared = False
                clear_msg_entry()

        self.root.after(100, try_chat)
        self.root.title("WinstagramDM - New chat")
        self.location = "newchat"

        for item in self.root.winfo_children():
            item.destroy()

        self.check_send_thread = threading.Thread(target=check_user)
        self.check_send_thread.daemon = True
        self.root.after(100, try_chat)

        user_select = tk.Entry(self.root)
        user_select.config(
            bg="#222",
            fg="#ccc",
            font=("Helvetica", 15)
        )
        user_select.insert(0, "Target user(s)")

        msg_entry = tk.Entry(self.root)
        msg_entry.config(
            bg="#222",
            fg="#ccc",
            font=("Helvetica", 15)
        )
        msg_entry.insert(0, "Message")

        start_convo = tk.Button(self.root, command=self.check_send_thread.start, text="Start chat")
        start_convo.config(
            bg="#222",
            fg="#ccc",
            font=("Helvetica", 15)
        )


        user_select.pack(side=tk.TOP, fill=tk.X)
        msg_entry.pack(side=tk.TOP, fill=tk.X)
        start_convo.pack(side=tk.TOP, fill=tk.X)

        user_select.bind("<Return>", lambda event: self.check_send_thread.start())
        user_select.bind("<Key>", lambda event: clear_usr_select())
        user_select.bind("<Button-1>", lambda event: clear_usr_select())
        msg_entry.bind("<Return>", lambda event: self.check_send_thread.start())
        msg_entry.bind("<Key>", lambda event: clear_msg_entry())
        msg_entry.bind("<Button-1>", lambda event: clear_msg_entry())
        start_convo.bind("<Return>", lambda event: self.check_send_thread.start())
        start_convo.bind("<Key>", lambda event: self.check_send_thread.start())

        self.root.mainloop()

    def convo_run(self, threadId, users):

        #TODO: find some way of adding timestamp in small text in bottom corner
        #Maybe make each message a frame with multiple text widgets on it?

        def copy(event):
            self.root.clipboard_clear()
            self.root.clipboard_append(event.widget["text"])
            self.root.update()

        def scrollbar_update():
            self.canvas.config(scrollregion=self.canvas.bbox("all"))

        def update_convo():
            try:
                for msg in chat.pending_msgs:
                    if msg.item_id not in chat.last_msgs:
                        msg.pack(side=tk.TOP, fill=tk.X)
                        chat.last_msgs.append(msg.item_id)

                chat.pending_msgs = []

            except AttributeError as e:
                print(e)

            #Autoscroll
            if self.vscroll.get()[1] >= .8 and chat.pending_msgs != []:
                self.canvas.yview_moveto(1) #Move to bottom if almost there already

            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            self.root.after(100, update_convo)

        def toggle_spam():
            if self.inf_spam["text"] == "Infinite spam":
                self.inf_spam["text"] = "Single message"

            elif self.inf_spam["text"] == "Single message":
                self.inf_spam["text"] = "Infinite spam"

        def end_spam():
            chat.stop_spam = True

        def mouse_scroll(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def popup(event):
            #Clear menu
            self.menu = tk.Menu(self.canvas_frame, tearoff=0) #Commands added in popup

            if type(event.widget) == tk.Label:
                self.menu.add_command(label="Copy", command=lambda event=event: copy(event))
                if event.widget.unsendable:
                    unsend_thread = threading.Thread(target=lambda thread_id=event.widget.thread_id, item_id=event.widget.item_id: self.usr.unsend(thread_id, item_id))
                    self.menu.add_command(label="Unsend", command=unsend_thread.start)
                self.menu.post(event.x_root, event.y_root)

        #Clear all widgets
        for item in self.root.winfo_children():
            item.destroy()

        self.location = "convorun"

        title = "WinstagramDM - Chatting with "
        for user in users:
            title += str(user) + " "
        self.root.title(title)

        self.root.update()

        msg_in = tk.Entry(self.root)
        msg_in.config(
            bg="#222",
            fg="#ccc",
            font=("Helvetica", 12)
        )
        msg_in.pack(side=tk.BOTTOM, fill=tk.X)
        msg_in.focus_set()


        chat = Chat(self, msg_in, threadId, users)

        self.inf_spam = tk.Button(self.root, text="Single message", command=toggle_spam)
        self.inf_spam.config(
            bg="#222",
            fg="#ccc",
            font=("Helvetica", 12)
        )
        self.stop_spam = tk.Button(self.root, text="Stop spam", state="disabled", command=end_spam)
        self.stop_spam.config(
            bg="#222",
            fg="#ccc",
            font=("Helvetica", 12)
        )
        self.back = tk.Button(self.root, text="Return to homepage", command=self.homepage)
        self.back.config(
            bg="#222",
            fg="#ccc",
            font=("Helvetica", 12)
        )
        self.inf_spam.pack(side=tk.BOTTOM, fill=tk.X)
        self.stop_spam.pack(side=tk.BOTTOM, fill=tk.X)
        self.back.pack(side=tk.BOTTOM, fill=tk.X)

        #setup canvas/scrollbar
        self.canvas = tk.Canvas(self.root, scrollregion=(0,0,500,500), background="#000", bd=0, highlightthickness=0)
        self.canvas_frame = tk.Frame(self.canvas, background="#000", bd=0, highlightthickness=0)
        #Setup scrollbar
        self.vscroll = tk.Scrollbar(self.root, orient=tk.VERTICAL)
        self.vscroll.config(command=self.canvas.yview)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        self.canvas.config(yscrollcommand=self.vscroll.set)
        self.canvas.pack(fill="both", expand=True)
        self.canvas_frame.pack(fill="both", expand=True)
        self.canvas.yview_moveto(1)
        self.canvas.create_window((0,0), window=self.canvas_frame, anchor="nw")
        self.root.bind_all("<MouseWheel>", mouse_scroll)
        self.root.bind_all("<Configure>", lambda event: scrollbar_update)
        #Styling
        self.canvas_frame.config(bd=0)
        self.canvas.config(bd=0)

        #Setup right click self.menu
        self.menu = tk.Menu(self.canvas_frame, tearoff=0) #Commands added in popup
        self.canvas_frame.bind_all("<Button-3>", popup)

        #Thread setup
        get_msg_thread = threading.Thread(target=chat.get_msgs)
        get_msg_thread.daemon = True
        get_msg_thread.start()

        chat.send_msg_thread = threading.Thread(target=chat.send_msg)
        chat.send_msg_thread.daemon = True

        #Bindings
        msg_in.bind("<Return>", lambda event: chat.send_msg_thread.start())

        self.root.after(100, update_convo)
        self.root.mainloop()

def main():
    try:
        app = App()
    except: #Handle exiting
        pass

if __name__ == "__main__":
    main()