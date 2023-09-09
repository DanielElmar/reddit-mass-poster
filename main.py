import configparser
import json
import os
import re
import shutil

import customtkinter
from tkinter import filedialog as fd, filedialog

import praw
from PIL import Image
from tkinterdnd2 import TkinterDnD, DND_FILES

customtkinter.set_appearance_mode("dark")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green


class Tk(customtkinter.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class App(Tk):
    def __init__(self):
        super().__init__()

        self.title("Reddit Mass Uploader")
        self.geometry("1240x720")

        self.reddit = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sideBar = SidebarFrame(self)
        self.sideBar.grid(row=0, column=0, padx=20, pady=20, sticky="nsw")

        self.primary_tabview = customtkinter.CTkTabview(self)
        self.primary_tabview.grid(row=0, column=1, padx=(0, 20), pady=(0, 20), sticky="sewn")

        # create tabs
        self.primary_tabview.add("Login")
        self.primary_tabview.add("Subreddits")
        self.primary_tabview.add("Post")

        # configure tabs
        self.primary_tabview.tab("Post").grid_rowconfigure(0, weight=1)
        self.primary_tabview.tab("Post").grid_columnconfigure(0, weight=1)

        self.primary_tabview.tab("Login").grid_rowconfigure(0, weight=1)
        self.primary_tabview.tab("Login").grid_columnconfigure(0, weight=1)

        self.primary_tabview.tab("Subreddits").grid_rowconfigure(0, weight=1)
        self.primary_tabview.tab("Subreddits").grid_columnconfigure(0, weight=1)

        # add widgets on tabs
        self.login = LoginFrame(master=self.primary_tabview.tab("Login"))
        self.login.grid(row=0, column=0, sticky="nesw")

        self.get_subreddits = GetSubRedditsFrame(self.primary_tabview.tab("Subreddits"), self.login)
        self.get_subreddits.grid(row=0, column=0, sticky="nesw")

        # UPLOAD TABS

        self.post_tabview = customtkinter.CTkTabview(self.primary_tabview.tab("Post"))
        self.post_tabview.grid(row=0, column=0, padx=(0, 20), pady=(0, 20), sticky="nesw")

        # create tabs
        self.post_tabview.add("Text")
        self.post_tabview.add("Image")
        self.post_tabview.add("Video")

        self.post_tabview.tab("Text").grid_rowconfigure(0, weight=1)
        self.post_tabview.tab("Text").grid_columnconfigure(0, weight=1)

        self.post_tabview.tab("Image").grid_rowconfigure(0, weight=1)
        self.post_tabview.tab("Image").grid_columnconfigure(0, weight=1)

        self.post_tabview.tab("Video").grid_rowconfigure(0, weight=1)
        self.post_tabview.tab("Video").grid_columnconfigure(0, weight=1)

        self.uploadTextPost = UploadTextPostFrame(self.post_tabview.tab("Text"), self.login, self.sideBar)
        self.uploadTextPost.grid(row=0, column=0, sticky="nesw")

        self.uploadImagePost = UploadImagePostFrame(self.post_tabview.tab("Image"), self.login, self.sideBar)
        self.uploadImagePost.grid(row=0, column=0, sticky="nesw")

        self.uploadVideoPost = UploadVideoPostFrame(self.post_tabview.tab("Video"), self.login, self.sideBar)
        self.uploadVideoPost.grid(row=0, column=0, sticky="nesw")

        # self.bind("<Configure>", self.resized)
        self.bind("<Configure>", self.uploadImagePost.dnd.dnd_gallery.width_resize)

        self.width_listeners = []

        # link buttons to login
        self.login.login_buttons_enable_list = [self.uploadTextPost.submit_button,
                                                self.uploadImagePost.submit_button,
                                                self.uploadVideoPost.submit_button,
                                                self.get_subreddits.get_button]

    def resized(self, event):
        for obj in self.width_listeners:
            obj.width_resive(self.winfo_width())


class SidebarFrame(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.grid_rowconfigure(0, weight=1)

        self.subreddits_scroll_frame = SubredditsScrollFrame(self)
        self.subreddits_scroll_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsw")

        button3 = customtkinter.CTkButton(self, text="Select All",
                                          command=self.subreddits_scroll_frame.select_all)
        button3.grid(row=1, column=0, padx=5, pady=5, sticky="s")

        button = customtkinter.CTkButton(self, text="Clear All", command=self.subreddits_scroll_frame.deselect_all)
        button.grid(row=2, column=0, padx=5, pady=5, sticky="s")

        button2 = customtkinter.CTkButton(self, text="Load SubReddits",
                                          command=self.subreddits_scroll_frame.load_subreddits_from_file)
        button2.grid(row=3, column=0, padx=5, pady=5, sticky="s")

        self.save_new_list_button = customtkinter.CTkButton(self, text="Save as new list",
                                                            command=self.subreddits_scroll_frame.save_subreddits)
        self.save_new_list_button.grid(row=4, column=0, padx=5, pady=5, sticky="s")


class SubredditsScrollFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master)

        self.subreddits_list = []
        self.checkbox_list = []

    def get_checked_items(self):
        return [checkbox.cget("text") for checkbox in self.checkbox_list if checkbox.get() == 1]

    def select_all(self):
        for i in self.checkbox_list:
            i.select()

    def deselect_all(self):
        for i in self.checkbox_list:
            i.deselect()

    def refresh_subreddits_list(self):

        print("REFRESH GUI LIST")
        for i in self.checkbox_list:
            i.destroy()

        self.checkbox_list.clear()

        for i, item in enumerate(self.subreddits_list):
            checkbox = customtkinter.CTkCheckBox(self, text=item)

            checkbox.grid(row=len(self.checkbox_list), column=0, pady=(0, 10), sticky="w")
            self.checkbox_list.append(checkbox)

    def load_subreddits_from_file(self):

        print("SET SUBREDDIT LIST")
        # file type
        filetypes = (
            ('text files', '*.txt'),
        )
        # show the open file dialog
        f = fd.askopenfile(mode='r', filetypes=filetypes)
        # read the text file and show its content on the Text

        self.subreddits_list = json.loads(f.readlines()[0])  # list(map(lambda s: s.strip(), f.readlines()))

        # while "" in self.subreddits_list:
        #    self.subreddits_list.remove("")

        self.refresh_subreddits_list()

    def load_subreddits_from_list(self, subreddits_list):

        self.subreddits_list = subreddits_list

        self.refresh_subreddits_list()

    def save_subreddits(self, button=None):

        fob = filedialog.asksaveasfile(filetypes=[('text file', '*.txt')],
                                       defaultextension='.txt',
                                       mode='w')
        try:
            print("SAVING SUBREDDITS: ", self.get_checked_items())
            fob.write(json.dumps(self.get_checked_items()))
            fob.close()

            if button != None:
                button.configure(text="Saved")
                button.after(4000, lambda: button.configure(text='Save To File'))
        except Exception as e:
            print("There is an error...", e)


class UploadTextPostFrame(customtkinter.CTkFrame):
    def __init__(self, master, loginFrame, sideBarFrame):
        super().__init__(master)

        self.app = master
        self.login_frame = loginFrame
        self.side_bar_frame = sideBarFrame

        self.title = ""
        self.description = ""

        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Title
        label = customtkinter.CTkLabel(self, text="Title", font=customtkinter.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.title_input = customtkinter.CTkEntry(self, placeholder_text="Title", width=300)
        self.title_input.grid(row=1, column=0, padx=20, pady=0, sticky="w")

        # Description
        label = customtkinter.CTkLabel(self, text="Description", font=customtkinter.CTkFont(size=20, weight="bold"))
        label.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        self.description_input = customtkinter.CTkTextbox(self, height=150, width=300) # placeholder_text="Description"
        self.description_input.grid(row=3, column=0, padx=20, pady=0, sticky="w")

        # NSFW
        self.nsfw_checkbox = customtkinter.CTkCheckBox(self, text="NSFW")
        self.nsfw_checkbox.grid(row=4, column=0, padx=20, pady=10, sticky="w")

        # Submit
        self.submit_button = customtkinter.CTkButton(self, text="Post!", state="disabled", command=lambda: self.post(
            self.login_frame.reddit,
            self.side_bar_frame.subreddits_scroll_frame.get_checked_items(),
            self.title_input.get(),
            self.description_input.get(),
            self.nsfw_checkbox.get(),
        ),
                                                     font=customtkinter.CTkFont(size=18, weight="bold"))
        self.submit_button.grid(row=7, column=0, padx=20, pady=10, sticky="s")

    def post(self, reddit, subreddits_to_post_in, title, description, nsfw):
        print("POSTING NORMAL")
        for subreddit in subreddits_to_post_in:
            print("POSTING TO: ", subreddit)
            api_resp = reddit.subreddit(subreddit).submit(
                title,
                selftext=description,
                nsfw=nsfw,
            )


class UploadImagePostFrame(customtkinter.CTkFrame):
    def __init__(self, master, loginFrame, sideBarFrame):
        super().__init__(master)

        self.app = master
        self.login_frame = loginFrame
        self.side_bar_frame = sideBarFrame

        self.title = ""
        self.description = ""

        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Title
        title_label = customtkinter.CTkLabel(self, text="Title", font=customtkinter.CTkFont(size=20, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.title_input = customtkinter.CTkEntry(self, placeholder_text="Title", width=300)
        self.title_input.grid(row=1, column=0, padx=20, pady=0, sticky="w")

        # OutBound URL
        outbound_url_label = customtkinter.CTkLabel(self, text="Gallery Outbound URL",
                                                    font=customtkinter.CTkFont(size=20, weight="bold"))
        outbound_url_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        self.outbound_url_input = customtkinter.CTkEntry(self, placeholder_text="Outbound URL", width=300)
        self.outbound_url_input.grid(row=3, column=0, padx=20, pady=0, sticky="w")

        # NSFW
        self.nsfw_checkbox = customtkinter.CTkCheckBox(self, text="NSFW")
        self.nsfw_checkbox.grid(row=4, column=0, padx=20, pady=10, sticky="w")

        # DnD
        self.dnd = DnDFrame(self, [".png", ".jpg", ".jpeg"], -1)
        self.dnd.grid(row=5, column=0, padx=20, pady=10, sticky="nesw")

        # DnD Clear
        button = customtkinter.CTkButton(self, text="Clear All",
                                         command=self.dnd.dnd_gallery.clear_all)
        button.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="w")

        # Submit
        self.submit_button = customtkinter.CTkButton(self, text="Post!", state="disabled", command=lambda: self.post(
            self.login_frame.reddit,
            self.side_bar_frame.subreddits_scroll_frame.get_checked_items(),
            self.title_input.get(),
            self.nsfw_checkbox.get(),
            self.dnd.dnd_gallery.image_paths_list,
            outbound_url=self.outbound_url_input.get(),

        ),
                                                     font=customtkinter.CTkFont(size=18, weight="bold"))
        self.submit_button.grid(row=7, column=0, padx=20, pady=10, sticky="s")

    def post(self, reddit, subreddits_to_post_in, title, nsfw, image_paths, outbound_url=None):

        if len(image_paths) == 1:

            print("POSTING SINGAL IMAGE")
            for subreddit in subreddits_to_post_in:
                print("POSTING TO: ", subreddit)
                api_resp = reddit.subreddit(subreddit).submit_image(
                    title,
                    nsfw=nsfw,
                    image_path=image_paths[0]
                )

        elif len(image_paths) > 1:
            print("POSTING GALLERY")

            # generate images dict
            image_dict = []
            for image_path in image_paths:
                image_dict.append({"image_path": image_path,
                                   "outbound_url": outbound_url})

            for subreddit in subreddits_to_post_in:
                print("POSTING TO: ", subreddit)
                api_resp = reddit.subreddit(subreddit).submit_gallery(
                    title,
                    images=image_dict,
                    nsfw=nsfw,
                )


class UploadVideoPostFrame(customtkinter.CTkFrame):
    def __init__(self, master, loginFrame, sideBarFrame):
        super().__init__(master)

        self.app = master
        self.login_frame = loginFrame
        self.side_bar_frame = sideBarFrame

        self.title = ""
        self.description = ""

        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Title
        label = customtkinter.CTkLabel(self, text="Title", font=customtkinter.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.title_input = customtkinter.CTkEntry(self, placeholder_text="Title", width=300)
        self.title_input.grid(row=1, column=0, padx=20, pady=0, sticky="w")

        # NSFW
        self.nsfw_checkbox = customtkinter.CTkCheckBox(self, text="NSFW")
        self.nsfw_checkbox.grid(row=4, column=0, padx=20, pady=10, sticky="w")

        # GIF
        self.gif_checkbox = customtkinter.CTkCheckBox(self, text="Gif")
        self.gif_checkbox.grid(row=4, column=0, padx=20, pady=10, sticky="w")

        # DnD
        self.dnd = DnDFrame(self, [".mp4"], 1)
        self.dnd.grid(row=5, column=0, padx=20, pady=10, sticky="nesw")

        # DnD Clear
        button = customtkinter.CTkButton(self, text="Clear All",
                                         command=self.dnd.dnd_gallery.clear_all)
        button.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="w")

        # Submit
        self.submit_button = customtkinter.CTkButton(self, text="Post!", state="disabled", command=lambda: self.post(
            self.login_frame.reddit,
            self.side_bar_frame.subreddits_scroll_frame.get_checked_items(),
            self.title_input.get(),
            self.nsfw_checkbox.get(),
            self.gif_checkbox.get(),
            self.dnd.dnd_gallery.image_paths_list
        ), font=customtkinter.CTkFont(size=18, weight="bold"))
        self.submit_button.grid(row=7, column=0, padx=20, pady=10, sticky="s")

    def post(self, reddit, subreddits_to_post_in, title, nsfw, gif, video_path):

        clean_video_path = None

        for path in video_path:
            if ".mp4" in path:
                clean_video_path = path
                break

        if clean_video_path is not None:
            print("POSTING VIDEO")

            for subreddit in subreddits_to_post_in:
                print("POSTING TO: ", subreddit)
                api_resp = reddit.subreddit(subreddit).submit_video(
                    title,
                    nsfw=nsfw,
                    video_path=clean_video_path,
                    videogif=gif
                )
        else:
            print("No Video Found in DnD")


class DnDFrame(customtkinter.CTkFrame):
    def __init__(self, master, allowed_file_type, max_items):
        super().__init__(master)

        self.app = master.app

        self.allowed_file_type = allowed_file_type

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.first_file_drop = True

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.file_dropped)

        # Drag & Drop Gallery
        self.dnd_gallery = DnDGallery(self, max_items)
        self.dnd_gallery.grid(row=0, column=0, padx=5, pady=5, sticky="nesw")

        # Drag & Drop Label
        self.dnd_label = customtkinter.CTkLabel(self, text="Drag and drop file in the entry box")
        self.dnd_label.grid(row=0, column=0, padx=5, pady=5, sticky="nesw")

    def file_dropped(self, event):

        images = []

        files_str = event.data
        split_data = []

        # format weird string to list of paths
        while True:
            search = re.search(r' \{{0,1}[A-Z]:', files_str)
            try:
                split_data.append(files_str[:search.start()])
                files_str = files_str[search.start() + 1:]
            except:
                split_data.append(files_str)
                break

        # process list of paths
        for image_path in split_data:

            if any(element in image_path for element in self.allowed_file_type):

                if image_path[0] == "{" and image_path[-1] == "}":
                    images.append(image_path[1:-1])
                else:
                    images.append(image_path)
            else:
                print("NOT ALLOWED FILE TYPE: ", image_path)

        if len(images) != 0:
            if self.first_file_drop:
                self.dnd_label.grid_forget()

            self.dnd_gallery.add_images(images)


class DnDGallery(customtkinter.CTkScrollableFrame):
    def __init__(self, master, max_items):
        super().__init__(master)

        self.app = master.app

        self.max_items = max_items

        self.image_size = 150
        self.image_paths_list = []
        self.image_widgets_list = []

        self.cols_max = 4

    def add_images(self, image_paths):

        print("\nADDING IMG PATHS: ", image_paths)

        if self.max_items == -1 or len(self.image_paths_list) < self.max_items:

            self.image_paths_list = self.image_paths_list + image_paths

            print("image_paths_list: ", self.image_paths_list)

            self.refresh_images()

        else:
            print("MAX IMAGES REACHED")

    def clear_all(self):

        self.clear_gui()
        self.image_paths_list.clear()

    def clear_gui(self):
        print("CLEAR GUI")
        for i in self.image_widgets_list:
            i.destroy()

        self.image_widgets_list.clear()

    def refresh_images(self):
        print("REFRESH Gallery Col: ", self.cols_max)

        self.clear_gui()

        for image_path in self.image_paths_list:

            if ".mp4" in image_path:
                path_split = image_path.split("/")
                file_name = path_split[-1]

                print("File Name: ", path_split[-1])

                try:
                    print("Check if thumbnail exsists")
                    imageCTK = customtkinter.CTkImage(Image.open("./thumbnails/" + file_name[:-4] + ".png"),
                                                      size=(150, 150))
                except:

                    try:

                        print("Creating thumbnail")

                        options = {
                            'trim': False,
                            'height': 150,
                            'width': 150,
                            'quality': 85,
                            'type': 'thumbnail'
                        }

                        # generate_thumbnail(image_path, "./thumbnails/" + file_name[:-4] + ".png", options)

                        command = f"ffmpeg -hide_banner -loglevel error -i \"{image_path}\" -ss 00:00:00.000 -vframes 1 \"./thumbnails/{file_name[:-4]}.png\""

                        os.system(command)

                        imageCTK = customtkinter.CTkImage(Image.open("./thumbnails/" + path_split[-1][:-4] + ".png"),
                                                          size=(150, 150))
                    except Exception as e:
                        imageCTK = customtkinter.CTkImage(Image.open("./images/default_video.png"), size=(150, 150))

            else:
                imageCTK = customtkinter.CTkImage(Image.open(image_path), size=(150, 150))

            widget = customtkinter.CTkLabel(self, image=imageCTK, text="")
            widget.grid(row=len(self.image_widgets_list) // self.cols_max,
                        column=len(self.image_widgets_list) % self.cols_max,
                        padx=5, pady=5)

            self.image_widgets_list.append(widget)

            print("IMG row: ", len(self.image_widgets_list) // self.cols_max, " col: ",
                  len(self.image_widgets_list) % self.cols_max)

    def width_resize(self, width):

        new_col_max = max((self.app.winfo_width() - 130) // self.image_size, 1)

        if new_col_max != self.cols_max:
            self.cols_max = new_col_max
            self.refresh_images()


class LoginFrame(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.reddit = None
        self.login_buttons_enable_list = None

        # try to auto load config

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        try:
            self.password = self.config['CONFIG']['PASSWORD']
        except KeyError:
            self.password = ""

        try:
            self.client_id = self.config['CONFIG']['CLIENT_ID']
        except KeyError:
            self.client_id = ""

        try:
            self.client_secret = self.config['CONFIG']['CLIENT_SECRET']
        except KeyError:
            self.client_secret = ""

        try:
            self.username = self.config['CONFIG']['USERNAME']
        except KeyError:
            self.username = ""

        try:
            WAIT = int(self.config['CONFIG']['WAIT'])
        except KeyError:
            WAIT = 1000

        self.grid_columnconfigure(0, weight=1)

        # CLIENT_ID
        label = customtkinter.CTkLabel(self, text="CLIENT_ID", font=customtkinter.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="w")

        self.client_id_input = customtkinter.CTkEntry(self, placeholder_text="Client ID")
        self.client_id_input.insert(0, self.client_id)
        self.client_id_input.grid(row=1, column=0, padx=20, pady=0, sticky="w")

        # CLIENT_SECRET
        label = customtkinter.CTkLabel(self, text="CLIENT_SECRET", font=customtkinter.CTkFont(size=20, weight="bold"))
        label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")

        self.client_secret_input = customtkinter.CTkEntry(self, placeholder_text="Client secret")
        self.client_secret_input.insert(0, self.client_secret)
        self.client_secret_input.grid(row=3, column=0, padx=20, pady=0, sticky="w")

        # USERNAME
        label = customtkinter.CTkLabel(self, text="USERNAME", font=customtkinter.CTkFont(size=20, weight="bold"))
        label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="w")

        self.username_input = customtkinter.CTkEntry(self, placeholder_text="Username")
        self.username_input.insert(0, self.username)
        self.username_input.grid(row=5, column=0, padx=20, pady=0, sticky="w")

        # PASSWORD
        label = customtkinter.CTkLabel(self, text="PASSWORD", font=customtkinter.CTkFont(size=20, weight="bold"))
        label.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="w")

        self.password_input = customtkinter.CTkEntry(self, placeholder_text="Password", show="*")
        self.password_input.insert(0, self.password)
        self.password_input.grid(row=7, column=0, padx=20, pady=0, sticky="w")

        # Login
        button = customtkinter.CTkButton(self, text="Login", command=self.login,
                                         font=customtkinter.CTkFont(size=18, weight="bold"))
        button.grid(row=8, column=0, padx=20, pady=10, sticky="w")

        # SAVE To Config
        button = customtkinter.CTkButton(self, text="Save To Config", command=self.save_config,
                                         font=customtkinter.CTkFont(size=18, weight="bold"))
        button.grid(row=9, column=0, padx=20, pady=10, sticky="w")

    def login(self):

        print("attempt loging")

        self.save_settings()

        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                password=self.password,
                user_agent="Script",
                username=self.username,
            )
            self.login_buttons_enable()
            print("LOGIN SUCCESS: ", self.reddit)
        except Exception as e:
            print("LOGIN ERROR: ", e)

    def login_buttons_enable(self):

        for button in self.login_buttons_enable_list:
            button.configure(state="normal")
        pass

    def save_settings(self):
        print("flushing login vars")
        self.client_id = self.client_id_input.get()
        self.client_secret = self.client_secret_input.get()
        self.username = self.username_input.get()
        self.password = self.password_input.get()

    def save_config(self):

        print("saving to config")

        self.save_settings()

        self.config.set("CONFIG", 'CLIENT_ID', self.client_id)
        self.config.set("CONFIG", 'CLIENT_SECRET', self.client_secret)
        self.config.set("CONFIG", 'USERNAME', self.username)

        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)


class GetSubRedditsFrame(customtkinter.CTkFrame):
    def __init__(self, master, loginFrame):
        super().__init__(master)

        self.loginFrame = loginFrame

        self.grid_rowconfigure(1, weight=1)

        # Pull Subreddits
        self.get_button = customtkinter.CTkButton(self, text="Get All Subreddits",
                                                  state="disabled",
                                                  command=lambda: self.get_all_subreddits(),
                                                  font=customtkinter.CTkFont(size=18, weight="bold"))
        self.get_button.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="")

        # Subreddits

        self.subreddits_scroll_frame = SubredditsScrollFrame(self)
        self.subreddits_scroll_frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsw")

        button = customtkinter.CTkButton(self, text="Select All", command=self.subreddits_scroll_frame.select_all)
        button.grid(row=2, column=0, padx=20, pady=5, sticky="")

        button = customtkinter.CTkButton(self, text="Clear All", command=self.subreddits_scroll_frame.deselect_all)
        button.grid(row=3, column=0, padx=20, pady=5, sticky="")

        # SAVE To File
        button = customtkinter.CTkButton(self, text="Save To File",
                                         command=lambda: self.subreddits_scroll_frame.save_subreddits(button),
                                         font=customtkinter.CTkFont(size=18, weight="bold"))
        button.grid(row=4, column=0, padx=20, pady=10, sticky="")

    def get_all_subreddits(self):
        print("GET SUBREDDITS API CALL")

        self.get_button.configure(text="Loading")

        # api call

        api_resp = self.loginFrame.reddit.user.subreddits(limit=None)

        self.get_button.configure(text="Get All Subreddits")

        filtered_subreddits = []

        for subreddit in api_resp:
            if subreddit.display_name[:2] != "u_":
                filtered_subreddits.append(subreddit.display_name)

        self.subreddits_scroll_frame.load_subreddits_from_list(filtered_subreddits)  # """


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    folder = './thumbnails'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    app = App()
    app.mainloop()
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
